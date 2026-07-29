"""
Cache backend — Redis ou in-memory avec fallback automatique.

Sans REDIS_URL : in-memory (single-instance, dev/test)
Avec REDIS_URL  : Redis via redis.asyncio (multi-instance, prod)

Usage:
    from packages.db.redis_client import get_cache

    cache = get_cache()
    count = await cache.incr("rl:user:abc")
    await cache.expire("rl:user:abc", 60)
    value = await cache.get("some:key")
"""

import logging
import os
import time

logger = logging.getLogger(__name__)


# ─── Protocol ─────────────────────────────────────────────────────────────────


class CacheBackend:
    """Interface commune pour Redis et in-memory."""

    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ex: int | None = None) -> None: ...
    async def incr(self, key: str) -> int: ...
    async def expire(self, key: str, seconds: int) -> None: ...
    async def ttl(self, key: str) -> int: ...
    async def delete(self, key: str) -> None: ...


# ─── In-Memory ─────────────────────────────────────────────────────────────────


class InMemoryCacheBackend(CacheBackend):
    """Fallback in-memory — même interface que Redis, sans dépendance externe.

    TTL géré par timestamps monotoniques. Adapté pour dev, tests, et instances uniques.
    """

    def __init__(self) -> None:
        # key → (value, expire_at_monotonic | None)
        self._store: dict[str, tuple[str, float | None]] = {}

    def _get_entry(self, key: str) -> tuple[str, float | None] | None:
        """Retourne l'entrée si elle existe et n'est pas expirée."""
        entry = self._store.get(key)
        if entry is None:
            return None
        _, exp = entry
        if exp is not None and time.monotonic() > exp:
            del self._store[key]
            return None
        return entry

    async def get(self, key: str) -> str | None:
        entry = self._get_entry(key)
        return entry[0] if entry else None

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        expire_at = (time.monotonic() + ex) if ex is not None else None
        self._store[key] = (value, expire_at)

    async def incr(self, key: str) -> int:
        entry = self._get_entry(key)
        if entry is None:
            self._store[key] = ("1", None)
            return 1
        new_val = int(entry[0]) + 1
        self._store[key] = (str(new_val), entry[1])
        return new_val

    async def expire(self, key: str, seconds: int) -> None:
        entry = self._store.get(key)
        if entry is not None:
            _, exp = entry
            # N'écrase le TTL que si la clé n'est pas déjà expirée
            if exp is None or time.monotonic() <= exp:
                self._store[key] = (entry[0], time.monotonic() + seconds)

    async def ttl(self, key: str) -> int:
        entry = self._store.get(key)
        if entry is None:
            return -2  # clé inexistante
        _, exp = entry
        if exp is None:
            return -1  # pas de TTL
        remaining = int(exp - time.monotonic())
        return max(0, remaining)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        """Vide le store — utile pour les tests."""
        self._store.clear()


# ─── Redis ─────────────────────────────────────────────────────────────────────


REDIS_HEALTH_CHECK_INTERVAL = 30  # secondes entre chaque tentative de reconnexion


class RedisCacheBackend(CacheBackend):
    """Backend Redis via redis.asyncio avec fallback in-memory si injoignable.

    Si Redis est down, bascule automatiquement sur InMemoryCacheBackend
    et tente un PING toutes les REDIS_HEALTH_CHECK_INTERVAL secondes.
    Si Redis revient, repasse sur le client Redis.
    """

    def __init__(self, url: str) -> None:
        import redis.asyncio as aioredis  # type: ignore[import]

        self._client = aioredis.from_url(url, decode_responses=True)
        self._fallback: InMemoryCacheBackend | None = None
        self._redis_down = False
        self._down_since: float = 0.0

    def _use_fallback(self) -> InMemoryCacheBackend:
        """Active le fallback in-memory après une erreur Redis."""
        if self._fallback is None:
            self._fallback = InMemoryCacheBackend()
            logger.warning(
                "Redis injoignable — fallback in-memory activé. "
                "Lancez Redis ou supprimez REDIS_URL pour supprimer ce warning."
            )
        return self._fallback

    def _mark_down(self) -> None:
        """Marque Redis comme down avec le timestamp courant."""
        self._redis_down = True
        self._down_since = time.monotonic()

    async def _try_recover(self) -> bool:
        """Tente un PING Redis si l'intervalle de health check est écoulé.

        Retourne True si Redis est de nouveau disponible.
        """
        if time.monotonic() - self._down_since < REDIS_HEALTH_CHECK_INTERVAL:
            return False
        try:
            await self._client.ping()
            self._redis_down = False
            self._down_since = 0.0
            logger.info("Redis reconnecté — reprise du backend Redis.")
            return True
        except Exception:
            self._down_since = time.monotonic()
            return False

    async def get(self, key: str) -> str | None:
        if self._redis_down:
            if await self._try_recover():
                return await self._client.get(key)
            return await self._use_fallback().get(key)
        try:
            return await self._client.get(key)
        except Exception:
            self._mark_down()
            return await self._use_fallback().get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        if self._redis_down:
            if await self._try_recover():
                await self._client.set(key, value, ex=ex)
                return
            return await self._use_fallback().set(key, value, ex=ex)
        try:
            await self._client.set(key, value, ex=ex)
        except Exception:
            self._mark_down()
            await self._use_fallback().set(key, value, ex=ex)

    async def incr(self, key: str) -> int:
        if self._redis_down:
            if await self._try_recover():
                return await self._client.incr(key)
            return await self._use_fallback().incr(key)
        try:
            return await self._client.incr(key)
        except Exception:
            self._mark_down()
            return await self._use_fallback().incr(key)

    async def expire(self, key: str, seconds: int) -> None:
        if self._redis_down:
            if await self._try_recover():
                await self._client.expire(key, seconds)
                return
            return await self._use_fallback().expire(key, seconds)
        try:
            await self._client.expire(key, seconds)
        except Exception:
            self._mark_down()
            await self._use_fallback().expire(key, seconds)

    async def ttl(self, key: str) -> int:
        if self._redis_down:
            if await self._try_recover():
                return await self._client.ttl(key)
            return await self._use_fallback().ttl(key)
        try:
            return await self._client.ttl(key)
        except Exception:
            self._mark_down()
            return await self._use_fallback().ttl(key)

    async def delete(self, key: str) -> None:
        if self._redis_down:
            if await self._try_recover():
                await self._client.delete(key)
                return
            return await self._use_fallback().delete(key)
        try:
            await self._client.delete(key)
        except Exception:
            self._mark_down()
            await self._use_fallback().delete(key)


# ─── Factory singleton ─────────────────────────────────────────────────────────

_cache_backend: "InMemoryCacheBackend | RedisCacheBackend | None" = None


def get_cache() -> "InMemoryCacheBackend | RedisCacheBackend":
    """Retourne le backend de cache (Redis ou in-memory).

    Singleton — initialisé au premier appel.
    Redis si REDIS_URL est défini, in-memory sinon.
    """
    global _cache_backend
    if _cache_backend is None:
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            logger.info("Cache: Redis (%s...)", redis_url[:20])
            _cache_backend = RedisCacheBackend(redis_url)
        else:
            logger.warning(
                "Cache: REDIS_URL absent — in-memory (single-instance uniquement)"
            )
            _cache_backend = InMemoryCacheBackend()
    return _cache_backend
