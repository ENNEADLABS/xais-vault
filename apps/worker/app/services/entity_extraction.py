"""
Extraction d'entités et relations depuis les chunks via LLM.

Pipeline :
  1. Batch les chunks par groupes de 5
  2. Appel Claude Haiku pour extraction structurée
  3. Déduplication par nom normalisé + embedding similarity
  4. Persist dans entities, entity_relations, chunk_entities

Coût estimé : ~$0.05 par document de 50 pages (~100 chunks).
Helpers de stockage dans entity_extraction_helpers.py.
"""

import json
import logging
from pathlib import Path

from packages.core.entity_schemas import (
    ExtractedEntity,
    ExtractionResult,
)
from packages.llm.factory import get_embedder, get_llm

from .entity_extraction_helpers import (
    normalize_entity_name,
    store_chunk_entities,
    store_entities,
    store_relations,
)

logger = logging.getLogger(__name__)

# Haiku pour l'extraction (coût réduit)
EXTRACTION_MODEL = "claude-haiku-4-5-20251001"
BATCH_SIZE = 5  # Chunks par appel LLM (amortir le prompt système)
DEDUP_SIMILARITY_THRESHOLD = 0.92
EMBEDDING_BATCH_SIZE = 50

EXTRACTION_SYSTEM_PROMPT = (
    Path(__file__).parent.parent / "prompts" / "entity_extraction_system.txt"
).read_text()


async def extract_entities_from_chunks(
    supabase,
    *,
    chunks: list[dict],
    workspace_id: str,
    organization_id: str,
) -> dict:
    """Extrait les entités et relations de tous les chunks d'un document.

    Returns dict avec les stats : {entities_count, relations_count, cost_usd}.
    """
    if not chunks:
        return {"entities_count": 0, "relations_count": 0, "cost_usd": 0.0}

    llm = get_llm()
    total_cost = 0.0
    all_entities: list[ExtractedEntity] = []
    all_relations = []
    chunk_entity_map: dict[str, list[str]] = {}  # chunk_id → [entity_names]

    # Batch les chunks par groupes de BATCH_SIZE
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        batch_text = "\n\n---\n\n".join(
            f"[CHUNK {c['chunk_index']}]\n{c['content']}" for c in batch
        )

        prompt = (
            "Analyse ces extraits de document et extrais les entités"
            f" et relations.\n\nEXTRAITS :\n{batch_text}"
        )

        response = await llm.generate(
            prompt,
            system=EXTRACTION_SYSTEM_PROMPT,
            model=EXTRACTION_MODEL,
            max_tokens=2048,
            temperature=0.0,
            json_mode=True,
        )
        total_cost += response.usage.cost_usd

        try:
            data = json.loads(response.content)
            result = ExtractionResult.model_validate(data)
            all_entities.extend(result.entities)
            all_relations.extend(result.relations)

            entity_names = [e.name for e in result.entities]
            for chunk in batch:
                chunk_entity_map[chunk["id"]] = entity_names

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                "Extraction failed for batch %d-%d: %s",
                i, i + len(batch), str(e),
            )
            continue

    if not all_entities:
        return {"entities_count": 0, "relations_count": 0, "cost_usd": total_cost}

    # Déduplication par nom normalisé
    unique_entities = _deduplicate_entities(all_entities)

    # Embed les entités pour le fuzzy matching et le graph search
    embedder = get_embedder()
    entity_texts = [
        f"{e.name}: {e.description}" if e.description else e.name
        for e in unique_entities
    ]

    embeddings: list[list[float]] = []
    for j in range(0, len(entity_texts), EMBEDDING_BATCH_SIZE):
        batch_texts = entity_texts[j : j + EMBEDDING_BATCH_SIZE]
        embed_response = await embedder.embed(
            batch_texts,
            dimensions=1536,
            task_type="RETRIEVAL_DOCUMENT",
        )
        embeddings.extend(embed_response.embeddings)
        total_cost += embed_response.usage.cost_usd

    # Persist via helpers
    entity_id_map = await store_entities(
        supabase,
        entities=unique_entities,
        embeddings=embeddings,
        workspace_id=workspace_id,
        organization_id=organization_id,
    )

    relations_count = await store_relations(
        supabase,
        relations=all_relations,
        entity_id_map=entity_id_map,
        workspace_id=workspace_id,
        organization_id=organization_id,
    )

    await store_chunk_entities(
        supabase,
        chunk_entity_map=chunk_entity_map,
        entity_id_map=entity_id_map,
    )

    # Log le coût dans usage_logs
    supabase.table("usage_logs").insert({
        "organization_id": organization_id,
        "workspace_id": workspace_id,
        "operation": "entity_extraction",
        "cost_usd": total_cost,
        "model_used": EXTRACTION_MODEL,
    }).execute()

    stats = {
        "entities_count": len(entity_id_map),
        "relations_count": relations_count,
        "cost_usd": total_cost,
    }
    logger.info("Entity extraction complete for workspace %s: %s", workspace_id, stats)
    return stats


def _deduplicate_entities(
    entities: list[ExtractedEntity],
) -> list[ExtractedEntity]:
    """Déduplique par nom normalisé. Garde la première occurrence."""
    seen: dict[str, ExtractedEntity] = {}
    for entity in entities:
        key = normalize_entity_name(entity.name)
        if key and key not in seen:
            seen[key] = entity
    return list(seen.values())
