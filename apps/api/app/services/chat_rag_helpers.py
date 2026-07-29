"""
Helpers pour chat_rag.py — fusion graph/hybrid, context building, metadata.

Extrait de chat_rag.py pour respecter la limite de 200 lignes par fichier.
"""

import logging

from packages.db.client import safe_get_list
from packages.llm.token_counter import count_tokens, truncate_to_tokens

from .chat_rag_types import RagMetadata

logger = logging.getLogger(__name__)

MAX_CONTEXT_TOKENS = 8_000
MAX_CHUNK_TOKENS = 1_500


def merge_hybrid_and_graph(
    hybrid_chunks: list[dict],
    graph_chunks: list[dict],
) -> tuple[list[dict], int]:
    """Fusionne les chunks hybrid et graph. Retourne (merged, graph_only_count)."""
    hybrid_ids: set[str] = set()
    for c in hybrid_chunks:
        cid = c.get("chunk_id") or c.get("id")
        if cid:
            hybrid_ids.add(cid)

    # Enrichir les chunks hybrid avec le graph_score si présent
    graph_score_map: dict[str, float] = {}
    graph_entities_map: dict[str, list[str]] = {}
    for gc in graph_chunks:
        cid = gc.get("chunk_id") or gc.get("id")
        if cid:
            graph_score_map[cid] = gc.get("graph_score", 0)
            graph_entities_map[cid] = gc.get("matched_entities") or []

    for c in hybrid_chunks:
        cid = c.get("chunk_id") or c.get("id")
        c["graph_score"] = graph_score_map.get(cid, 0)
        c["matched_entities"] = graph_entities_map.get(cid, [])

    # Ajouter les chunks trouvés UNIQUEMENT par le graph
    graph_only_count = 0
    for gc in graph_chunks:
        cid = gc.get("chunk_id") or gc.get("id")
        if cid and cid not in hybrid_ids:
            merged_chunk = {
                "id": cid,
                "content": gc.get("content", ""),
                "source_id": gc.get("source_id", ""),
                "page_number": gc.get("page_number"),
                "section_title": gc.get("section_title"),
                "similarity": 0,
                "fts_rank": 0,
                "graph_score": gc.get("graph_score", 0),
                "matched_entities": gc.get("matched_entities") or [],
            }
            hybrid_chunks.append(merged_chunk)
            graph_only_count += 1

    return hybrid_chunks, graph_only_count


def build_context_block(
    chunks: list[dict],
    source_map: dict[str, str],
    budget: int,
) -> tuple[str, int]:
    """Construit le bloc de contexte en respectant le budget tokens."""
    if not chunks:
        return "(Aucun document pertinent trouvé pour cette question.)", 0

    parts: list[str] = []
    tokens_used = 0

    for chunk in chunks:
        source_name = source_map.get(chunk["source_id"], "Document inconnu")
        page = chunk.get("page_number", "?")
        section = chunk.get("section_title") or "?"

        header = (
            f"[SOURCE_ID:{chunk['source_id']}] {source_name}"
            f" — Page {page}, Section: {section}"
        )
        content = chunk["content"]

        content_tokens = count_tokens(content)
        if content_tokens > MAX_CHUNK_TOKENS:
            content = truncate_to_tokens(content, MAX_CHUNK_TOKENS)

        block = f"{header}\n{content}"
        block_tokens = count_tokens(block)

        if tokens_used + block_tokens > budget:
            remaining = budget - tokens_used
            if remaining > 200:
                content = truncate_to_tokens(
                    content, remaining - count_tokens(header) - 10
                )
                block = f"{header}\n{content}"
                parts.append(block)
                tokens_used += count_tokens(block)
            break

        parts.append(block)
        tokens_used += block_tokens

    return "\n\n---\n\n".join(parts), tokens_used


def fulltext_fallback(db, *, query: str, workspace_id: str, top_k: int) -> list[dict]:
    """Fallback sur le full-text search quand le hybrid ne retourne rien."""
    result = db.rpc(
        "search_chunks_fulltext",
        {"query_text": query, "target_workspace_id": workspace_id, "match_count": top_k},
    ).execute()
    chunks = safe_get_list(result)
    logger.info("Full-text fallback: %d results for workspace %s", len(chunks), workspace_id)
    return chunks


def build_rag_metadata(
    chunks: list[dict],
    source_map: dict[str, str],
    search_mode: str = "hybrid",
    tokens_used: int = 0,
    tokens_budget: int = MAX_CONTEXT_TOKENS,
    entities_matched: int = 0,
    graph_chunks_added: int = 0,
):
    """Calcule les métadonnées RAG à partir des chunks utilisés."""

    reranked = any("rrf_score" in c for c in chunks) if chunks else False

    if not chunks:
        return RagMetadata(
            chunk_count=0,
            source_count=0,
            avg_similarity=0.0,
            avg_fts_rank=0.0,
            reranked=False,
            search_mode=search_mode,
            tokens_used=0,
            tokens_budget=tokens_budget,
            sources_used=[],
        )

    source_chunk_counts: dict[str, int] = {}
    for c in chunks:
        sid = c["source_id"]
        source_chunk_counts[sid] = source_chunk_counts.get(sid, 0) + 1

    sources_used = [
        {"id": sid, "name": source_map.get(sid, "?"), "chunk_count": count}
        for sid, count in source_chunk_counts.items()
    ]

    avg_sim = sum(c.get("similarity", 0) for c in chunks) / len(chunks)
    avg_fts = sum(c.get("fts_rank", 0) for c in chunks) / len(chunks)

    return RagMetadata(
        chunk_count=len(chunks),
        source_count=len(source_chunk_counts),
        avg_similarity=round(avg_sim, 3),
        avg_fts_rank=round(avg_fts, 4),
        reranked=reranked,
        search_mode=search_mode,
        tokens_used=tokens_used,
        tokens_budget=tokens_budget,
        sources_used=sources_used,
        entities_matched=entities_matched,
        graph_chunks_added=graph_chunks_added,
    )
