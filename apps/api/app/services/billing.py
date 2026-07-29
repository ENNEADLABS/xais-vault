"""
Stripe billing service — checkout, portal, subscription sync.

Toutes les interactions Stripe passent par ce service.
Jamais d'appel Stripe direct depuis un router.
"""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException

from .billing_stripe import (  # noqa: F401
    create_checkout_session,
    create_portal_session,
)
from .billing_webhooks import (  # noqa: F401
    handle_checkout_completed,
    handle_subscription_deleted,
    sync_subscription,
)

logger = logging.getLogger(__name__)


async def get_billing_status(db, organization_id: str) -> dict:
    """Retourne le statut billing d'une organisation."""
    from .plan_limits import ANALYSIS_JOB_TYPES, PLAN_LIMITS

    result = (
        db.table("organizations")
        .select("id, plan, stripe_customer_id, stripe_subscription_id, trial_ends_at")
        .eq("id", organization_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Organization not found")

    org = result.data[0]
    plan = org.get("plan", "starter")
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"])

    # Compter les workspaces actifs
    workspaces_result = (
        db.table("workspaces")
        .select("id", count="exact")
        .eq("organization_id", organization_id)
        .neq("status", "archived")
        .execute()
    )
    workspaces_count = workspaces_result.count or 0

    # Compter les analyses ce mois
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    analyses_result = (
        db.table("jobs")
        .select("id", count="exact")
        .eq("organization_id", organization_id)
        .in_("type", list(ANALYSIS_JOB_TYPES))
        .gte("created_at", month_start.isoformat())
        .execute()
    )
    analyses_count = analyses_result.count or 0

    return {
        "plan": plan,
        "stripe_customer_id": org.get("stripe_customer_id"),
        "stripe_subscription_id": org.get("stripe_subscription_id"),
        "trial_ends_at": org.get("trial_ends_at"),
        "limits": limits,
        "current_usage": {
            "workspaces_count": workspaces_count,
            "analyses_this_month": analyses_count,
        },
    }
