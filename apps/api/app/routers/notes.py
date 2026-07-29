"""
Notes router — CRUD for structured annotations on workspaces.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from packages.db.client import require_one, safe_get_list

from ..dependencies import DB, AnalystAuth, ViewerAuth, require_scope_dep
from ..models.common import ApiResponse
from ..models.note import NoteCreate, NoteResponse, NoteUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", dependencies=[Depends(require_scope_dep("notes:read"))])
async def list_notes(
    workspace_id: str,
    auth: ViewerAuth,
    db: DB,
    pinned_only: bool = Query(False, description="Filter pinned notes only"),
    tag: str | None = Query(None, description="Filter by tag"),
):
    """List all notes for a workspace, pinned first then newest."""
    require_one(
        db.table("workspaces")
        .select("id")
        .eq("id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Workspace",
    )

    query = (
        db.table("notes")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
    )

    if pinned_only:
        query = query.eq("is_pinned", True)

    if tag:
        query = query.contains("tags", [tag])

    notes = safe_get_list(
        query.order("is_pinned", desc=True).order("created_at", desc=True).execute()
    )

    return ApiResponse(data=[NoteResponse(**n) for n in notes])


@router.post(
    "/",
    status_code=201,
    dependencies=[Depends(require_scope_dep("notes:write"))],
)
async def create_note(
    workspace_id: str,
    body: NoteCreate,
    auth: AnalystAuth,
    db: DB,
):
    """Create a new note on a workspace."""
    require_one(
        db.table("workspaces")
        .select("id")
        .eq("id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Workspace",
    )

    insert_data = {
        "workspace_id": workspace_id,
        "organization_id": auth.organization_id,
        "user_id": auth.user_id,
        **body.model_dump(),
    }

    if insert_data.get("checklist_items"):
        insert_data["checklist_items"] = [
            item.model_dump() for item in body.checklist_items
        ]

    result = db.table("notes").insert(insert_data).execute()
    created = require_one(result, "Note")

    return ApiResponse(data=NoteResponse(**created))


@router.patch(
    "/{note_id}",
    dependencies=[Depends(require_scope_dep("notes:write"))],
)
async def update_note(
    workspace_id: str,
    note_id: str,
    body: NoteUpdate,
    auth: AnalystAuth,
    db: DB,
):
    """Partial update of a note."""
    require_one(
        db.table("notes")
        .select("id")
        .eq("id", note_id)
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Note",
    )

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        existing = require_one(
            db.table("notes").select("*").eq("id", note_id).execute(),
            "Note",
        )
        return ApiResponse(data=NoteResponse(**existing))

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    if "checklist_items" in updates and updates["checklist_items"] is not None:
        updates["checklist_items"] = [
            item.model_dump() for item in body.checklist_items
        ]

    result = (
        db.table("notes")
        .update(updates)
        .eq("id", note_id)
        .eq("organization_id", auth.organization_id)
        .execute()
    )
    updated = require_one(result, "Note")

    return ApiResponse(data=NoteResponse(**updated))


@router.delete(
    "/{note_id}",
    status_code=204,
    dependencies=[Depends(require_scope_dep("notes:write"))],
)
async def delete_note(
    workspace_id: str,
    note_id: str,
    auth: AnalystAuth,
    db: DB,
):
    """Delete a note."""
    require_one(
        db.table("notes")
        .select("id")
        .eq("id", note_id)
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Note",
    )

    db.table("notes").delete().eq("id", note_id).execute()
