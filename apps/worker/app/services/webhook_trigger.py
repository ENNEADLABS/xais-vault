"""
Webhook trigger — fan-out dispatch jobs for business events.
Extracted from webhook_dispatcher.py.
"""

import logging

from packages.db.client import safe_get_list
from packages.db.job_queue import create_job

logger = logging.getLogger(__name__)


async def trigger_webhooks(
    supabase,
    *,
    organization_id: str,
    event_type: str,
    data: dict,
) -> int:
    """Find subscribed webhooks and create dispatch jobs.

    Called by agents/services after a business event.
    Returns the number of webhooks triggered.
    """
    webhooks = safe_get_list(
        supabase.table("webhooks")
        .select("id")
        .eq("organization_id", organization_id)
        .eq("is_active", True)
        .contains("events", [event_type])
        .execute()
    )

    if not webhooks:
        return 0

    for wh in webhooks:
        await create_job(
            supabase,
            type="dispatch_webhook",
            payload={
                "webhook_id": wh["id"],
                "event_type": event_type,
                "payload": data,
                "organization_id": organization_id,
                "attempt": 1,
            },
            organization_id=organization_id,
            max_attempts=1,
        )

    logger.info(
        "Triggered %d webhook(s) for event %s in org %s",
        len(webhooks),
        event_type,
        organization_id,
    )
    return len(webhooks)


async def _emit_webhook(
    supabase,
    *,
    organization_id: str,
    event_type: str,
    data: dict,
) -> None:
    """Emit a webhook event. Never raises — best-effort, won't crash the pipeline."""
    try:
        await trigger_webhooks(
            supabase,
            organization_id=organization_id,
            event_type=event_type,
            data=data,
        )
    except Exception as exc:
        logger.warning("Failed to trigger webhook %s: %s", event_type, exc)
