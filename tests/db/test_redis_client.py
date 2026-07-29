"""
Tests pour packages/db/redis_client.py

- InMemoryCacheBackend : tests unitaires directs
- RedisCacheBackend : tests avec mock redis.asyncio (fallback, _redis_down)
- Factory get_cache : singleton + sélection du backend
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.db.redis_client import (
    REDIS_HEALTH_CHECK_INTERVAL,
    InMemoryCacheBackend,
    RedisCacheBackend,
    get_cache,
)


@pytest.fixture
def cache():
    """Backend in-memory frais pour chaque test."""
    return InMemoryCacheBackend()


# ─── INCR ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_incr_creates_key(cache):
    """INCR sur clé inexistante crée la clé avec valeur 1."""
    result = await cache.incr("counter")
    assert result == 1


@pytest.mark.asyncio
async def test_incr_increments(cache):
    """INCR successifs incrémentent correctement."""
    for i in range(1, 6):
        result = await cache.incr("counter")
        assert result == i


# ─── GET / SET ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_set_and_get(cache):
    """SET puis GET retourne la valeur."""
    await cache.set("key", "value")
    assert await cache.get("key") == "value"


@pytest.mark.asyncio
async def test_get_missing_key_returns_none(cache):
    """GET sur clé inexistante retourne None."""
    assert await cache.get("nonexistent") is None


@pytest.mark.asyncio
async def test_set_with_expiry(cache):
    """SET avec ex=1 expire après TTL écoulé."""
    import time

    await cache.set("expiring", "val", ex=1)
    assert await cache.get("expiring") == "val"

    # Simuler l'expiration en manipulant le store directement
    cache._store["expiring"] = ("val", time.monotonic() - 1)
    assert await cache.get("expiring") is None


# ─── EXPIRE / TTL ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_expire_sets_ttl(cache):
    """EXPIRE positionne un TTL sur une clé existante."""
    await cache.set("key", "value")
    await cache.expire("key", 60)
    ttl = await cache.ttl("key")
    assert 58 <= ttl <= 60


@pytest.mark.asyncio
async def test_ttl_no_expiry_returns_minus_one(cache):
    """TTL sur clé sans expiry retourne -1."""
    await cache.set("key", "value")
    assert await cache.ttl("key") == -1


@pytest.mark.asyncio
async def test_ttl_missing_key_returns_minus_two(cache):
    """TTL sur clé inexistante retourne -2."""
    assert await cache.ttl("nonexistent") == -2


@pytest.mark.asyncio
async def test_incr_expire_pattern(cache):
    """INCR + EXPIRE : pattern rate limiting standard."""
    count = await cache.incr("rl:user:abc")
    assert count == 1
    await cache.expire("rl:user:abc", 60)

    count2 = await cache.incr("rl:user:abc")
    assert count2 == 2

    # TTL doit être positionné
    ttl = await cache.ttl("rl:user:abc")
    assert ttl > 0


# ─── DELETE ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_removes_key(cache):
    """DELETE supprime la clé."""
    await cache.set("key", "value")
    await cache.delete("key")
    assert await cache.get("key") is None


@pytest.mark.asyncio
async def test_delete_nonexistent_no_error(cache):
    """DELETE sur clé inexistante ne lève pas d'erreur."""
    await cache.delete("nonexistent")  # Should not raise


# ─── CLEAR ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_clear_empties_store(cache):
    """clear() vide le store."""
    await cache.set("a", "1")
    await cache.set("b", "2")
    cache.clear()
    assert await cache.get("a") is None
    assert await cache.get("b") is None


# ─── Factory ──────────────────────────────────────────────────────────────────


def test_get_cache_returns_in_memory_without_redis_url(monkeypatch):
    """Sans REDIS_URL, get_cache() retourne un InMemoryCacheBackend."""
    import packages.db.redis_client as module

    monkeypatch.setattr(module, "_cache_backend", None)
    monkeypatch.delenv("REDIS_URL", raising=False)

    backend = get_cache()
    assert isinstance(backend, InMemoryCacheBackend)

    # Reset pour ne pas polluer les autres tests
    monkeypatch.setattr(module, "_cache_backend", None)


# ─── RedisCacheBackend — succès Redis ────────────────────────────────────────


@pytest.fixture
def redis_backend():
    """RedisCacheBackend avec un client Redis mocké."""
    with patch("redis.asyncio.from_url") as mock_from_url:
        mock_client = MagicMock()
        mock_from_url.return_value = mock_client
        backend = RedisCacheBackend("redis://fake:6379")
        backend._client = mock_client
        yield backend, mock_client


