"""
Service admin — agrégation des stats d'usage, overview org, API keys, activité.

Toutes les fonctions filtrent par organization_id (multi-tenant).
"""

import logging

from supabase import Client

from ..models.admin import (
    ActivityItem,
    ActivityLogResponse,
    ApiKeysUsageResponse,
    ApiKeyUsageItem,
    OrgOverviewResponse,
    UsageByMonth,
    UsageStatsResponse,
    UsageTotals,
)

logger = logging.getLogger(__name__)


async def get_usage_stats(
    db: Client,
    org_id: str,
    months: int = 6,
) -> UsageStatsResponse:
    """Agrégation usage_logs par mois et opération via RPC Supabase."""
    result = db.rpc(
        "admin_usage_by_month",
        {"target_org_id": org_id, "month_count": months},
    ).execute()

    rows = result.data or []
    usage_months = [
        UsageByMonth(
            month=row["month"],
            operation=row["operation"],
            count=int(row["count"]),
            input_tokens=int(row["input_tokens"]),
            output_tokens=int(row["output_tokens"]),
            cost_usd=float(row["cost_usd"]),
        )
        for row in rows
    ]

    totals = UsageTotals(
        total_cost_usd=sum(m.cost_usd for m in usage_months),
        total_input_tokens=sum(m.input_tokens for m in usage_months),
        total_output_tokens=sum(m.output_tokens for m in usage_months),
        total_operations=sum(m.count for m in usage_months),
    )

    return UsageStatsResponse(months=usage_months, totals=totals)


async def get_org_overview(
    db: Client,
    org_id: str,
) -> OrgOverviewResponse:
    """Stats globales de l'organisation : membres, workspaces, sources, insights."""
    # Organisation info
    org_result = (
        db.table("organizations")
        .select("name, plan, trial_ends_at")
        .eq("id", org_id)
        .execute()
    )
    org_data = org_result.data[0] if org_result.data else {}

    # Comptages — séquentiels (Supabase Python client est synchrone)
    members_result = (
        db.table("organization_members")
        .select("id", count="exact")
        .eq("organization_id", org_id)
        .execute()
    )
    workspaces_result = (
        db.table("workspaces")
        .select("id", count="exact")
        .eq("organization_id", org_id)
        .execute()
    )
    sources_result = (
        db.table("sources")
        .select("id", count="exact")
        .eq("organization_id", org_id)
        .execute()
    )
    insights_result = (
        db.table("insights")
        .select("id", count="exact")
        .eq("organization_id", org_id)
        .execute()
    )

    return OrgOverviewResponse(
        name=org_data.get("name", ""),
        plan=org_data.get("plan", "starter"),
        member_count=members_result.count or 0,
        workspace_count=workspaces_result.count or 0,
        source_count=sources_result.count or 0,
        insight_count=insights_result.count or 0,
        trial_ends_at=org_data.get("trial_ends_at"),
    )


async def get_api_keys_usage(
    db: Client,
    org_id: str,
) -> ApiKeysUsageResponse:
    """Liste les API keys de l'org avec leurs métadonnées."""
    result = (
        db.table("api_keys")
        .select(
            "id, name, key_prefix, is_active, rpm_limit, rpd_limit, last_used_at, created_at"
        )
        .eq("organization_id", org_id)
        .order("created_at", desc=True)
        .execute()
    )

    keys = [
        ApiKeyUsageItem(
            id=row["id"],
            name=row["name"],
            key_prefix=row["key_prefix"],
            is_active=row["is_active"],
            rpm_limit=row.get("rpm_limit") or 60,
            rpd_limit=row.get("rpd_limit") or 1000,
            last_used_at=row.get("last_used_at"),
            created_at=row["created_at"],
        )
        for row in (result.data or [])
    ]

    return ApiKeysUsageResponse(keys=keys)


async def get_activity_log(
    db: Client,
    org_id: str,
    limit: int = 50,
) -> ActivityLogResponse:
    """Derniers jobs de l'org avec enrichissement workspace/source depuis le payload."""
    result = (
        db.table("jobs")
        .select("id, type, status, payload, created_at, completed_at")
        .eq("organization_id", org_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    rows = result.data or []
    if not rows:
        return ActivityLogResponse(items=[])

    # Collecter les workspace_ids uniques pour fetch les noms en un seul batch
    workspace_ids = {
        row["payload"].get("workspace_id")
        for row in rows
        if row.get("payload") and row["payload"].get("workspace_id")
    }

    workspace_names: dict[str, str] = {}
    if workspace_ids:
        workspaces_result = (
            db.table("workspaces").select("id, name").in_("id", list(workspace_ids)).execute()
        )
        workspace_names = {d["id"]: d["name"] for d in (workspaces_result.data or [])}

    items = [
        ActivityItem(
            id=row["id"],
            type=row["type"],
            status=row["status"],
            created_at=row["created_at"],
            completed_at=row.get("completed_at"),
            workspace_name=workspace_names.get(
                (row.get("payload") or {}).get("workspace_id", ""), None
            ),
            source_name=(row.get("payload") or {}).get("filename"),
        )
        for row in rows
    ]

    return ActivityLogResponse(items=items)
