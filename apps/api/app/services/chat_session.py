"""
Chat session management — create, persist messages, update.

Extracted from chat_engine.py for the 200-line-per-file rule.
"""

import logging
from datetime import datetime, timezone

from packages.db.client import safe_get_one
from packages.llm.types import LLMUsage

logger = logging.getLogger(__name__)


async def get_or_create_session(
    db,
    *,
    session_id: str | None,
    workspace_id: str,
    organization_id: str,
    user_id: str,
    first_message: str,
) -> str:
    """Get existing session or create a new one.

    For new sessions, auto-generates a title from the first message.
    """
    if session_id:
        result = (
            db.table("chat_sessions")
            .select("id")
            .eq("id", session_id)
            .eq("workspace_id", workspace_id)
            .eq("organization_id", organization_id)
            .execute()
        )
        session = safe_get_one(result)
        if not session:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Chat session not found")
        return session_id

    title = first_message[:80].strip()
    if len(first_message) > 80:
        title += "..."

    now = datetime.now(timezone.utc).isoformat()
    result = db.table("chat_sessions").insert({
        "workspace_id": workspace_id,
        "organization_id": organization_id,
        "user_id": user_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
    }).execute()

    session = safe_get_one(result)
    if not session:
        raise RuntimeError("Failed to create chat session")

    return session["id"]


async def persist_messages(
    db,
    *,
    session_id: str,
    organization_id: str,
    user_content: str,
    assistant_content: str,
    citations: list[dict],
    usage: LLMUsage | None,
) -> tuple[dict, dict]:
    """Save both the user message and assistant response to DB."""
    now = datetime.now(timezone.utc).isoformat()

    user_result = db.table("chat_messages").insert({
        "session_id": session_id,
        "organization_id": organization_id,
        "role": "user",
        "content": user_content,
        "created_at": now,
    }).execute()

    assistant_data: dict = {
        "session_id": session_id,
        "organization_id": organization_id,
        "role": "assistant",
        "content": assistant_content,
        "citations": citations if citations else None,
        "created_at": now,
    }

    if usage:
        assistant_data.update({
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cost_usd": float(usage.cost_usd),
            "model_used": usage.model,
        })

    assistant_result = db.table("chat_messages").insert(assistant_data).execute()

    user_msg = safe_get_one(user_result) or {}
    assistant_msg = safe_get_one(assistant_result) or {}

    db.table("chat_sessions").update({
        "updated_at": now,
    }).eq("id", session_id).execute()

    return user_msg, assistant_msg