@pytest.mark.asyncio
async def test_redis_get_success(redis_backend):
    """GET délègue à redis quand Redis est up."""
    backend, client = redis_backend
    client.get = AsyncMock(return_value="val")
    result = await backend.get("k")
    assert result == "val"
    client.get.assert_awaited_once_with("k")


@pytest.mark.asyncio
async def test_redis_set_success(redis_backend):
    """SET délègue à redis quand Redis est up."""
    backend, client = redis_backend
    client.set = AsyncMock()
    await backend.set("k", "v", ex=60)
    client.set.assert_awaited_once_with("k", "v", ex=60)


@pytest.mark.asyncio
async def test_redis_incr_success(redis_backend):
    """INCR délègue à redis quand Redis est up."""
    backend, client = redis_backend
    client.incr = AsyncMock(return_value=5)
    result = await backend.incr("counter")
    assert result == 5


@pytest.mark.asyncio
async def test_redis_expire_success(redis_backend):
    """EXPIRE délègue à redis quand Redis est up."""
    backend, client = redis_backend
    client.expire = AsyncMock()
    await backend.expire("k", 120)
    client.expire.assert_awaited_once_with("k", 120)


@pytest.mark.asyncio
async def test_redis_ttl_success(redis_backend):
    """TTL délègue à redis quand Redis est up."""
    backend, client = redis_backend
    client.ttl = AsyncMock(return_value=42)
    result = await backend.ttl("k")
    assert result == 42


@pytest.mark.asyncio
async def test_redis_delete_success(redis_backend):
    """DELETE délègue à redis quand Redis est up."""
    backend, client = redis_backend
    client.delete = AsyncMock()
    await backend.delete("k")
    client.delete.assert_awaited_once_with("k")


# ─── RedisCacheBackend — fallback sur erreur Redis ───────────────────────────


@pytest.mark.asyncio
async def test_redis_get_fallback_on_error(redis_backend):
    """GET bascule sur in-memory après une erreur Redis."""
    backend, client = redis_backend
    client.get = AsyncMock(side_effect=ConnectionError("down"))

    result = await backend.get("k")
    assert result is None  # clé inexistante dans le fallback
    assert backend._redis_down is True
    assert backend._fallback is not None


@pytest.mark.asyncio
async def test_redis_set_fallback_on_error(redis_backend):
    """SET bascule sur in-memory après une erreur Redis."""
    backend, client = redis_backend
    client.set = AsyncMock(side_effect=ConnectionError("down"))

    await backend.set("k", "v", ex=30)
    assert backend._redis_down is True
    # La valeur est dans le fallback
    assert await backend._fallback.get("k") == "v"


@pytest.mark.asyncio
async def test_redis_incr_fallback_on_error(redis_backend):
    """INCR bascule sur in-memory après une erreur Redis."""
    backend, client = redis_backend
    client.incr = AsyncMock(side_effect=ConnectionError("down"))

    result = await backend.incr("counter")
    assert result == 1
    assert backend._redis_down is True


@pytest.mark.asyncio
async def test_redis_expire_fallback_on_error(redis_backend):
    """EXPIRE bascule sur in-memory après une erreur Redis."""
    backend, client = redis_backend
    client.expire = AsyncMock(side_effect=ConnectionError("down"))

    # Préparer une clé dans le fallback pour que expire ait un effet
    await backend.expire("k", 60)
    assert backend._redis_down is True


@pytest.mark.asyncio
async def test_redis_ttl_fallback_on_error(redis_backend):
    """TTL bascule sur in-memory après une erreur Redis."""
    backend, client = redis_backend
    client.ttl = AsyncMock(side_effect=ConnectionError("down"))

    result = await backend.ttl("k")
    assert result == -2  # clé inexistante → -2
    assert backend._redis_down is True


@pytest.mark.asyncio
async def test_redis_delete_fallback_on_error(redis_backend):
    """DELETE bascule sur in-memory après une erreur Redis."""
    backend, client = redis_backend
    client.delete = AsyncMock(side_effect=ConnectionError("down"))

    await backend.delete("k")  # ne lève pas d'erreur
    assert backend._redis_down is True


# ─── RedisCacheBackend — _redis_down avec health check ──────────────────────


