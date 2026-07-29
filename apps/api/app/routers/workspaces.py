"""
Workspaces router — CRUD for workspaces.
All queries filter by organization_id (defense in depth, on top of RLS).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from packages.db.client import require_one, safe_get_list
from packages.db.job_queue import create_job

from ..dependencies import DB, AnalystAuth, ViewerAuth, require_scope_dep
from ..models.common import ApiResponse, PaginatedResponse
from ..models.workspace import (
    ScanRequest,
    WorkspaceCreate,
    WorkspaceListItem,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from ..services.plan_limits import check_analysis_limit, check_workspace_limit
from ..services.suggested_questions_service import get_workspace_suggested_questions

router = APIRouter()


@router.post(
    "/",
    status_code=201,
    dependencies=[Depends(require_scope_dep("workspaces:write"))],
)
async def create_workspace(body: WorkspaceCreate, auth: AnalystAuth, db: DB):
    """Create a new workspace. Requires analyst or admin role."""
    await check_workspace_limit(db, auth.organization_id)
    result = (
        db.table("workspaces")
        .insert(
            {
                "name": body.name,
                "emoji": body.emoji,
                "description": body.description,
                "deal_type": body.deal_type,
                "sector": body.sector,
                "target_company": body.target_company,
                "organization_id": auth.organization_id,
                "created_by": auth.user_id,
            }
        )
        .execute()
    )

    workspace = require_one(result, "Workspace")
    return ApiResponse(data=WorkspaceResponse(**workspace, source_count=0, insight_count=0))


@router.get("/", dependencies=[Depends(require_scope_dep("workspaces:read"))])
async def list_workspaces(
    auth: ViewerAuth,
    db: DB,
    status: str | None = Query(None, pattern=r"^(active|archived|closed)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List workspaces in the current organization."""
    # Utilise la vue workspaces_with_counts — 1 query au lieu de 1 + 2N
    query = (
        db.table("workspaces_with_counts")
        .select("*", count="exact")
        .eq("organization_id", auth.organization_id)
        .order("updated_at", desc=True)
    )

    if status:
        query = query.eq("status", status)

    offset = (page - 1) * per_page
    query = query.range(offset, offset + per_page - 1)
    result = query.execute()

    workspaces = safe_get_list(result)
    total = result.count or 0

    return PaginatedResponse(
        data=[WorkspaceListItem(**d) for d in workspaces],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.get("/{workspace_id}", dependencies=[Depends(require_scope_dep("workspaces:read"))])
async def get_workspace(workspace_id: str, auth: ViewerAuth, db: DB):
    """Get a single workspace with counts."""
    # Utilise la vue workspaces_with_counts — source_count/insight_count inclus
    workspace = require_one(
        db.table("workspaces_with_counts")
        .select("*")
        .eq("id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Workspace",
    )

    return ApiResponse(data=WorkspaceResponse(**workspace))


@router.patch(
    "/{workspace_id}",
    dependencies=[Depends(require_scope_dep("workspaces:write"))],
)
async def update_workspace(workspace_id: str, body: WorkspaceUpdate, auth: AnalystAuth, db: DB):
    """Update a workspace. Requires analyst or admin role."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = (
        db.table("workspaces")
        .update(updates)
        .eq("id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute()
    )

    workspace = require_one(result, "Workspace")
    return ApiResponse(data=workspace)


@router.delete(
    "/{workspace_id}",
    status_code=204,
    dependencies=[Depends(require_scope_dep("workspaces:write"))],
)
async def delete_workspace(workspace_id: str, auth: AnalystAuth, db: DB):
    """Delete a workspace and all its children (CASCADE)."""
    # Verify it exists and belongs to the org
    require_one(
        db.table("workspaces")
        .select("id")
        .eq("id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Workspace",
    )

    db.table("workspaces").delete().eq("id", workspace_id).execute()


@router.post(
    "/{workspace_id}/scan",
    status_code=202,
    dependencies=[Depends(require_scope_dep("workspaces:write"))],
)
async def launch_scan(workspace_id: str, body: ScanRequest, auth: AnalystAuth, db: DB):
    """Lancer un scan DD manuellement."""
    workspace = require_one(
        db.table("workspaces")
        .select("id, scan_status")
        .eq("id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Workspace",
    )

    if workspace["scan_status"] == "scanning":
        raise HTTPException(400, "Scan already in progress")

    await check_analysis_limit(db, auth.organization_id)

    db.table("workspaces").update({"scan_status": "scanning"}).eq("id", workspace_id).execute()

    job = await create_job(
        db,
        type="scan_workspace",
        payload={
            "workspace_id": workspace_id,
            "organization_id": auth.organization_id,
            "mode": body.mode,
        },
        organization_id=auth.organization_id,
    )

    return ApiResponse(data={"job_id": job["id"], "mode": body.mode})


# ─── Suggested questions ───────────────────────────────────────


class SuggestedQuestion(BaseModel):
    """Aggregated question surfaced in the Studio as an exploration entry point."""

    question: str
    source_id: str
    source_name: str


@router.get(
    "/{workspace_id}/suggested-questions",
    response_model=list[SuggestedQuestion],
    dependencies=[Depends(require_scope_dep("workspaces:read"))],
)
async def list_suggested_questions(
    workspace_id: str,
    auth: ViewerAuth,
    db: DB,
    limit: int = Query(8, ge=1, le=20),
):
    """List pre-computed questions aggregated across the workspace's ready sources.

    Questions are deduplicated (case-insensitive, trimmed) and capped at `limit`.
    """
    # Defense in depth: verify the workspace belongs to the org before aggregating.
    require_one(
        db.table("workspaces")
        .select("id")
        .eq("id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Workspace",
    )

    return await get_workspace_suggested_questions(db, workspace_id, auth.organization_id, limit)
