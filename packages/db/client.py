"""
Supabase client — shared between API and Worker.
Service role key for backend operations (bypasses RLS).
Anon key NOT used server-side.

CRITICAL: Never use .single() — it throws unrecoverable exceptions
on 0 results. Always use .execute() + explicit check.
"""

import logging
import os
from functools import lru_cache

from supabase import Client, create_client

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Get singleton Supabase client (service role)."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required")
    return create_client(url, key)


# ─── Safe query helpers ────────────────────────────────────


def safe_get_one(result) -> dict | None:
    """Safely get one row from a Supabase query result.

    NEVER use .single(). This is the safe alternative.
    Returns None if no rows, first row if found.
    """
    if not result.data:
        return None
    return result.data[0]


def safe_get_list(result) -> list[dict]:
    """Safely get a list of rows from a Supabase query result."""
    return result.data or []


def require_one(result, entity: str = "Record") -> dict:
    """Get exactly one row or raise 404.

    Usage:
        row = require_one(
            supabase.table("workspaces").select("*").eq("id", id).execute(),
            "Workspace"
        )
    """
    from fastapi import HTTPException
    row = safe_get_one(result)
    if not row:
        raise HTTPException(status_code=404, detail=f"{entity} not found")
    return row


# ─── Pagination helper ─────────────────────────────────────


def paginate(query, *, page: int = 1, per_page: int = 20):
    """Apply pagination to a Supabase query.

    Usage:
        query = supabase.table("workspaces").select("*", count="exact")
        query = paginate(query, page=2, per_page=20)
        result = query.execute()
        # result.count = total rows, result.data = page rows
    """
    offset = (page - 1) * per_page
    return query.range(offset, offset + per_page - 1)
