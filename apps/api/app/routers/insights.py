"""
Insights router — list, get, update status, trigger verification.

Insights are created by the Scanner agent. Analysts review them
via confirm/reject/investigate actions (human-in-the-loop).
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from packages.db.client import require_one, safe_get_list
from packages.db.job_queue import create_job

from ..dependencies import DB, AnalystAuth, ViewerAuth, require_scope_dep
from ..models.common import ApiResponse
from ..models.insight import (
    InsightAction,
    InsightActionRequest,
    InsightResponse,
    InsightSeverity,
    InsightStatus,
    InsightType,
)
from ..services.plan_limits import check_analysis_limit

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", dependencies=[Depends(require_scope_dep("insights:read"))])
async def list_insights(
    workspace_id: str,
    auth: ViewerAuth,
    db: DB,
    type: InsightType | None = Query(None, description="Filter by type"),
    severity: InsightSeverity | None = Query(None, description="Filter by severity"),
    status: InsightStatus | None = Query(None, description="Filter by status"),
):
    """List all insights for a workspace, with optional filters."""
    # Validate workspace belongs to org
    require_one(
        db.table("workspaces")
        .select("id")
        .eq("id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Workspace",
    )

    query = (
        db.table("insights")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
    )

    if type:
        query = query.eq("type", type.value)
    if severity:
        query = query.eq("severity", severity.value)
    if status:
        query = query.eq("status", status.value)

    insights = safe_get_list(query.order("created_at", desc=True).execute())

    return ApiResponse(data=[InsightResponse(**f) for f in insights])


@router.get(
    "/{insight_id}",
    dependencies=[Depends(require_scope_dep("insights:read"))],
)
async def get_insight(workspace_id: str, insight_id: str, auth: ViewerAuth, db: DB):
    """Get a single insight with full details."""
    insight = require_one(
        db.table("insights")
        .select("*")
        .eq("id", insight_id)
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Insight",
    )

    return ApiResponse(data=InsightResponse(**insight))


@router.patch(
    "/{insight_id}",
    dependencies=[Depends(require_scope_dep("insights:write"))],
)
async def update_insight_status(
    workspace_id: str,
    insight_id: str,
    body: InsightActionRequest,
    auth: AnalystAuth,
    db: DB,
):
    """Update a insight status: confirm, reject, or trigger investigation.

    - confirm → status = 'confirmed'
    - reject → status = 'rejected'
    - investigate → status = 'investigating', creates a verify_insight job
    """
    require_one(
        db.table("insights")
        .select("*")
        .eq("id", insight_id)
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Insight",
    )

    now = datetime.now(timezone.utc).isoformat()

    match body.action:
        case InsightAction.confirm:
            result = (
                db.table("insights")
                .update(
                    {
                        "status": "confirmed",
                        "reviewed_by": auth.user_id,
                        "reviewed_at": now,
                        "updated_at": now,
                    }
                )
                .eq("id", insight_id)
                .execute()
            )
            updated = require_one(result, "Insight")
            return ApiResponse(data=InsightResponse(**updated))

        case InsightAction.reject:
            result = (
                db.table("insights")
                .update(
                    {
                        "status": "rejected",
                        "reviewed_by": auth.user_id,
                        "reviewed_at": now,
                        "updated_at": now,
                    }
                )
                .eq("id", insight_id)
                .execute()
            )
            updated = require_one(result, "Insight")
            return ApiResponse(data=InsightResponse(**updated))

        case InsightAction.investigate:
            await check_analysis_limit(db, auth.organization_id)

            # Mark as investigating
            db.table("insights").update(
                {
                    "status": "investigating",
                    "reviewed_by": auth.user_id,
                    "reviewed_at": now,
                    "updated_at": now,
                }
            ).eq("id", insight_id).execute()

            # Create verification job
            job = await create_job(
                db,
                type="verify_insight",
                payload={
                    "insight_id": insight_id,
                    "workspace_id": workspace_id,
                    "organization_id": auth.organization_id,
                },
                organization_id=auth.organization_id,
            )

            # Refetch the updated insight
            updated_result = (
                db.table("insights").select("*").eq("id", insight_id).execute()
            )
            updated = require_one(updated_result, "Insight")

            return ApiResponse(
                data=InsightResponse(**updated),
                meta={"job_id": job["id"]},
            )
