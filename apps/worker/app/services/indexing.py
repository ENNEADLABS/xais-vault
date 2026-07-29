"""
Source indexing pipeline — the complete lifecycle of a document.

Pipeline:
  1. Download file from Supabase Storage
  2. Extract text (via extractors)
  3. Chunk intelligently (4000-6000 tokens)
  4. Embed chunks (Gemini Embedding 2, 1536 dims)
  5. Generate summary + topics (Claude)
  6. Store everything in DB
  7. Extract entities + relations (Knowledge Graph, Claude Haiku)
  8. Update source status to 'ready'

Helpers in indexing_helpers.py. Prompt in prompts/summary_system.txt.
"""

import logging
import os
from datetime import datetime, timezone

from packages.db.client import safe_get_list, safe_get_one

from ..extractors import extract
from .chunking import chunk_document
from .entity_extraction import extract_entities_from_chunks
from .indexing_helpers import (
    download_file,
    embed_chunks,
    generate_summary,
    maybe_trigger_scan,
    store_chunks,
)
from .webhook_dispatcher import _emit_webhook

logger = logging.getLogger(__name__)


async def index_source(supabase, payload: dict) -> dict:
    """Full indexing pipeline for a single source document."""
    source_id = payload["source_id"]

    supabase.table("sources").update(
        {
            "status": "processing",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", source_id).execute()

    try:
        result = supabase.table("sources").select("*").eq("id", source_id).execute()
        source = safe_get_one(result)
        if not source:
            raise ValueError(f"Source {source_id} not found")

        workspace_id = source["workspace_id"]
        # Defense-in-depth contre le job poisoning : vérifier que le source
        # appartient bien à l'organisation du job (évite les jobs cross-tenant).
        job_org_id = payload.get("organization_id")
        if job_org_id and source.get("organization_id") != job_org_id:
            raise ValueError(
                f"Job poisoning detected: source {source_id} belongs to org "
                f"{source.get('organization_id')}, not {job_org_id}"
            )
        organization_id = job_org_id or source["organization_id"]
        file_type = source["type"]
        file_path = source.get("file_path")
        skip_extraction = payload.get("skip_extraction", False)

        # Text sources have extracted_text already in the DB
        if skip_extraction and source.get("extracted_text"):
            text = source["extracted_text"]
            word_count = len(text.split())
            page_count = None
            extraction_metadata = {"source": "pasted_text"}
        elif file_path:
            local_path = await download_file(supabase, file_path)
        else:
            raise ValueError(
                f"Source {source_id} has no file_path and no extracted_text"
            )

        try:
            if not skip_extraction or not source.get("extracted_text"):
                logger.info(f"Extracting text from source {source_id} ({file_type})")
                extraction = await extract(local_path, file_type)
                text = extraction.text
                word_count = extraction.word_count
                page_count = extraction.page_count
                extraction_metadata = extraction.metadata
            else:
                local_path = None  # No file to clean up

            logger.info(f"Chunking source {source_id}: {word_count} words")
            chunks = chunk_document(text)

            if not chunks:
                raise ValueError(f"No content extracted from source {source_id}")

            logger.info(f"Embedding {len(chunks)} chunks for source {source_id}")
            embeddings, embedding_usage = await embed_chunks(chunks)

            logger.info(f"Generating summary for source {source_id}")
            summary_data, summary_usage = await generate_summary(text)

            logger.info(f"Storing {len(chunks)} chunks in DB for source {source_id}")
            await store_chunks(
                supabase,
                chunks=chunks,
                embeddings=embeddings,
                source_id=source_id,
                workspace_id=workspace_id,
                organization_id=organization_id,
            )

            # Knowledge Graph : extraire entités et relations
            logger.info("Extracting entities for source %s", source_id)
            stored_chunks = safe_get_list(
                supabase.table("chunks")
                .select("id, content, chunk_index")
                .eq("source_id", source_id)
                .order("chunk_index")
                .execute()
            )
            entity_stats = await extract_entities_from_chunks(
                supabase,
                chunks=stored_chunks,
                workspace_id=workspace_id,
                organization_id=organization_id,
            )
            entity_cost = entity_stats.get("cost_usd", 0.0)

            supabase.table("sources").update(
                {
                    "status": "ready",
                    "extracted_text": text,
                    "page_count": page_count,
                    "word_count": word_count,
                    "summary": summary_data.get("summary", ""),
                    "topics": summary_data.get("topics", []),
                    "suggested_questions": summary_data.get("suggested_questions", []),
                    "metadata": {
                        **source.get("metadata", {}),
                        "extraction": extraction_metadata,
                        "chunk_count": len(chunks),
                        "entity_count": entity_stats.get("entities_count", 0),
                        "relation_count": entity_stats.get("relations_count", 0),
                    },
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", source_id).execute()

            total_cost = embedding_usage + summary_usage + entity_cost
            stats = {
                "source_id": source_id,
                "chunks": len(chunks),
                "pages": page_count,
                "words": word_count,
                "entities": entity_stats.get("entities_count", 0),
                "relations": entity_stats.get("relations_count", 0),
                "total_cost_usd": total_cost,
            }

            logger.info(f"Indexing complete for source {source_id}: {stats}")

            await maybe_trigger_scan(
                supabase, workspace_id=workspace_id, organization_id=organization_id
            )

            await _emit_webhook(
                supabase,
                organization_id=organization_id,
                event_type="source.ready",
                data={
                    "source_id": source_id,
                    "workspace_id": workspace_id,
                    "name": source.get("name", ""),
                    "type": file_type,
                    "word_count": word_count,
                    "chunk_count": len(chunks),
                },
            )

            return stats

        finally:
            if local_path and os.path.exists(local_path):
                os.unlink(local_path)

    except Exception as e:
        supabase.table("sources").update(
            {
                "status": "failed",
                "error_message": str(e),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", source_id).execute()
        await _emit_webhook(
            supabase,
            organization_id=payload.get("organization_id", ""),
            event_type="source.failed",
            data={
                "source_id": source_id,
                "workspace_id": payload.get("workspace_id", ""),
                "error": str(e),
            },
        )
        raise
