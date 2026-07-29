"""
Authentication service — JWT verification + API key validation.

CRITICAL: JWT signatures are ALWAYS verified. No exceptions.
This was a security flaw in the previous project. Never regress.

Two auth paths:
  1. JWT (Supabase Auth) — for frontend users
  2. API Key (X-API-Key header) — for programmatic access

Priority: X-API-Key > Authorization Bearer > 401
"""

import hashlib
import logging

from fastapi import HTTPException, Request

from supabase import Client

from .auth_jwt import (  # noqa: F401
    _JWT_CACHE_MAX_SIZE,
    AuthContext,
    _authenticate_jwt,
    _jwt_cache,
)
from .auth_org import resolve_organization  # noqa: F401

logger = logging.getLogger(__name__)

# Re-exports for backward compatibility
__all__ = [
    "AuthContext",
    "authenticate",
    "resolve_organization",
    "require_role",
    "require_scope",
    "_jwt_cache",
]


async def authenticate(request: Request, supabase_client: Client) -> AuthContext:
    """Authenticate a request. Returns AuthContext or raises 401/403.

    JWT verification delegated to Supabase Auth API — handles all signing
    algorithms (HS256, RS256, EdDSA) without needing a local secret.
    """
    # Path 1: API Key
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return await _authenticate_api_key(api_key, supabase_client)

    # Path 2: JWT via Supabase
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return await _authenticate_jwt(token, supabase_client)

    raise HTTPException(status_code=401, detail="Authentication required")


async def _authenticate_api_key(raw_key: str, supabase_client) -> AuthContext:
    """Validate an API key against the database.

    Keys are stored as SHA256 hashes. We hash the incoming key
    and look it up. Never store or log the raw key.
    """
    if not raw_key.startswith("xv_live_") and not raw_key.startswith("xv_test_"):
        raise HTTPException(status_code=401, detail="Invalid API key format")

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    # Look up the key — NEVER use .single()
    result = (
        supabase_client.table("api_keys")
        .select(
            "id, organization_id, scopes, rpm_limit, rpd_limit, is_active, created_by"
        )
        .eq("key_hash", key_hash)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid API key")

    key_data = result.data[0]

    if not key_data.get("is_active"):
        raise HTTPException(status_code=403, detail="API key is deactivated")

    # Update last_used_at (fire and forget, don't block auth)
    try:
        supabase_client.table("api_keys").update({"last_used_at": "now()"}).eq(
            "id", key_data["id"]
        ).execute()
    except Exception:
        pass  # Non-critical, don't fail auth

    # Per-key rate limiting (RPM + RPD)
    from .api_key_rate_limit import check_api_key_rate_limit

    allowed, error_msg = await check_api_key_rate_limit(
        api_key_id=key_data["id"],
        rpm_limit=key_data.get("rpm_limit", 60),
        rpd_limit=key_data.get("rpd_limit", 1000),
    )
    if not allowed:
        raise HTTPException(status_code=429, detail=error_msg)

    return AuthContext(
        user_id=key_data["created_by"],
        organization_id=key_data["organization_id"],
        auth_method="api_key",
        api_key_id=key_data["id"],
        scopes=key_data.get("scopes", ["*"]),
    )


def require_role(auth: AuthContext, allowed_roles: list[str]) -> None:
    """Check that the user has one of the allowed roles. Raises 403 if not."""
    if not auth.role or auth.role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Insufficient permissions. Required: {', '.join(allowed_roles)}",
        )


def require_scope(auth: AuthContext, required_scope: str) -> None:
    """Check that the API key has the required scope. Raises 403 if not."""
    if auth.auth_method != "api_key":
        return  # JWT users have full access
    if auth.scopes and "*" in auth.scopes:
        return  # Wildcard scope
    if auth.scopes and required_scope not in auth.scopes:
        raise HTTPException(
            status_code=403,
            detail=f"API key missing required scope: {required_scope}",
        )
