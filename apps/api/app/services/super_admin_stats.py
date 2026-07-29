"""
Service super-admin — agrégation cross-org des stats plateforme.

Pas de filtre organization_id — vue globale réservée aux super-admins.
"""

import logging
from datetime import datetime, timedelta, timezone

from packages.db.client import safe_get_list
from supabase import Client

from ..models.super_admin import (
    ErrorItem,
    GraphStats,
    OrgMetrics,
    PlatformOverview,
    SummarizationStats,
    SuperAdminActivityItem,
    UserActivity,
)

logger = logging.getLogger(__name__)


def _resolve_names(
    db: Client,
    rows: list[dict],
) -> tuple[dict[str, str], dict[str, str]]:
    """Résout les noms d'orgs et de workspaces à partir d'une liste de rows jobs."""
    # Noms d'orgs
    org_ids = list({row["organization_id"] for row in rows})
    orgs_result = (
        db.table("organizations").select("id, name").in_("id", org_ids).execute()
    )
    org_names = {o["id"]: o["name"] for o in (orgs_result.data or [])}

    # Noms de workspaces
    workspace_ids = [
        row["payload"].get("workspace_id")
        for row in rows
        if row.get("payload") and row["payload"].get("workspace_id")
    ]
    workspace_names: dict[str, str] = {}
    if workspace_ids:
        workspaces_result = (
            db.table("workspaces").select("id, name").in_("id", workspace_ids).execute()
        )
        workspace_names = {d["id"]: d["name"] for d in (workspaces_result.data or [])}

    return org_names, workspace_names


async def get_summarization_stats(db: Client) -> SummarizationStats:
    """KPIs summarization — coûts et volumes."""
    result = db.rpc("super_admin_summarization_stats").execute()
    data = result.data
    return SummarizationStats(
        total_count=int(data["total_count"]),
        count_24h=int(data["count_24h"]),
        total_cost_usd=float(data["total_cost_usd"]),
        cost_24h_usd=float(data["cost_24h_usd"]),
        avg_cost_usd=float(data["avg_cost_usd"]),
        avg_input_tokens=int(data["avg_input_tokens"]),
        avg_output_tokens=int(data["avg_output_tokens"]),
    )


async def get_platform_overview(db: Client) -> PlatformOverview:
    """KPIs globaux de la plateforme via RPC SQL (1 seule query)."""
    result = db.rpc("super_admin_platform_overview").execute()
    data = result.data
    return PlatformOverview(
        total_organizations=int(data["total_organizations"]),
        total_workspaces=int(data["total_workspaces"]),
        total_sources=int(data["total_sources"]),
        total_insights=int(data["total_insights"]),
        total_deliverables=int(data["total_deliverables"]),
        total_chat_messages=int(data["total_chat_messages"]),
        active_orgs_7d=int(data["active_orgs_7d"]),
        failed_jobs_24h=int(data["failed_jobs_24h"]),
        job_success_rate_7d=float(data["job_success_rate_7d"]),
    )


async def get_org_metrics(db: Client) -> list[OrgMetrics]:
    """Métriques par organisation via RPC SQL."""
    result = db.rpc("super_admin_org_metrics").execute()
    rows = result.data or []

    return [
        OrgMetrics(
            org_id=row["org_id"],
            org_name=row["org_name"],
            plan=row["plan"],
            member_count=int(row["member_count"]),
            workspace_count=int(row["workspace_count"]),
            source_count=int(row["source_count"]),
            insight_count=int(row["insight_count"]),
            deliverable_count=int(row["deliverable_count"]),
            chat_message_count=int(row["chat_message_count"]),
            last_activity_at=row.get("last_activity_at"),
            created_at=row["created_at"],
        )
        for row in rows
    ]


