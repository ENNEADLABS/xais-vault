"""
Plan limits enforcement — workspaces and analyses quotas per organization plan.
"""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Limites par plan
PLAN_LIMITS: dict[str, dict] = {
    "starter": {"max_workspaces": 5, "max_analyses_per_month": 50},
    "premium": {"max_workspaces": 10, "max_analyses_per_month": 100},
    "team": {"max_workspaces": 20, "max_analyses_per_month": 200},
    "enterprise": {"max_workspaces": None, "max_analyses_per_month": None},  # illimité
    "trial": {"max_workspaces": 20, "max_analyses_per_month": 200},  # identique Team
}

# Types de jobs qui comptent comme "analyse" (hors index_source)
ANALYSIS_JOB_TYPES = {
    "scan_workspace",
    "verify_insight",
    "investigate",
    "generate_deliverable",
}


async def check_workspace_limit(db, organization_id: str) -> None:
    """Lever 403 si l'organisation a atteint sa limite de workspaces."""
    org = _get_org(db, organization_id)
    plan = org.get("plan", "starter")
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"])
    max_workspaces = limits["max_workspaces"]

    if max_workspaces is None:
        return  # Illimité

    result = (
        db.table("workspaces")
        .select("id", count="exact")
        .eq("organization_id", organization_id)
        .neq("status", "archived")
        .execute()
    )

    current = result.count or 0
    if current >= max_workspaces:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Workspace limit reached for plan '{plan}' "
                f"({current}/{max_workspaces}). Upgrade to create more workspaces."
            ),
        )


async def check_analysis_limit(db, organization_id: str) -> None:
    """Lever 403 si l'organisation a dépassé son quota d'analyses ce mois."""
    org = _get_org(db, organization_id)
    plan = org.get("plan", "starter")
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"])
    max_analyses = limits["max_analyses_per_month"]

    if max_analyses is None:
        return  # Illimité

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = (
        db.table("jobs")
        .select("id", count="exact")
        .eq("organization_id", organization_id)
        .in_("type", list(ANALYSIS_JOB_TYPES))
        .gte("created_at", month_start.isoformat())
        .execute()
    )

    current = result.count or 0
    if current >= max_analyses:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Monthly analysis limit reached for plan '{plan}' "
                f"({current}/{max_analyses}). Upgrade for more analyses."
            ),
        )


async def is_analysis_limit_reached(db, organization_id: str) -> bool:
    """Version sans HTTPException — pour le Worker (non-bloquant)."""
    try:
        await check_analysis_limit(db, organization_id)
        return False
    except HTTPException:
        return True


def _get_org(db, organization_id: str) -> dict:
    """Fetch organization plan. Auto-expire le trial si dépassé (lazy check)."""
    result = (
        db.table("organizations")
        .select("id, plan, trial_ends_at")
        .eq("id", organization_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Organization not found")

    org = result.data[0]

    # Auto-expiration du trial
    if org.get("plan") == "trial" and org.get("trial_ends_at"):
        trial_end = datetime.fromisoformat(org["trial_ends_at"].replace("Z", "+00:00"))
        if trial_end < datetime.now(timezone.utc):
            db.table("organizations").update({"plan": "starter"}).eq(
                "id", organization_id
            ).execute()
            org["plan"] = "starter"

    return org
