"""
Cache Redis pour les embeddings de queries.

Clé : embedding:{workspace_id}:{hash(query_normalized)}
TTL : 1 heure
Fallback gracieux si Redis indisponible.
"""

import hashlib
import json
import logging

logger = logging.getLogger(__name__)

CACHE_TTL = 3600  # 1 heure
CACHE_PREFIX = "embedding"


def _cache_key(query: str, workspace_id: str) -> str:
    """Génère la clé de cache pour un embedding de query."""
    normalized = query.strip().lower()
    query_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"{CACHE_PREFIX}:{workspace_id}:{query_hash}"


async def get_cached_embedding(cache, query: str, workspace_id: str) -> list[float] | None:
    """Récupère un embedding depuis le cache."""
    if not cache:
        return None
    try:
        key = _cache_key(query, workspace_id)
        cached = await cache.get(key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Embedding cache get failed: {e}")
    return None


async def set_cached_embedding(
    cache,
    query: str,
    workspace_id: str,
    embedding: list[float],
) -> None:
    """Stocke un embedding dans le cache."""
    if not cache:
        return
    try:
        key = _cache_key(query, workspace_id)
        await cache.set(key, json.dumps(embedding), ex=CACHE_TTL)
    except Exception as e:
        logger.warning(f"Embedding cache set failed: {e}")
