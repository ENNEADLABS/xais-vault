"""
Tests for rate limiting middleware (apps/api/app/middleware/rate_limit.py).

Utilise InMemoryCacheBackend injecté pour isoler chaque test.
"""

from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from apps.api.app.middleware.rate_limit import EXEMPT_PATHS, RateLimitMiddleware
from packages.db.redis_client import InMemoryCacheBackend


def _create_app(rate_limit: int = 5, window: int = 60) -> FastAPI:
    """Crée une app FastAPI minimale avec rate limiting — backend isolé par instance."""
    app = FastAPI()
    # Chaque app reçoit son propre backend in-memory → isolation entre tests
    cache = InMemoryCacheBackend()
    app.add_middleware(
        RateLimitMiddleware, rate_limit=rate_limit, window=window, cache=cache
    )

    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app


@pytest_asyncio.fixture
async def client():
    app = _create_app(rate_limit=5, window=60)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# ─── Basic rate limiting ──────────────────────────────────────


@pytest.mark.asyncio
class TestRateLimiting:
    async def test_requests_under_limit_pass(self, client):
        """Requests under the limit return 200."""
        for _ in range(5):
            r = await client.get("/test")
            assert r.status_code == 200

    async def test_request_over_limit_returns_429(self, client):
        """Request exceeding limit returns 429 with Retry-After."""
        for _ in range(5):
            await client.get("/test")

        r = await client.get("/test")
        assert r.status_code == 429
        assert "Retry-After" in r.headers
        assert r.json()["error"]["code"] == 429

    async def test_rate_limit_headers_present(self, client):
        """Successful responses include X-RateLimit headers."""
        r = await client.get("/test")
        assert r.status_code == 200
        assert "X-RateLimit-Limit" in r.headers
        assert "X-RateLimit-Remaining" in r.headers
        assert r.headers["X-RateLimit-Limit"] == "5"
        assert r.headers["X-RateLimit-Remaining"] == "4"

    async def test_remaining_decrements(self, client):
        """X-RateLimit-Remaining decrements with each request."""
        for i in range(5):
            r = await client.get("/test")
            assert r.headers["X-RateLimit-Remaining"] == str(4 - i)


# ─── Exempt paths ─────────────────────────────────────────────


@pytest.mark.asyncio
class TestExemptPaths:
    async def test_health_exempt(self, client):
        """Health endpoint is not rate limited."""
        for _ in range(10):
            r = await client.get("/health")
            assert r.status_code == 200
        assert "X-RateLimit-Limit" not in r.headers

    async def test_exempt_paths_list(self):
        """All expected paths are exempt."""
        assert "/health" in EXEMPT_PATHS
        assert "/docs" in EXEMPT_PATHS
        assert "/openapi.json" in EXEMPT_PATHS


# ─── Identifier extraction ────────────────────────────────────


@pytest.mark.asyncio
class TestIdentifier:
    async def test_jwt_users_tracked_separately(self):
        """Different JWT tokens get separate rate limit buckets."""
        app = _create_app(rate_limit=2, window=60)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            # User A: 2 requests → exhausts limit
            for _ in range(2):
                r = await c.get(
                    "/test",
                    headers={
                        "Authorization": "Bearer token_aaaaaaaaaaaaaaaaaaaaaaaaaaaaAAAA"
                    },
                )
                assert r.status_code == 200

            # User A: 3rd request → 429
            r = await c.get(
                "/test",
                headers={
                    "Authorization": "Bearer token_aaaaaaaaaaaaaaaaaaaaaaaaaaaaAAAA"
                },
            )
            assert r.status_code == 429

            # User B: still has quota
            r = await c.get(
                "/test",
                headers={
                    "Authorization": "Bearer token_bbbbbbbbbbbbbbbbbbbbbbbbbbbbBBBB"
                },
            )
            assert r.status_code == 200

    async def test_api_key_identifier(self):
        """X-API-Key header creates a separate bucket."""
        app = _create_app(rate_limit=2, window=60)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            for _ in range(2):
                r = await c.get("/test", headers={"X-API-Key": "key123456"})
                assert r.status_code == 200

            r = await c.get("/test", headers={"X-API-Key": "key123456"})
            assert r.status_code == 429


