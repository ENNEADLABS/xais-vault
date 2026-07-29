"""
Graph search — recherche de chunks via le knowledge graph.

Utilise la RPC search_graph_chunks pour traverser entités → relations → chunks.
Le graph search est gratuit en tokens LLM — c'est du SQL pur.
Latence estimée : 30-50ms (parallèle avec le hybrid search).
"""

import logging

from packages.db.client import safe_get_list

logger = logging.getLogger(__name__)

GRAPH_MATCH_COUNT = 30
ENTITY_SIMILARITY_THRESHOLD = 0.7


async def graph_search(
    db,
    *,
    query_embedding: list[float],
    workspace_id: str,
) -> list[dict]:
    """Recherche de chunks via le knowledge graph.

    1. Trouve les entités proches de la query (vector similarity)
    2. Traverse les relations (1 hop)
    3. Récupère les chunks connectés, scorés par graph_score

    Returns liste de chunks enrichis avec graph_score et matched_entities.
    """
    try:
        result = db.rpc(
            "search_graph_chunks",
            {
                "query_embedding": query_embedding,
                "target_workspace_id": workspace_id,
                "match_count": GRAPH_MATCH_COUNT,
                "entity_similarity_threshold": ENTITY_SIMILARITY_THRESHOLD,
            },
        ).execute()

        chunks = safe_get_list(result)

        if chunks:
            logger.info(
                "Graph search: %d chunks found for workspace %s (top score: %.3f)",
                len(chunks),
                workspace_id,
                chunks[0].get("graph_score", 0),
            )
        else:
            logger.info("Graph search: no results for workspace %s", workspace_id)

        return chunks

    except Exception as e:
        # Le graph search est optionnel — on ne veut pas bloquer le RAG
        logger.warning("Graph search failed for workspace %s: %s", workspace_id, str(e))
        return []


async def has_graph_data(db, *, workspace_id: str) -> bool:
    """Vérifie rapidement si le workspace a des entités dans le graph.

    Utile pour éviter un appel RPC inutile si le graph est vide.
    """
    try:
        result = (
            db.table("entities")
            .select("id", count="exact")
            .eq("workspace_id", workspace_id)
            .limit(1)
            .execute()
        )
        return (result.count or 0) > 0
    except Exception:
        return False
