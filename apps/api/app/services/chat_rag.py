"""
Chat RAG — embed query, search chunks, build context prompt.

RAG v3 : hybrid search + knowledge graph search → RRF-3 reranking.
Helpers dans chat_rag_helpers.py pour la limite 200 lignes.
"""

import logging

from packages.db.client import safe_get_list, safe_get_one
from packages.db.redis_client import get_cache
from packages.llm.embedding_cache import get_cached_embedding, set_cached_embedding
from packages.llm.factory import get_embedder

from .chat_graph import graph_search, has_graph_data
from .chat_rag_helpers import (
    build_context_block,
    build_rag_metadata,
    fulltext_fallback,
    merge_hybrid_and_graph,
)
from .chat_rag_types import ChatContext, RagMetadata
from .chat_reranker import rerank_rrf, rerank_rrf3
from .prompts.chat_personas import get_persona

logger = logging.getLogger(__name__)

# Re-export pour backward compat des imports existants
__all__ = ["ChatContext", "RagMetadata", "prepare_context"]

FETCH_COUNT = 50
RERANK_TOP_K = 15
SIMILARITY_THRESHOLD = 0.3
VECTOR_WEIGHT = 0.7
MAX_CONTEXT_TOKENS = 8_000  # Budget tokens pour le contexte RAG


async def _load_org_persona(db, organization_id: str) -> str | None:
    """Lit `organizations.chat_persona`. Retourne None si la colonne n'existe pas (pré-migration)."""
    try:
        result = (
            db.table("organizations")
            .select("chat_persona")
            .eq("id", organization_id)
            .execute()
        )
        row = safe_get_one(result)
        return row.get("chat_persona") if row else None
    except Exception:
        return None


async def prepare_context(
    db,
    *,
    query: str,
    workspace_id: str,
    organization_id: str,
    session_id: str | None = None,
    source_ids: list[str] | None = None,
) -> ChatContext:
    """Embed query → hybrid + graph search → RRF-3 rerank → prompt."""
    cache = get_cache()

    query_embedding = await get_cached_embedding(cache, query, workspace_id)
    if query_embedding is None:
        embedder = get_embedder()
        query_embedding = await embedder.embed_query(query, dimensions=1536)
        await set_cached_embedding(cache, query, workspace_id, query_embedding)

    # Vérifier si le workspace a des données graph
    use_graph = await has_graph_data(db, workspace_id=workspace_id)

    # Hybrid search : over-fetch 50 candidats
    search_result = db.rpc(
        "search_chunks_hybrid",
        {
            "query_embedding": query_embedding,
            "query_text": query,
            "target_workspace_id": workspace_id,
            "match_count": FETCH_COUNT,
            "similarity_threshold": SIMILARITY_THRESHOLD,
            "vector_weight": VECTOR_WEIGHT,
        },
    ).execute()

    hybrid_chunks = safe_get_list(search_result)
    search_mode = "hybrid"
    graph_chunks: list[dict] = []
    entities_matched = 0
    graph_chunks_added = 0

    # Graph search si le workspace a des entités
    if use_graph and hybrid_chunks:
        graph_chunks = await graph_search(
            db, query_embedding=query_embedding, workspace_id=workspace_id,
        )

    # Fusionner et reranker
    if graph_chunks:
        chunks, graph_chunks_added = merge_hybrid_and_graph(
            hybrid_chunks, graph_chunks,
        )
        chunks = rerank_rrf3(chunks, top_k=RERANK_TOP_K)
        search_mode = "hybrid+graph"
        all_entities: set[str] = set()
        for gc in graph_chunks:
            for name in gc.get("matched_entities") or []:
                all_entities.add(name)
        entities_matched = len(all_entities)
    elif hybrid_chunks:
        chunks = rerank_rrf(hybrid_chunks, top_k=RERANK_TOP_K)
    else:
        chunks = []

    if not chunks:
        chunks = fulltext_fallback(db, query=query, workspace_id=workspace_id, top_k=RERANK_TOP_K)
        search_mode = "fulltext_fallback" if chunks else "no_results"

    if source_ids:
        allowed = set(source_ids)
        chunks = [c for c in chunks if c["source_id"] in allowed]

    if not chunks:
        logger.info("No relevant chunks found for query in workspace %s", workspace_id)

    chunk_source_ids = list({c["source_id"] for c in chunks})
    source_map: dict[str, str] = {}

    if chunk_source_ids:
        sources_result = (
            db.table("sources")
            .select("id, name")
            .in_("id", chunk_source_ids)
            .eq("organization_id", organization_id)
            .execute()
        )
        for s in safe_get_list(sources_result):
            source_map[s["id"]] = s["name"]

    context_budget = MAX_CONTEXT_TOKENS
    workspace_result = db.table("workspaces").select("settings").eq("id", workspace_id).execute()
    workspace_settings = safe_get_one(workspace_result)
    if workspace_settings and workspace_settings.get("settings"):
        context_budget = workspace_settings["settings"].get(
            "rag_context_tokens", MAX_CONTEXT_TOKENS
        )

    context_block, tokens_used = build_context_block(
        chunks, source_map, context_budget
    )

    from .chat_history import build_history_block

    history_block = ""
    if session_id:
        history_block = await build_history_block(db, session_id)

    prompt = f"""DOCUMENTS DE RÉFÉRENCE :

{context_block}

---

{history_block}QUESTION DE L'UTILISATEUR :
{query}"""

    rag_metadata = build_rag_metadata(
        chunks, source_map, search_mode, tokens_used, context_budget,
        entities_matched=entities_matched,
        graph_chunks_added=graph_chunks_added,
    )

    persona_name = await _load_org_persona(db, organization_id)
    system_prompt = get_persona(persona_name)

    return ChatContext(
        chunks=chunks,
        prompt=prompt,
        system_prompt=system_prompt,
        source_map=source_map,
        rag_metadata=rag_metadata,
    )
