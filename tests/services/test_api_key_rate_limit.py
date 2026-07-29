"""
Tests pour apps/api/app/services/api_key_rate_limit.py

La fonction est maintenant async et utilise le CacheBackend.
On injecte un InMemoryCacheBackend frais via monkeypatch pour isoler les tests.
"""

import pytest

from packages.db.redis_client import InMemoryCacheBackend

KEY_ID = "key-abc123"


@pytest.fixture(autouse=True)
def fresh_cache(monkeypatch):
    """Injecte un backend in-memory frais avant chaque test."""
    import packages.db.redis_client as cache_module

    backend = InMemoryCacheBackend()
    monkeypatch.setattr(cache_module, "_cache_backend", backend)
    return backend


async def _check(key_id: str = KEY_ID, rpm: int = 60, rpd: int = 1000):
    from apps.api.app.services.api_key_rate_limit import check_api_key_rate_limit

    return await check_api_key_rate_limit(key_id, rpm_limit=rpm, rpd_limit=rpd)


# ─── Happy path ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_new_key_is_allowed():
    """Première requête d'une clé inconnue est toujours autorisée."""
    allowed, msg = await _check()
    assert allowed is True
    assert msg == ""


@pytest.mark.asyncio
async def test_within_limits_allowed():
    """Requêtes en dessous des deux limites sont autorisées."""
    for _ in range(5):
        allowed, msg = await _check(rpm=10, rpd=100)
        assert allowed is True
        assert msg == ""


# ─── RPM limit ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rpm_limit_exceeded():
    """Dépasser la limite RPM retourne False avec message."""
    rpm = 3
    for _ in range(rpm):
        await _check(rpm=rpm)
    allowed, msg = await _check(rpm=rpm)
    assert allowed is False
    assert "RPM" in msg
    assert str(rpm) in msg


@pytest.mark.asyncio
async def test_rpm_retry_in_message():
    """Le message RPM contient un temps de retry."""
    rpm = 1
    await _check(rpm=rpm)
    allowed, msg = await _check(rpm=rpm)
    assert allowed is False
    assert "Retry in" in msg


# ─── RPD limit ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rpd_limit_exceeded():
    """Dépasser la limite RPD retourne False avec message."""
    rpd = 3
    for _ in range(rpd):
        await _check(rpm=1000, rpd=rpd)
    allowed, msg = await _check(rpm=1000, rpd=rpd)
    assert allowed is False
    assert "RPD" in msg
    assert str(rpd) in msg


@pytest.mark.asyncio
async def test_rpm_checked_before_rpd():
    """Quand les deux limites sont dépassées, RPM est signalé en premier."""
    limit = 2
    for _ in range(limit + 1):
        await _check(rpm=limit, rpd=limit)
    allowed, msg = await _check(rpm=limit, rpd=limit)
    assert allowed is False
    assert "RPM" in msg


# ─── Clés indépendantes ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_different_keys_have_independent_buckets():
    """Les limites sont trackées indépendamment par clé."""
    rpm = 2
    for _ in range(rpm + 1):
        await _check("key-A", rpm=rpm)
    allowed_a, _ = await _check("key-A", rpm=rpm)

    # key-B n'est pas affectée
    allowed_b, _ = await _check("key-B", rpm=rpm)

    assert allowed_a is False
    assert allowed_b is True


# ─── Cache keys ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cache_keys_are_namespaced(fresh_cache):
    """Les clés Redis sont préfixées par rl:key:{id}:rpm / :rpd."""
    await _check("mykey", rpm=10, rpd=100)

    rpm_val = await fresh_cache.get("rl:key:mykey:rpm")
    rpd_val = await fresh_cache.get("rl:key:mykey:rpd")

    assert rpm_val == "1"
    assert rpd_val == "1"


@pytest.mark.asyncio
async def test_ttl_set_after_first_request(fresh_cache):
    """TTL est positionné sur les clés après la première requête."""
    await _check("mykey", rpm=10, rpd=100)

    rpm_ttl = await fresh_cache.ttl("rl:key:mykey:rpm")
    rpd_ttl = await fresh_cache.ttl("rl:key:mykey:rpd")

    assert rpm_ttl > 0
    assert rpd_ttl > 0
