"""
JWT authentication cache and verification — extracted from auth.py.
"""

import hashlib
import logging
import time
from dataclasses import dataclass

import sentry_sdk
from fastapi import HTTPException

from supabase import Client

logger = logging.getLogger(__name__)

# ─── Cache JWT ─────────────────────────────────────────────────
# TTL court (30s) — trade-off acceptable : un token révoqué reste
# valide au pire 30s. Réduit ~1 appel HTTP Supabase par requête.

_JWT_CACHE_TTL = 30  # secondes
_JWT_CACHE_MAX_SIZE = 1000
_jwt_cache: dict[str, tuple["AuthContext", float]] = {}


@dataclass
class AuthContext:
    """Authenticated user context, attached to every request."""

    user_id: str
    email: str | None = None
    organization_id: str | None = None  # Resolved from org membership
    role: str | None = None  # admin, analyst, viewer
    auth_method: str = "jwt"  # jwt or api_key
    api_key_id: str | None = None  # If authenticated via API key
    scopes: list[str] | None = None  # API key scopes


async def _authenticate_jwt(token: str, supabase_client: Client) -> "AuthContext":
    """Verify JWT via Supabase Auth API.

    Uses supabase.auth.get_user(token) which validates the token server-side.
    Handles all signing algorithms automatically (HS256, RS256, EdDSA).

    Cache TTL=30s : réduit ~1 appel HTTP Supabase sur les requêtes répétées.
    """
    cache_key = hashlib.sha256(token.encode()).hexdigest()
    now = time.monotonic()

    cached = _jwt_cache.get(cache_key)
    if cached and now - cached[1] < _JWT_CACHE_TTL:
        return cached[0]

    try:
        with sentry_sdk.start_span(op="auth.jwt_verify", name="Supabase JWT verify"):
            response = supabase_client.auth.get_user(token)
    except Exception as e:
        logger.warning("JWT verification failed via Supabase: %s", e)
        raise HTTPException(status_code=401, detail="Invalid token")

    if not response or not response.user:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = response.user
    auth_ctx = AuthContext(
        user_id=user.id,
        email=user.email,
        auth_method="jwt",
    )

    _jwt_cache[cache_key] = (auth_ctx, now)

    # Nettoyage périodique pour éviter une fuite mémoire
    if len(_jwt_cache) > _JWT_CACHE_MAX_SIZE:
        expired = [k for k, (_, t) in _jwt_cache.items() if now - t > _JWT_CACHE_TTL]
        for k in expired:
            del _jwt_cache[k]

    return auth_ctx
