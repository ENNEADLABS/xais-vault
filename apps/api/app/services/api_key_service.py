"""
API Key service — generation, hashing, rotation.
"""

import hashlib
import logging
import secrets

from fastapi import HTTPException

from packages.db.client import require_one

logger = logging.getLogger(__name__)

KEY_PREFIX = "xv_live_"
KEY_HEX_BYTES = 16  # 16 bytes = 32 hex chars


def generate_api_key() -> tuple[str, str, str]:
    """Generate a cryptographically secure API key.

    Returns:
        (raw_key, key_hash, key_prefix)
        - raw_key: xv_live_{32_hex} — returned to caller ONCE
        - key_hash: SHA256 hex digest — stored in DB
        - key_prefix: first 8 hex chars after prefix — for display
    """
    hex_part = secrets.token_hex(KEY_HEX_BYTES)
    raw_key = f"{KEY_PREFIX}{hex_part}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = f"{KEY_PREFIX}{hex_part[:8]}"
    return raw_key, key_hash, key_prefix


async def create_api_key(
    db,
    *,
    name: str,
    scopes: list[str],
    rpm_limit: int,
    rpd_limit: int,
    organization_id: str,
    created_by: str,
) -> tuple[dict, str]:
    """Insert a new API key in DB. Returns (row, raw_key).

    raw_key must be returned to the caller immediately — it is never stored.
    """
    raw_key, key_hash, key_prefix = generate_api_key()

    result = db.table("api_keys").insert({
        "name": name,
        "key_hash": key_hash,
        "key_prefix": key_prefix,
        "scopes": scopes,
        "rpm_limit": rpm_limit,
        "rpd_limit": rpd_limit,
        "organization_id": organization_id,
        "created_by": created_by,
    }).execute()

    row = require_one(result, "API Key")
    return row, raw_key


async def rotate_api_key(
    db,
    *,
    key_id: str,
    organization_id: str,
) -> tuple[dict, str, dict]:
    """Rotate a key: deactivate old, create new with same params.

    Returns:
        (new_row, raw_key, old_row)

    Raises:
        HTTPException 400 if the key is already inactive.
    """
    old_result = (
        db.table("api_keys")
        .select("*")
        .eq("id", key_id)
        .eq("organization_id", organization_id)
        .execute()
    )
    old_row = require_one(old_result, "API Key")

    if not old_row.get("is_active"):
        raise HTTPException(
            status_code=400,
            detail="Cannot rotate an inactive key",
        )

    db.table("api_keys").update({"is_active": False}).eq("id", key_id).execute()

    new_row, raw_key = await create_api_key(
        db,
        name=old_row["name"],
        scopes=old_row["scopes"],
        rpm_limit=old_row["rpm_limit"],
        rpd_limit=old_row["rpd_limit"],
        organization_id=organization_id,
        created_by=old_row["created_by"],
    )

    return new_row, raw_key, old_row
