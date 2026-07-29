"""
Webhook Dispatcher — HTTP delivery with HMAC-SHA256 signature and exponential retry.

Two modes:
  1. deliver_webhook() — direct send (called by job worker for a specific webhook_id)
  2. trigger_webhooks() — fan-out (called by agents after a business event)

Never raises from _emit_webhook() — best-effort, won't crash the pipeline.
"""

import json
import logging
from datetime import datetime, timedelta, timezone

import httpx

from packages.db.client import safe_get_one
from packages.db.job_queue import create_job

from .webhook_security import sign_payload, validate_webhook_url
from .webhook_trigger import _emit_webhook, trigger_webhooks  # noqa: F401

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT = 10
WEBHOOK_USER_AGENT = "XAIS-Vault-Webhook/1.0"
RETRY_DELAYS = [60, 300, 1800]  # 1min, 5min, 30min
MAX_RETRY_ATTEMPTS = 3


async def deliver_webhook(
    supabase,
    *,
    webhook_id: str,
    event_type: str,
    payload: dict,
    organization_id: str,
    attempt: int = 1,
    **_kwargs,
) -> dict:
    """Send a webhook and record the delivery.

    Returns a dict describing the delivery outcome.
    """
    webhook = safe_get_one(
        supabase.table("webhooks")
        .select("id, url, secret, is_active")
        .eq("id", webhook_id)
        .execute()
    )

    if not webhook or not webhook.get("is_active"):
        return {"status": "skipped", "reason": "webhook_inactive_or_not_found"}

    url = webhook["url"]
    secret = webhook["secret"]

    try:
        validate_webhook_url(url)
    except ValueError as e:
        logger.warning("Webhook %s blocked by SSRF filter: %s", webhook_id, e)
        return {"status": "blocked", "reason": str(e)}

    body_dict = {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }
    body_bytes = json.dumps(body_dict, default=str).encode()
    signature = sign_payload(secret, body_bytes)

    delivery_record: dict = {
        "webhook_id": webhook_id,
        "event_type": event_type,
        "payload": body_dict,
        "attempt": attempt,
    }

    try:
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.post(
                url,
                content=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                    "X-Webhook-Event": event_type,
                    "X-Webhook-Version": "2",
                    "User-Agent": WEBHOOK_USER_AGENT,
                },
                timeout=WEBHOOK_TIMEOUT,
            )

        if 200 <= response.status_code < 300:
            delivery_record.update(
                {
                    "status": "delivered",
                    "http_status": response.status_code,
                    "response_body": response.text[:1000],
                    "delivered_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        else:
            delivery_record.update(
                {
                    "status": "failed",
                    "http_status": response.status_code,
                    "response_body": response.text[:1000],
                }
            )

    except Exception as exc:
        delivery_record.update(
            {
                "status": "failed",
                "http_status": None,
                "response_body": str(exc)[:1000],
            }
        )

    supabase.table("webhook_deliveries").insert(delivery_record).execute()

    if delivery_record["status"] == "failed":
        await _schedule_retry(
            supabase,
            webhook_id=webhook_id,
            event_type=event_type,
            payload=payload,
            organization_id=organization_id,
            attempt=attempt,
        )

    return delivery_record


async def _schedule_retry(
    supabase,
    *,
    webhook_id: str,
    event_type: str,
    payload: dict,
    organization_id: str,
    attempt: int,
) -> None:
    """Schedule a retry job if under MAX_RETRY_ATTEMPTS."""
    if attempt >= MAX_RETRY_ATTEMPTS:
        logger.warning(
            "Webhook %s delivery failed after %d attempts, giving up for event %s",
            webhook_id,
            attempt,
            event_type,
        )
        return

    delay_seconds = RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)]
    locked_until = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)

    await create_job(
        supabase,
        type="dispatch_webhook",
        payload={
            "webhook_id": webhook_id,
            "event_type": event_type,
            "payload": payload,
            "organization_id": organization_id,
            "attempt": attempt + 1,
        },
        organization_id=organization_id,
        max_attempts=1,
    )

    logger.info(
        "Scheduled webhook retry #%d for webhook %s in %ds",
        attempt + 1,
        webhook_id,
        delay_seconds,
    )

    # Update the locked_until on the newly created job
    # (create_job doesn't support locked_until directly — update after insert)
    result = (
        supabase.table("jobs")
        .select("id")
        .eq("type", "dispatch_webhook")
        .eq("status", "pending")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        supabase.table("jobs").update(
            {
                "locked_until": locked_until.isoformat(),
            }
        ).eq("id", result.data[0]["id"]).execute()