def _set_down(backend, fallback=None):
    """Helper : marque le backend comme down sans déclencher le health check."""
    import time

    backend._redis_down = True
    # down_since dans le futur → _try_recover ne se déclenche pas
    backend._down_since = time.monotonic() + 9999
    backend._fallback = fallback or InMemoryCacheBackend()


@pytest.mark.asyncio
async def test_redis_down_flag_is_sticky(redis_backend):
    """Une fois _redis_down=True, les opérations passent par le fallback."""
    backend, client = redis_backend
    client.get = AsyncMock(side_effect=ConnectionError("down"))

    # Première erreur → active le fallback
    await backend.get("k")
    assert backend._redis_down is True

    # Empêcher le health check pour tester le sticky
    import time

    backend._down_since = time.monotonic() + 9999

    # Les appels suivants ne touchent plus Redis
    await backend.set("k", "v")
    result = await backend.get("k")
    assert result == "v"
    assert client.get.await_count == 1


@pytest.mark.asyncio
async def test_redis_down_incr_uses_fallback(redis_backend):
    """INCR utilise le fallback directement quand _redis_down=True."""
    backend, _ = redis_backend
    _set_down(backend)
    result = await backend.incr("c")
    assert result == 1


@pytest.mark.asyncio
async def test_redis_down_expire_uses_fallback(redis_backend):
    """EXPIRE utilise le fallback directement quand _redis_down=True."""
    backend, _ = redis_backend
    _set_down(backend)
    await backend._fallback.set("k", "v")
    await backend.expire("k", 30)
    ttl = await backend._fallback.ttl("k")
    assert 28 <= ttl <= 30


@pytest.mark.asyncio
async def test_redis_down_ttl_uses_fallback(redis_backend):
    """TTL utilise le fallback directement quand _redis_down=True."""
    backend, _ = redis_backend
    _set_down(backend)
    result = await backend.ttl("missing")
    assert result == -2


@pytest.mark.asyncio
async def test_redis_down_delete_uses_fallback(redis_backend):
    """DELETE utilise le fallback directement quand _redis_down=True."""
    backend, _ = redis_backend
    _set_down(backend)
    await backend._fallback.set("k", "v")
    await backend.delete("k")
    assert await backend._fallback.get("k") is None


# ─── RedisCacheBackend — health check recovery ──────────────────────────────


@pytest.mark.asyncio
async def test_try_recover_skips_if_interval_not_elapsed(redis_backend):
    """_try_recover ne tente pas un PING si l'intervalle n'est pas écoulé."""
    import time

    backend, client = redis_backend
    backend._redis_down = True
    backend._down_since = time.monotonic()  # vient de tomber
    client.ping = AsyncMock()

    recovered = await backend._try_recover()
    assert recovered is False
    client.ping.assert_not_awaited()


@pytest.mark.asyncio
async def test_try_recover_succeeds_after_interval(redis_backend):
    """_try_recover réactive Redis si PING réussit après l'intervalle."""
    import time

    backend, client = redis_backend
    backend._redis_down = True
    backend._down_since = time.monotonic() - REDIS_HEALTH_CHECK_INTERVAL - 1
    client.ping = AsyncMock(return_value=True)

    recovered = await backend._try_recover()
    assert recovered is True
    assert backend._redis_down is False
    assert backend._down_since == 0.0
    client.ping.assert_awaited_once()


@pytest.mark.asyncio
async def test_try_recover_fails_resets_timer(redis_backend):
    """_try_recover remet le timer si PING échoue."""
    import time

    backend, client = redis_backend
    backend._redis_down = True
    backend._down_since = time.monotonic() - REDIS_HEALTH_CHECK_INTERVAL - 1
    client.ping = AsyncMock(side_effect=ConnectionError("still down"))

    recovered = await backend._try_recover()
    assert recovered is False
    assert backend._redis_down is True
    # Le timer a été remis à maintenant
    assert backend._down_since > time.monotonic() - 2


@pytest.mark.asyncio
async def test_get_recovers_after_interval(redis_backend):
    """GET repasse sur Redis quand le health check réussit."""
    import time

    backend, client = redis_backend
    backend._redis_down = True
    backend._down_since = time.monotonic() - REDIS_HEALTH_CHECK_INTERVAL - 1
    backend._fallback = InMemoryCacheBackend()
    client.ping = AsyncMock(return_value=True)
    client.get = AsyncMock(return_value="from_redis")

    result = await backend.get("k")
    assert result == "from_redis"
    assert backend._redis_down is False


