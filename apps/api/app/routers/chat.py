"""
Chat router — RAG chat with SSE streaming + session CRUD.

SSE streaming logic extracted to services/sse.py.
Session/persistence logic in services/chat_session.py.
RAG context logic in services/chat_rag.py.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from packages.db.client import require_one, safe_get_list

from ..dependencies import DB, AnalystAuth, ViewerAuth, require_scope_dep
from ..models.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionRename,
    ChatSessionResponse,
)
from ..models.common import ApiResponse
from ..services.chat_rag import prepare_context
from ..services.chat_session import get_or_create_session
from ..services.sse import build_chat_event_stream

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", dependencies=[Depends(require_scope_dep("chat:write"))])
async def send_message(
    workspace_id: str,
    body: ChatMessageRequest,
    auth: AnalystAuth,
    db: DB,
):
    """Send a chat message and stream the AI response via SSE."""
    require_one(
        db.table("workspaces")
        .select("id")
        .eq("id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Workspace",
    )

    session_id = await get_or_create_session(
        db,
        session_id=body.session_id,
        workspace_id=workspace_id,
        organization_id=auth.organization_id,
        user_id=auth.user_id,
        first_message=body.content,
    )

    context = await prepare_context(
        db,
        query=body.content,
        workspace_id=workspace_id,
        organization_id=auth.organization_id,
        session_id=session_id,
        source_ids=body.source_ids,
    )

    return StreamingResponse(
        build_chat_event_stream(
            context=context,
            session_id=session_id,
            organization_id=auth.organization_id,
            user_content=body.content,
            db=db,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Session CRUD ─────────────────────────────────────────────


@router.get("/sessions", dependencies=[Depends(require_scope_dep("chat:read"))])
async def list_sessions(workspace_id: str, auth: ViewerAuth, db: DB):
    """List all chat sessions for a workspace, newest first."""
    sessions = safe_get_list(
        db.table("chat_sessions")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .order("updated_at", desc=True)
        .execute()
    )
    return ApiResponse(data=[ChatSessionResponse(**s) for s in sessions])


@router.get(
    "/sessions/{session_id}",
    dependencies=[Depends(require_scope_dep("chat:read"))],
)
async def get_session(workspace_id: str, session_id: str, auth: ViewerAuth, db: DB):
    """Get a chat session with its full message history."""
    session = require_one(
        db.table("chat_sessions")
        .select("*")
        .eq("id", session_id)
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Chat session",
    )

    messages = safe_get_list(
        db.table("chat_messages")
        .select("*")
        .eq("session_id", session_id)
        .eq("organization_id", auth.organization_id)
        .order("created_at", desc=False)
        .execute()
    )

    return ApiResponse(
        data={
            "session": ChatSessionResponse(**session),
            "messages": [ChatMessageResponse(**m) for m in messages],
        },
    )


@router.patch(
    "/sessions/{session_id}",
    dependencies=[Depends(require_scope_dep("chat:write"))],
)
async def rename_session(
    workspace_id: str,
    session_id: str,
    body: ChatSessionRename,
    auth: AnalystAuth,
    db: DB,
):
    """Rename a chat session."""
    require_one(
        db.table("chat_sessions")
        .select("id")
        .eq("id", session_id)
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Chat session",
    )

    result = (
        db.table("chat_sessions")
        .update(
            {
                "title": body.title,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", session_id)
        .execute()
    )

    session = require_one(result, "Chat session")
    return ApiResponse(data=ChatSessionResponse(**session))


@router.delete(
    "/sessions/{session_id}",
    status_code=204,
    dependencies=[Depends(require_scope_dep("chat:write"))],
)
async def delete_session(workspace_id: str, session_id: str, auth: AnalystAuth, db: DB):
    """Delete a chat session and all its messages (CASCADE)."""
    require_one(
        db.table("chat_sessions")
        .select("id")
        .eq("id", session_id)
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Chat session",
    )
    db.table("chat_sessions").delete().eq("id", session_id).execute()
