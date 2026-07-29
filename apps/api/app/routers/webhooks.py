"""
Webhooks router — CRUD + rotate-secret + deliveries + test event.

Auth: JWT only (admin or analyst). API keys cannot manage webhooks.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from packages.db.client import require_one
from packages.db.job_queue import create_job

from ..dependencies import DB, AnalystAuth
from ..models.common import ApiResponse, JobAccepted, PaginatedResponse
from ..models.webhook import (
    WebhookCreate,
    WebhookCreated,
    WebhookDeliveryResponse,
    WebhookResponse,
    WebhookUpdate,
)
from ..services.webhook_service import (
    create_webhook as svc_create,
)
from ..services.webhook_service import (
    list_webhook_deliveries as svc_list_deliveries,
)
from ..services.webhook_service import (
    list_webhooks as svc_list_webhooks,
)
from ..services.webhook_service import (
    require_webhook as _require_webhook,
)
from ..services.webhook_service import (
    rotate_webhook_secret as svc_rotate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _require_jwt(auth) -> None:
    """Reject API key auth — webhook management requires JWT."""
    if auth.auth_method != "jwt":
        raise HTTPException(
            status_code=403,
            detail="Webhook management requires JWT authentication",
        )


# ─── POST / ───────────────────────────────────────────────────────────────────


@router.post("/", status_code=201)
async def create_webhook(body: WebhookCreate, auth: AnalystAuth, db: DB):
    """Create a webhook. Returns the secret ONCE — store it immediately."""
    _require_jwt(auth)
    row, secret = await svc_create(
        db,
        url=str(body.url),
        events=body.events,
        is_active=body.is_active,
        organization_id=auth.organization_id,
        created_by=auth.user_id,
    )
    row_data = {k: v for k, v in row.items() if k != "secret"}
    return ApiResponse(data=WebhookCreated(**row_data, secret=secret))


# ─── GET / ────────────────────────────────────────────────────────────────────


@router.get("/")
async def list_webhooks(
    auth: AnalystAuth,
    db: DB,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List webhooks for the organization (without secrets)."""
    _require_jwt(auth)
    items, total = await svc_list_webhooks(
        db, organization_id=auth.organization_id, page=page, per_page=per_page
    )
    pages = (total + per_page - 1) // per_page if total > 0 else 0
    return PaginatedResponse(
        data=[WebhookResponse(**w) for w in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


# ─── GET /{webhook_id} ────────────────────────────────────────────────────────


@router.get("/{webhook_id}")
async def get_webhook(webhook_id: str, auth: AnalystAuth, db: DB):
    """Get webhook detail (without secret)."""
    _require_jwt(auth)
    row = _require_webhook(db, webhook_id, auth.organization_id)
    return ApiResponse(data=WebhookResponse(**row))


# ─── PATCH /{webhook_id} ──────────────────────────────────────────────────────


@router.patch("/{webhook_id}")
async def update_webhook(
    webhook_id: str, body: WebhookUpdate, auth: AnalystAuth, db: DB
):
    """Update webhook url, events, or is_active."""
    _require_jwt(auth)
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "url" in updates:
        updates["url"] = str(updates["url"])
    updates["updated_at"] = "now()"
    result = (
        db.table("webhooks")
        .update(updates)
        .eq("id", webhook_id)
        .eq("organization_id", auth.organization_id)
        .execute()
    )
    row = require_one(result, "Webhook")
    return ApiResponse(data=WebhookResponse(**row))


# ─── DELETE /{webhook_id} ─────────────────────────────────────────────────────


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(webhook_id: str, auth: AnalystAuth, db: DB):
    """Delete a webhook and its delivery history (CASCADE)."""
    _require_jwt(auth)
    _require_webhook(db, webhook_id, auth.organization_id)
    db.table("webhooks").delete().eq("id", webhook_id).execute()


# ─── POST /{webhook_id}/rotate-secret ─────────────────────────────────────────


@router.post("/{webhook_id}/rotate-secret", status_code=201)
async def rotate_secret(webhook_id: str, auth: AnalystAuth, db: DB):
    """Regenerate the webhook secret. Returns the new secret ONCE."""
    _require_jwt(auth)
    row, new_secret = await svc_rotate(
        db,
        webhook_id=webhook_id,
        organization_id=auth.organization_id,
    )
    row_data = {k: v for k, v in row.items() if k != "secret"}
    return ApiResponse(data=WebhookCreated(**row_data, secret=new_secret))


# ─── GET /{webhook_id}/deliveries ─────────────────────────────────────────────


@router.get("/{webhook_id}/deliveries")
async def list_deliveries(
    webhook_id: str,
    auth: AnalystAuth,
    db: DB,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List delivery history for a webhook."""
    _require_jwt(auth)
    _require_webhook(db, webhook_id, auth.organization_id)
    items, total = await svc_list_deliveries(
        db, webhook_id=webhook_id, page=page, per_page=per_page
    )
    pages = (total + per_page - 1) // per_page if total > 0 else 0
    return PaginatedResponse(
        data=[WebhookDeliveryResponse(**d) for d in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


# ─── POST /{webhook_id}/test ──────────────────────────────────────────────────


@router.post("/{webhook_id}/test", status_code=202)
async def send_test_event(webhook_id: str, auth: AnalystAuth, db: DB):
    """Dispatch a webhook.test event to verify the endpoint is reachable."""
    _require_jwt(auth)
    _require_webhook(db, webhook_id, auth.organization_id)
    job = await create_job(
        db,
        type="dispatch_webhook",
        payload={
            "webhook_id": webhook_id,
            "event_type": "webhook.test",
            "payload": {
                "event": "webhook.test",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {"message": "This is a test webhook delivery"},
            },
            "organization_id": auth.organization_id,
        },
        organization_id=auth.organization_id,
    )
    return ApiResponse(data=JobAccepted(job_id=job["id"]))
