"""
Conftest local pour les tests de routers.

Neutralise le RateLimitMiddleware (in-memory, 60 req/min) qui cause des 429
quand tous les tests tournent en séquence sur le même `ip:127.0.0.1`.
"""

import pytest

from apps.api.app.middleware.rate_limit import RateLimitMiddleware


@pytest.fixture(autouse=True)
def disable_rate_limit(monkeypatch):
    """Patch RateLimitMiddleware.dispatch pour bypasser le rate limiting en tests."""

    async def pass_through(self, request, call_next):
        return await call_next(request)

    monkeypatch.setattr(RateLimitMiddleware, "dispatch", pass_through)