@pytest.mark.asyncio
async def test_set_recovers_after_interval(redis_backend):
    """SET repasse sur Redis quand le health check réussit."""
    import time

    backend, client = redis_backend
    backend._redis_down = True
    backend._down_since = time.monotonic() - REDIS_HEALTH_CHECK_INTERVAL - 1
    backend._fallback = InMemoryCacheBackend()
    client.ping = AsyncMock(return_value=True)
    client.set = AsyncMock()

    await backend.set("k", "v", ex=10)
    client.set.assert_awaited_once_with("k", "v", ex=10)
    assert backend._redis_down is False


@pytest.mark.asyncio
async def test_incr_recovers_after_interval(redis_backend):
    """INCR repasse sur Redis quand le health check réussit."""
    import time

    backend, client = redis_backend
    backend._redis_down = True
    backend._down_since = time.monotonic() - REDIS_HEALTH_CHECK_INTERVAL - 1
    backend._fallback = InMemoryCacheBackend()
    client.ping = AsyncMock(return_value=True)
    client.incr = AsyncMock(return_value=7)

    result = await backend.incr("c")
    assert result == 7
    assert backend._redis_down is False


@pytest.mark.asyncio
async def test_expire_recovers_after_interval(redis_backend):
    """EXPIRE repasse sur Redis quand le health check réussit."""
    import time

    backend, client = redis_backend
    backend._redis_down = True
    backend._down_since = time.monotonic() - REDIS_HEALTH_CHECK_INTERVAL - 1
    backend._fallback = InMemoryCacheBackend()
    client.ping = AsyncMock(return_value=True)
    client.expire = AsyncMock()

    await backend.expire("k", 60)
    client.expire.assert_awaited_once_with("k", 60)


@pytest.mark.asyncio
async def test_ttl_recovers_after_interval(redis_backend):
    """TTL repasse sur Redis quand le health check réussit."""
    import time

    backend, client = redis_backend
    backend._redis_down = True
    backend._down_since = time.monotonic() - REDIS_HEALTH_CHECK_INTERVAL - 1
    backend._fallback = InMemoryCacheBackend()
    client.ping = AsyncMock(return_value=True)
    client.ttl = AsyncMock(return_value=55)

    result = await backend.ttl("k")
    assert result == 55


@pytest.mark.asyncio
async def test_delete_recovers_after_interval(redis_backend):
    """DELETE repasse sur Redis quand le health check réussit."""
    import time

    backend, client = redis_backend
    backend._redis_down = True
    backend._down_since = time.monotonic() - REDIS_HEALTH_CHECK_INTERVAL - 1
    backend._fallback = InMemoryCacheBackend()
    client.ping = AsyncMock(return_value=True)
    client.delete = AsyncMock()

    await backend.delete("k")
    client.delete.assert_awaited_once_with("k")


@pytest.mark.asyncio
async def test_mark_down_sets_timestamp(redis_backend):
    """_mark_down() positionne _redis_down et _down_since."""
    import time

    backend, _ = redis_backend
    before = time.monotonic()
    backend._mark_down()
    after = time.monotonic()

    assert backend._redis_down is True
    assert before <= backend._down_since <= after


@pytest.mark.asyncio
async def test_use_fallback_creates_singleton():
    """_use_fallback() retourne toujours la même instance."""
    with patch("redis.asyncio.from_url"):
        backend = RedisCacheBackend("redis://fake:6379")
        fb1 = backend._use_fallback()
        fb2 = backend._use_fallback()
        assert fb1 is fb2
        assert isinstance(fb1, InMemoryCacheBackend)


# ─── Factory — avec REDIS_URL ───────────────────────────────────────────────


def test_get_cache_returns_redis_with_url(monkeypatch):
    """Avec REDIS_URL, get_cache() retourne un RedisCacheBackend."""
    import packages.db.redis_client as module

    monkeypatch.setattr(module, "_cache_backend", None)
    monkeypatch.setenv("REDIS_URL", "redis://fake:6379")

    with patch("redis.asyncio.from_url"):
        backend = get_cache()
        assert isinstance(backend, RedisCacheBackend)

    monkeypatch.setattr(module, "_cache_backend", None)


def test_get_cache_singleton(monkeypatch):
    """get_cache() retourne toujours la même instance."""
    import packages.db.redis_client as module

    monkeypatch.setattr(module, "_cache_backend", None)
    monkeypatch.delenv("REDIS_URL", raising=False)

    b1 = get_cache()
    b2 = get_cache()
    assert b1 is b2

    monkeypatch.setattr(module, "_cache_backend", None)