# ─── Window reset ─────────────────────────────────────────────


@pytest.mark.asyncio
class TestWindowReset:
    async def test_fresh_app_has_clean_state(self):
        """Chaque app avec son propre backend a un état vierge."""
        app1 = _create_app(rate_limit=2, window=60)
        app2 = _create_app(rate_limit=2, window=60)

        async with AsyncClient(
            transport=ASGITransport(app=app1), base_url="http://test"
        ) as c1:
            # Exhaust app1
            for _ in range(2):
                await c1.get("/test")
            r = await c1.get("/test")
            assert r.status_code == 429

        # app2 a son propre backend — pas affecté par app1
        async with AsyncClient(
            transport=ASGITransport(app=app2), base_url="http://test"
        ) as c2:
            r = await c2.get("/test")
            assert r.status_code == 200


# ─── Identifier extraction (unit) ────────────────────────────


class TestIdentifierExtraction:
    def test_ip_fallback_when_no_auth(self):
        """No Authorization / X-API-Key → identifier is ip:{client_host}."""
        mw = RateLimitMiddleware(MagicMock())
        request = MagicMock()
        request.headers.get.side_effect = lambda key, default="": {
            "Authorization": "",
            "X-API-Key": "",
        }.get(key, default)
        request.client.host = "203.0.113.1"

        identifier = mw._get_identifier(request)
        assert identifier == "ip:203.0.113.1"

    def test_api_key_identifier_is_sha256_hashed(self):
        """X-API-Key is SHA-256 hashed (no partial-match, no leak, stable per key)."""
        import hashlib

        mw = RateLimitMiddleware(MagicMock())

        def _identifier_for(key: str) -> str:
            request = MagicMock()
            request.headers.get.side_effect = lambda k, default="": {
                "Authorization": "",
                "X-API-Key": key,
            }.get(k, default)
            return mw._get_identifier(request)

        key = "abcdefghijklmnop_secret_suffix"
        expected = "key:" + hashlib.sha256(key.encode()).hexdigest()[:24]
        assert _identifier_for(key) == expected
        # Stability: same key → same identifier
        assert _identifier_for(key) == _identifier_for(key)
        # Distinctness: different keys → different identifiers
        assert _identifier_for(key) != _identifier_for(key + "x")
        # No leak: raw key must not appear in the identifier
        assert key not in _identifier_for(key)

    def test_jwt_identifier_is_sha256_hashed(self):
        """Bearer token is SHA-256 hashed (prevents re-login bypass via token rotation)."""
        import hashlib

        mw = RateLimitMiddleware(MagicMock())
        token = "A" * 10 + "B" * 32
        request = MagicMock()
        request.headers.get.side_effect = lambda k, default="": {
            "Authorization": f"Bearer {token}",
            "X-API-Key": "",
        }.get(k, default)

        expected = "jwt:" + hashlib.sha256(token.encode()).hexdigest()[:24]
        assert mw._get_identifier(request) == expected
        # Raw token must not leak in the identifier
        assert token not in mw._get_identifier(request)

    def test_xff_takes_last_ip_in_production(self, monkeypatch):
        """X-Forwarded-For spoofing: in prod, trust the LAST IP (set by Render), not the first."""
        from types import SimpleNamespace

        import apps.api.app.middleware.rate_limit as rate_limit_mod

        monkeypatch.setattr(
            rate_limit_mod,
            "load_config",
            lambda: SimpleNamespace(environment="production"),
        )
        mw = RateLimitMiddleware(MagicMock())
        request = MagicMock()
        # Attacker spoofs 1.2.3.4 as first entry; real client IP (203.0.113.1) is last.
        request.headers.get.side_effect = lambda k, default="": {
            "Authorization": "",
            "X-API-Key": "",
            "X-Forwarded-For": "1.2.3.4, 10.0.0.1, 203.0.113.1",
        }.get(k, default)
        request.client.host = "10.0.0.1"

        identifier = mw._get_identifier(request)
        assert identifier == "ip:203.0.113.1"
        assert "1.2.3.4" not in identifier
