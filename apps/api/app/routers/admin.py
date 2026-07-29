"""
Admin router — stats d'usage, overview org, API keys, activité.

Tous les endpoints requièrent le rôle admin (AdminAuth).
Filtrés par organization_id du contexte auth (multi-tenant).
"""

import logging

from fastapi import APIRouter, Query

from ..dependencies import DB, AdminAuth
from ..models.admin import (
    ActivityLogResponse,
    ApiKeysUsageResponse,
    OrgOverviewResponse,
    UsageStatsResponse,
)
from ..models.common import ApiResponse
from ..services import admin_stats

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/usage")
async def get_usage_stats(
    auth: AdminAuth,
    db: DB,
    months: int = Query(default=6, ge=1, le=12),
):
    """Agrégation usage_logs par mois et type d'opération. Admin only."""
    data = await admin_stats.get_usage_stats(
        db=db,
        org_id=auth.organization_id,
        months=months,
    )
    return ApiResponse(data=UsageStatsResponse(**data.model_dump()))


@router.get("/overview")
async def get_org_overview(auth: AdminAuth, db: DB):
    """Stats globales de l'organisation (membres, workspaces, sources, insights). Admin only."""
    data = await admin_stats.get_org_overview(db=db, org_id=auth.organization_id)
    return ApiResponse(data=OrgOverviewResponse(**data.model_dump()))


@router.get("/api-keys/usage")
async def get_api_keys_usage(auth: AdminAuth, db: DB):
    """Métadonnées et statistiques des API keys. Admin only."""
    data = await admin_stats.get_api_keys_usage(db=db, org_id=auth.organization_id)
    return ApiResponse(data=ApiKeysUsageResponse(**data.model_dump()))


@router.get("/activity")
async def get_activity_log(
    auth: AdminAuth,
    db: DB,
    limit: int = Query(default=50, ge=1, le=200),
):
    """Log d'activité récent — derniers jobs terminés. Admin only."""
    data = await admin_stats.get_activity_log(
        db=db,
        org_id=auth.organization_id,
        limit=limit,
    )
    return ApiResponse(data=ActivityLogResponse(**data.model_dump()))
