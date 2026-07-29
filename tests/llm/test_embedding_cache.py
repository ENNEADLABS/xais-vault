"""Tests pour packages/llm/embedding_cache.py"""

import pytest

from packages.db.redis_client import InMemoryCacheBackend
from packages.llm.embedding_cache import (
    _cache_key,
    get_cached_embedding,
    set_cached_embedding,
)


@pytest.fixture
def cache():
    return InMemoryCacheBackend()


def test_cache_key_normalization():
    """Queries avec casse différente → même clé."""
    k1 = _cache_key("Quel est le CA?", "workspace-1")
    k2 = _cache_key("quel est le ca?", "workspace-1")
    assert k1 == k2


def test_cache_key_different_deals():
    """Même query, workspaces différents → clés différentes."""
    k1 = _cache_key("test", "workspace-1")
    k2 = _cache_key("test", "workspace-2")
    assert k1 != k2


@pytest.mark.asyncio
async def test_cache_miss_returns_none(cache):
    result = await get_cached_embedding(cache, "query", "workspace-1")
    assert result is None


@pytest.mark.asyncio
async def test_cache_hit_returns_embedding(cache):
    embedding = [0.1, 0.2, 0.3]
    await set_cached_embedding(cache, "query", "workspace-1", embedding)
    result = await get_cached_embedding(cache, "query", "workspace-1")
    assert result == embedding


@pytest.mark.asyncio
async def test_cache_graceful_no_redis():
    """cache=None → pas d'erreur."""
    result = await get_cached_embedding(None, "query", "workspace-1")
    assert result is None
    await set_cached_embedding(None, "query", "workspace-1", [0.1])


@pytest.mark.asyncio
async def test_cache_graceful_redis_error():
    """Cache qui lève une exception → fallback silencieux."""

    class BrokenCache:
        async def get(self, key):
            raise ConnectionError("down")

        async def set(self, key, value, ex=None):
            raise ConnectionError("down")

    broken = BrokenCache()
    result = await get_cached_embedding(broken, "query", "workspace-1")
    assert result is None
    await set_cached_embedding(broken, "query", "workspace-1", [0.1])
