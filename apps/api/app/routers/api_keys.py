"""
API Keys router — CRUD for programmatic access keys.

Auth: JWT only. API keys cannot manage API keys (anti-privilege-escalation).
Roles: admin or analyst.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from packages.db.client import require_one, safe_get_list

from ..dependencies import DB, AnalystAuth
from ..models.api_key import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyResponse,
    ApiKeyUpdate,
    ApiKeyWithUsage,
)
from ..models.common import ApiResponse, PaginatedResponse
from ..services.api_key_service import (
    create_api_key as svc_create,
)
from ..services.api_key_service import (
    rotate_api_key as svc_rotate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _require_jwt(auth) -> None:
    """Reject API key auth — no self-service key management."""
    if auth.auth_method != "jwt":
        raise HTTPException(
            status_code=403,
            detail="API key management requires JWT authentication",
        )


@router.post("/", status_code=201)
async def create_api_key(body: ApiKeyCreate, auth: AnalystAuth, db: DB):
    """Create a new API key. Returns the secret ONCE — store it immediately."""
    _require_jwt(auth)
    row, raw_key = await svc_create(
        db,
        name=body.name,
        scopes=body.scopes,
        rpm_limit=body.rpm_limit,
        rpd_limit=body.rpd_limit,
        organization_id=auth.organization_id,
        created_by=auth.user_id,
    )
    return ApiResponse(data=ApiKeyCreated(**row, key=raw_key))


@router.get("/")
async def list_api_keys(
    auth: AnalystAuth,
    db: DB,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List API keys for the organization (without secrets)."""
    _require_jwt(auth)
    offset = (page - 1) * per_page
    result = (
        db.table("api_keys")
        .select("*", count="exact")
        .eq("organization_id", auth.organization_id)
        .order("created_at", desc=True)
        .range(offset, offset + per_page - 1)
        .execute()
    )
    keys = safe_get_list(result)
    total = result.count or 0
    pages = (total + per_page - 1) // per_page if total > 0 else 0
    return PaginatedResponse(
        data=[ApiKeyResponse(**k) for k in keys],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{key_id}")
async def get_api_key(key_id: str, auth: AnalystAuth, db: DB):
    """Get API key detail with usage stats."""
    _require_jwt(auth)
    row = require_one(
        db.table("api_keys")
        .select("*")
        .eq("id", key_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "API Key",
    )
    return ApiResponse(data=ApiKeyWithUsage(**row, usage_today=0, usage_this_month=0))


@router.patch("/{key_id}")
async def update_api_key(key_id: str, body: ApiKeyUpdate, auth: AnalystAuth, db: DB):
    """Update API key metadata."""
    _require_jwt(auth)
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = (
        db.table("api_keys")
        .update(updates)
        .eq("id", key_id)
        .eq("organization_id", auth.organization_id)
        .execute()
    )
    row = require_one(result, "API Key")
    return ApiResponse(data=ApiKeyResponse(**row))


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(key_id: str, auth: AnalystAuth, db: DB):
    """Revoke an API key (soft delete: is_active=false)."""
    _require_jwt(auth)
    require_one(
        db.table("api_keys")
        .select("id")
        .eq("id", key_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "API Key",
    )
    db.table("api_keys").update({"is_active": False}).eq("id", key_id).execute()


@router.post("/{key_id}/rotate", status_code=201)
async def rotate_api_key(key_id: str, auth: AnalystAuth, db: DB):
    """Rotate: deactivate old key, create new with same params. Returns new secret ONCE."""
    _require_jwt(auth)
    new_row, raw_key, _ = await svc_rotate(
        db,
        key_id=key_id,
        organization_id=auth.organization_id,
    )
    return ApiResponse(data=ApiKeyCreated(**new_row, key=raw_key))
