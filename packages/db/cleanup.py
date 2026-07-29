"""
Garbage collection — suppression périodique des données expirées.

Fonctions appelées par le worker toutes les heures pour éviter
que les tables jobs, agent_traces et webhook_deliveries ne grossissent indéfiniment.
"""

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


async def cleanup_old_jobs(
    supabase,
    *,
    completed_retention_days: int = 7,
    failed_retention_days: int = 30,
) -> dict[str, int]:
    """Supprime les jobs terminés au-delà de la période de rétention.

    Returns:
        {"completed_deleted": N, "failed_deleted": N}
    """
    now = datetime.now(timezone.utc)

    completed_cutoff = (now - timedelta(days=completed_retention_days)).isoformat()
    failed_cutoff = (now - timedelta(days=failed_retention_days)).isoformat()

    completed_result = (
        supabase.table("jobs")
        .delete()
        .eq("status", "completed")
        .lt("completed_at", completed_cutoff)
        .execute()
    )
    completed_deleted = len(completed_result.data) if completed_result.data else 0

    failed_result = (
        supabase.table("jobs")
        .delete()
        .eq("status", "failed")
        .lt("completed_at", failed_cutoff)
        .execute()
    )
    failed_deleted = len(failed_result.data) if failed_result.data else 0

    if completed_deleted or failed_deleted:
        logger.info(
            "GC jobs: %d completed supprimés (>%dd), %d failed supprimés (>%dd)",
            completed_deleted,
            completed_retention_days,
            failed_deleted,
            failed_retention_days,
        )

    return {"completed_deleted": completed_deleted, "failed_deleted": failed_deleted}


async def cleanup_old_traces(
    supabase,
    *,
    retention_days: int = 90,
) -> int:
    """Supprime les agent_traces de plus de N jours.

    Returns:
        Nombre de lignes supprimées.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()

    result = supabase.table("agent_traces").delete().lt("created_at", cutoff).execute()
    deleted = len(result.data) if result.data else 0

    if deleted:
        logger.info(
            "GC traces: %d agent_traces supprimées (>%dd)", deleted, retention_days
        )

    return deleted


async def cleanup_old_webhook_deliveries(
    supabase,
    *,
    retention_days: int = 30,
) -> int:
    """Supprime les webhook_deliveries delivered/failed de plus de N jours.

    Returns:
        Nombre de lignes supprimées.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()

    result = (
        supabase.table("webhook_deliveries")
        .delete()
        .in_("status", ["delivered", "failed"])
        .lt("created_at", cutoff)
        .execute()
    )
    deleted = len(result.data) if result.data else 0

    if deleted:
        logger.info(
            "GC webhooks: %d webhook_deliveries supprimées (>%dd)",
            deleted,
            retention_days,
        )

    return deleted
