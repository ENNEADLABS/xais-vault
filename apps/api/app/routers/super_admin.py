"""Router super-admin — dashboard opérationnel cross-org."""

from fastapi import APIRouter, Query

from packages.core.config import load_config

from ..dependencies import DB, AuthOnly, SuperAdmin
from ..models.super_admin import (
    ErrorItem,
    GraphStats,
    OrgMetrics,
    PlatformOverview,
    SummarizationStats,
    SuperAdminActivityItem,
    UserActivity,
)
from ..services import super_admin_stats

router = APIRouter()


@router.get("/check")
async def check_super_admin(auth: AuthOnly, db: DB):
    """Vérifie si l'utilisateur est super-admin (pas de 403)."""
    config = load_config()
    return {"is_super_admin": auth.user_id in config.admin_user_ids}


@router.get("/summarization", response_model=SummarizationStats)
async def get_summarization(auth: SuperAdmin, db: DB):
    """KPIs de summarization — coûts et volumes."""
    return await super_admin_stats.get_summarization_stats(db)


@router.get("/overview", response_model=PlatformOverview)
async def get_overview(auth: SuperAdmin, db: DB):
    """KPIs globaux de la plateforme."""
    return await super_admin_stats.get_platform_overview(db)


@router.get("/organizations", response_model=list[OrgMetrics])
async def get_organizations(auth: SuperAdmin, db: DB):
    """Tableau des organisations avec métriques."""
    return await super_admin_stats.get_org_metrics(db)


@router.get("/users", response_model=list[UserActivity])
async def get_users(
    auth: SuperAdmin,
    db: DB,
    org_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """Activité par utilisateur, filtre org optionnel."""
    return await super_admin_stats.get_user_activity(db, org_id=org_id, limit=limit)


@router.get("/activity", response_model=list[SuperAdminActivityItem])
async def get_activity(
    auth: SuperAdmin,
    db: DB,
    limit: int = Query(100, ge=1, le=500),
):
    """Feed d'activité global — derniers jobs."""
    return await super_admin_stats.get_global_activity(db, limit=limit)


@router.get("/errors", response_model=list[ErrorItem])
async def get_errors(
    auth: SuperAdmin,
    db: DB,
    limit: int = Query(50, ge=1, le=200),
):
    """Jobs en erreur récents."""
    return await super_admin_stats.get_error_log(db, limit=limit)


@router.get("/graph", response_model=GraphStats)
async def get_graph_stats(auth: SuperAdmin, db: DB):
    """Stats du knowledge graph — entités, relations, coûts extraction."""
    return await super_admin_stats.get_graph_stats(db)