async def get_user_activity(
    db: Client,
    org_id: str | None = None,
    limit: int = 100,
) -> list[UserActivity]:
    """Activité par user via RPC SQL."""
    params: dict = {"row_limit": limit}
    if org_id:
        params["target_org_id"] = org_id

    result = db.rpc("super_admin_user_activity", params).execute()
    rows = result.data or []

    return [
        UserActivity(
            user_id=row["user_id"],
            email=row.get("email"),
            display_name=row.get("display_name"),
            org_name=row["org_name"],
            workspaces_created=int(row["workspaces_created"]),
            sources_uploaded=int(row["sources_uploaded"]),
            chat_messages_sent=int(row["chat_messages_sent"]),
            deliverables_generated=int(row["deliverables_generated"]),
            last_active_at=row.get("last_active_at"),
        )
        for row in rows
    ]


async def get_global_activity(
    db: Client,
    limit: int = 100,
) -> list[SuperAdminActivityItem]:
    """Feed d'activité global — derniers jobs toutes orgs confondues."""
    result = (
        db.table("jobs")
        .select(
            "id, type, status, organization_id, payload, created_at, completed_at, error_message"
        )
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = safe_get_list(result)
    if not rows:
        return []

    org_names, workspace_names = _resolve_names(db, rows)

    return [
        SuperAdminActivityItem(
            id=row["id"],
            type=row["type"],
            status=row["status"],
            org_name=org_names.get(row["organization_id"], "?"),
            workspace_name=workspace_names.get((row.get("payload") or {}).get("workspace_id", "")),
            created_at=row["created_at"],
            completed_at=row.get("completed_at"),
            error_message=row.get("error_message"),
        )
        for row in rows
    ]


async def get_graph_stats(db: Client) -> GraphStats:
    """Stats du knowledge graph — entités, relations, coûts extraction."""
    entities_result = db.table("entities").select("id, workspace_id, entity_type", count="exact").execute()
    total_entities = entities_result.count or 0
    entity_rows = safe_get_list(entities_result)

    relations_result = db.table("entity_relations").select("id", count="exact").execute()
    total_relations = relations_result.count or 0

    links_result = db.table("chunk_entities").select("chunk_id", count="exact").execute()
    total_chunk_links = links_result.count or 0

    # Entités par type
    entities_by_type: dict[str, int] = {}
    for e in entity_rows:
        t = e["entity_type"]
        entities_by_type[t] = entities_by_type.get(t, 0) + 1

    # Workspaces uniques avec des entités
    workspace_ids = {e["workspace_id"] for e in entity_rows}
    workspaces_with_graph = len(workspace_ids)
    avg_per_workspace = total_entities / workspaces_with_graph if workspaces_with_graph else 0

    # Coûts extraction depuis usage_logs
    cost_result = safe_get_list(
        db.table("usage_logs")
        .select("cost_usd, created_at")
        .eq("operation", "entity_extraction")
        .execute()
    )
    total_cost = sum(float(r.get("cost_usd") or 0) for r in cost_result)
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    cost_24h = sum(float(r.get("cost_usd") or 0) for r in cost_result if r.get("created_at", "") >= cutoff)

    return GraphStats(
        total_entities=total_entities,
        total_relations=total_relations,
        total_chunk_links=total_chunk_links,
        entities_by_type=entities_by_type,
        workspaces_with_graph=workspaces_with_graph,
        extraction_cost_total_usd=round(total_cost, 4),
        extraction_cost_24h_usd=round(cost_24h, 4),
        avg_entities_per_workspace=round(avg_per_workspace, 1),
    )


async def get_error_log(
    db: Client,
    limit: int = 50,
) -> list[ErrorItem]:
    """Jobs en erreur — derniers failed toutes orgs confondues."""
    result = (
        db.table("jobs")
        .select(
            "id, type, organization_id, payload, error_message, attempts, created_at, completed_at"
        )
        .eq("status", "failed")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = safe_get_list(result)
    if not rows:
        return []

    org_names, workspace_names = _resolve_names(db, rows)

    return [
        ErrorItem(
            id=row["id"],
            type=row["type"],
            org_name=org_names.get(row["organization_id"], "?"),
            workspace_name=workspace_names.get((row.get("payload") or {}).get("workspace_id", "")),
            error_message=row.get("error_message"),
            attempts=row.get("attempts", 0),
            created_at=row["created_at"],
            failed_at=row.get("completed_at"),
        )
        for row in rows
    ]
