"""
Rate limiting middleware — 60 req/min per user.

Utilise le CacheBackend (Redis ou in-memory).
Redis (prod multi-instance) si REDIS_URL est défini.
In-memory (fallback single-instance) sinon.
"""

import hashlib
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from packages.core.config import load_config
from packages.db.redis_client import CacheBackend, get_cache

logger = logging.getLogger(__name__)

RATE_LIMIT = 60  # requests per window
WINDOW_SECONDS = 60  # 1 minute window

# Paths exemptés (health check, docs)
EXEMPT_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        rate_limit: int = RATE_LIMIT,
        window: int = WINDOW_SECONDS,
        cache: CacheBackend | None = None,
    ):
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window = window
        # Cache injecté (tests) ou global singleton (prod)
        self._cache = cache

    def _get_backend(self) -> CacheBackend:
        return self._cache if self._cache is not None else get_cache()

    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        identifier = self._get_identifier(request)
        cache = self._get_backend()
        cache_key = f"rl:global:{identifier}"

        count = await cache.incr(cache_key)
        if count == 1:
            # Première requête dans la fenêtre — set TTL
            await cache.expire(cache_key, self.window)

        if count > self.rate_limit:
            ttl = await cache.ttl(cache_key)
            retry_in = max(0, ttl)
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": 429,
                        "message": f"Too many requests. Retry in {retry_in}s.",
                    }
                },
                headers={
                    "Retry-After": str(retry_in),
                    "X-RateLimit-Limit": str(self.rate_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_in),
                },
            )

        response = await call_next(request)
        remaining = max(0, self.rate_limit - count)
        response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    def _get_identifier(self, request: Request) -> str:
        """Extrait l'identifiant user depuis JWT, API key ou IP.

        Tokens et API keys sont hashés SHA-256 (pas de partial-match exploitable,
        pas de leak du token tronqué dans les logs/keys Redis).
        """
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return "jwt:" + hashlib.sha256(token.encode()).hexdigest()[:24]

        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            return "key:" + hashlib.sha256(api_key.encode()).hexdigest()[:24]

        return f"ip:{self._client_ip(request)}"

    @staticmethod
    def _client_ip(request: Request) -> str:
        """Résout l'IP client en tenant compte du trusted proxy.

        En prod (derrière Render), le vrai IP client est le DERNIER élément
        de X-Forwarded-For — chaque proxy ajoute son IP en bout de chaîne.
        Prendre le premier permettrait à un client de spoofer son IP et de
        contourner le rate limit en envoyant `X-Forwarded-For: 1.2.3.4`.
        """
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            env = load_config().environment
            parts = [p.strip() for p in forwarded_for.split(",") if p.strip()]
            if parts:
                return parts[-1] if env == "production" else parts[0]
        return request.client.host if request.client else "unknown"
