"""
Investigations router — CRUD pour les investigations.

Les investigations peuvent être créées manuellement depuis le Studio
ou automatiquement via l'action 'investigate' sur un insight.
Exécutées par le Researcher agent (worker).
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from packages.db.client import require_one, safe_get_list
from packages.db.job_queue import create_job

from ..dependencies import DB, AnalystAuth, ViewerAuth, require_scope_dep
from ..models.common import ApiResponse
from ..models.investigation import (
    InvestigationCreate,
    InvestigationResponse,
    InvestigationStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", dependencies=[Depends(require_scope_dep("investigations:read"))])
async def list_investigations(
    workspace_id: str,
    auth: ViewerAuth,
    db: DB,
    status: InvestigationStatus | None = Query(None, description="Filter by status"),
    insight_id: str | None = Query(None, description="Filter by linked insight"),
):
    """List investigations for a workspace, with optional filters."""
    require_one(
        db.table("workspaces")
        .select("id")
        .eq("id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Workspace",
    )

    query = (
        db.table("investigations")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
    )

    if status:
        query = query.eq("status", status.value)
    if insight_id:
        query = query.eq("insight_id", insight_id)

    investigations = safe_get_list(query.order("created_at", desc=True).execute())

    return ApiResponse(data=[InvestigationResponse(**inv) for inv in investigations])


@router.post(
    "/",
    status_code=202,
    dependencies=[Depends(require_scope_dep("investigations:write"))],
)
async def create_investigation(
    workspace_id: str,
    body: InvestigationCreate,
    auth: AnalystAuth,
    db: DB,
):
    """Lancer une investigation depuis le Studio."""
    require_one(
        db.table("workspaces")
        .select("id")
        .eq("id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Workspace",
    )

    # Vérifier que le insight existe si fourni
    if body.insight_id:
        require_one(
            db.table("insights")
            .select("id")
            .eq("id", body.insight_id)
            .eq("workspace_id", workspace_id)
            .execute(),
            "Insight",
        )

    now = datetime.now(timezone.utc).isoformat()
    inv_row = {
        "workspace_id": workspace_id,
        "organization_id": auth.organization_id,
        "requested_by": auth.user_id,
        "question": body.question,
        "scope": body.scope.value,
        "insight_id": body.insight_id,
        "status": "pending",
        "created_at": now,
    }
    result = db.table("investigations").insert(inv_row).execute()
    investigation = require_one(result, "Investigation")

    job = await create_job(
        db,
        type="investigate",
        payload={
            "investigation_id": investigation["id"],
            "workspace_id": workspace_id,
            "organization_id": auth.organization_id,
        },
        organization_id=auth.organization_id,
    )

    return ApiResponse(
        data=InvestigationResponse(**investigation),
        meta={"job_id": job["id"]},
    )


@router.get(
    "/{investigation_id}",
    dependencies=[Depends(require_scope_dep("investigations:read"))],
)
async def get_investigation(
    workspace_id: str,
    investigation_id: str,
    auth: ViewerAuth,
    db: DB,
):
    """Get a single investigation with full report."""
    investigation = require_one(
        db.table("investigations")
        .select("*")
        .eq("id", investigation_id)
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Investigation",
    )

    return ApiResponse(data=InvestigationResponse(**investigation))
