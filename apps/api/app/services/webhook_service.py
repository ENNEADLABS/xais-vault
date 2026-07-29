"""
Webhook service — secret generation and core operations.

Note: The secret is stored in plaintext (unlike API keys which are hashed)
because the worker must read it to sign outgoing payloads.
"""

import logging
import secrets

from packages.db.client import require_one, safe_get_list

logger = logging.getLogger(__name__)

SECRET_PREFIX = "whsec_"
SECRET_HEX_BYTES = 16  # 16 bytes = 32 hex chars


def generate_webhook_secret() -> str:
    """Generate a cryptographically secure HMAC secret.

    Format: whsec_{32_hex}
    Stored in plaintext — needed to sign outgoing payloads.
    """
    return f"{SECRET_PREFIX}{secrets.token_hex(SECRET_HEX_BYTES)}"


async def create_webhook(
    db,
    *,
    url: str,
    events: list[str],
    is_active: bool,
    organization_id: str,
    created_by: str,
) -> tuple[dict, str]:
    """Insert a webhook in DB. Returns (row, secret).

    The secret is returned to the caller ONCE — store it immediately.
    """
    secret = generate_webhook_secret()
    result = (
        db.table("webhooks")
        .insert({
            "url": str(url),
            "events": events,
            "secret": secret,
            "is_active": is_active,
            "organization_id": organization_id,
            "created_by": created_by,
        })
        .execute()
    )
    row = require_one(result, "Webhook")
    return row, secret


async def rotate_webhook_secret(
    db,
    *,
    webhook_id: str,
    organization_id: str,
) -> tuple[dict, str]:
    """Regenerate the secret of a webhook. Returns (row, new_secret).

    Raises 404 if the webhook does not exist or belongs to another org.
    """
    require_one(
        db.table("webhooks")
        .select("id")
        .eq("id", webhook_id)
        .eq("organization_id", organization_id)
        .execute(),
        "Webhook",
    )
    new_secret = generate_webhook_secret()
    result = (
        db.table("webhooks")
        .update({"secret": new_secret, "updated_at": "now()"})
        .eq("id", webhook_id)
        .execute()
    )
    row = require_one(result, "Webhook")
    return row, new_secret


async def list_webhooks(
    db,
    *,
    organization_id: str,
    page: int,
    per_page: int,
) -> tuple[list[dict], int]:
    """List webhooks for an organization (without secrets). Returns (items, total)."""
    offset = (page - 1) * per_page
    result = (
        db.table("webhooks")
        .select("*", count="exact")
        .eq("organization_id", organization_id)
        .order("created_at", desc=True)
        .range(offset, offset + per_page - 1)
        .execute()
    )
    return safe_get_list(result), result.count or 0


async def list_webhook_deliveries(
    db,
    *,
    webhook_id: str,
    page: int,
    per_page: int,
) -> tuple[list[dict], int]:
    """List delivery history for a webhook. Returns (items, total)."""
    offset = (page - 1) * per_page
    result = (
        db.table("webhook_deliveries")
        .select("*", count="exact")
        .eq("webhook_id", webhook_id)
        .order("created_at", desc=True)
        .range(offset, offset + per_page - 1)
        .execute()
    )
    return safe_get_list(result), result.count or 0


def require_webhook(db, webhook_id: str, organization_id: str) -> dict:
    """Fetch webhook or raise 404."""
    return require_one(
        db.table("webhooks")
        .select("*")
        .eq("id", webhook_id)
        .eq("organization_id", organization_id)
        .execute(),
        "Webhook",
    )
