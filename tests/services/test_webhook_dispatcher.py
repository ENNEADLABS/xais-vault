"""
Tests for apps/worker/app/services/webhook_dispatcher.py

Uses respx to mock HTTP calls and unittest.mock for Supabase.
"""

import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import respx
from httpx import Response

from apps.worker.app.services.webhook_dispatcher import (
    MAX_RETRY_ATTEMPTS,
    RETRY_DELAYS,
    _emit_webhook,
    _schedule_retry,
    deliver_webhook,
    sign_payload,
    trigger_webhooks,
)

# ─── Constants ─────────────────────────────────────────────────

ORG_ID = str(uuid.uuid4())
WEBHOOK_ID = str(uuid.uuid4())
SECRET = "whsec_" + "a" * 32
URL = "https://example.com/hook"
EVENT_TYPE = "source.ready"
PAYLOAD = {"source_id": str(uuid.uuid4()), "workspace_id": str(uuid.uuid4())}
NOW = datetime.now(timezone.utc).isoformat()


# ─── Helpers ───────────────────────────────────────────────────


def _make_webhook_row(**overrides) -> dict:
    base = {
        "id": WEBHOOK_ID,
        "url": URL,
        "secret": SECRET,
        "is_active": True,
    }
    return {**base, **overrides}


def _make_supabase(webhook_row=None, insert_ok=True) -> MagicMock:
    """Build a mock Supabase client."""
    db = MagicMock()
    chain = MagicMock()
    for m in ("select", "eq", "insert", "update", "order", "limit", "contains"):
        getattr(chain, m).return_value = chain

    rows = [webhook_row] if webhook_row is not None else []
    result = MagicMock(data=rows)
    result.count = len(rows)
    chain.execute.return_value = result

    db.table.return_value = chain
    return db


# ─── sign_payload ───────────────────────────────────────────────


class TestSignPayload:
    def test_hmac_sha256_is_correct(self):
        """sign_payload produces a valid HMAC-SHA256 hex digest."""
        body = b'{"event": "test"}'
        expected = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
        assert sign_payload(SECRET, body) == expected

    def test_different_secrets_produce_different_signatures(self):
        body = b"payload"
        sig1 = sign_payload("whsec_" + "a" * 32, body)
        sig2 = sign_payload("whsec_" + "b" * 32, body)
        assert sig1 != sig2


# ─── deliver_webhook — success ──────────────────────────────────


@pytest.mark.asyncio
class TestDeliverWebhookSuccess:
    @respx.mock
    async def test_success_records_delivered(self):
        """HTTP 200 → delivery status is 'delivered'."""
        respx.post(URL).mock(return_value=Response(200, text="OK"))
        db = _make_supabase(_make_webhook_row())

        result = await deliver_webhook(
            db,
            webhook_id=WEBHOOK_ID,
            event_type=EVENT_TYPE,
            payload=PAYLOAD,
            organization_id=ORG_ID,
        )

        assert result["status"] == "delivered"
        assert result["http_status"] == 200
        # Verify delivery was inserted
        db.table.assert_any_call("webhook_deliveries")

    @respx.mock
    async def test_correct_headers_sent(self):
        """Request includes signature, event, and user-agent headers."""
        request_obj = None

        def capture(request):
            nonlocal request_obj
            request_obj = request
            return Response(200, text="OK")

        respx.post(URL).mock(side_effect=capture)
        db = _make_supabase(_make_webhook_row())

        await deliver_webhook(
            db,
            webhook_id=WEBHOOK_ID,
            event_type=EVENT_TYPE,
            payload=PAYLOAD,
            organization_id=ORG_ID,
        )

        assert request_obj is not None
        headers = dict(request_obj.headers)
        assert headers["content-type"] == "application/json"
        assert headers["x-webhook-event"] == EVENT_TYPE
        assert headers["x-webhook-version"] == "2"
        assert headers["user-agent"] == "XAIS-Vault-Webhook/1.0"
        # Signature must be a valid hex string
        sig = headers["x-webhook-signature"]
        assert len(sig) == 64  # SHA256 hex = 64 chars
        int(sig, 16)  # raises if not hex


# ─── deliver_webhook — failure ──────────────────────────────────


@pytest.mark.asyncio
class TestDeliverWebhookFailure:
    @respx.mock
    async def test_http_500_marks_failed(self):
        """HTTP 500 → status 'failed', retry scheduled."""
        respx.post(URL).mock(return_value=Response(500, text="Server Error"))
        db = _make_supabase(_make_webhook_row())

        with patch(
            "apps.worker.app.services.webhook_dispatcher._schedule_retry",
            new=AsyncMock(),
        ) as mock_retry:
            result = await deliver_webhook(
                db,
                webhook_id=WEBHOOK_ID,
                event_type=EVENT_TYPE,
                payload=PAYLOAD,
                organization_id=ORG_ID,
            )

        assert result["status"] == "failed"
        assert result["http_status"] == 500
        mock_retry.assert_called_once()

    @respx.mock
    async def test_timeout_marks_failed(self):
        """Network timeout → status 'failed'."""
        import httpx

        respx.post(URL).mock(side_effect=httpx.TimeoutException("timeout"))
        db = _make_supabase(_make_webhook_row())

        with patch(
            "apps.worker.app.services.webhook_dispatcher._schedule_retry",
            new=AsyncMock(),
        ):
            result = await deliver_webhook(
                db,
                webhook_id=WEBHOOK_ID,
                event_type=EVENT_TYPE,
                payload=PAYLOAD,
                organization_id=ORG_ID,
            )

        assert result["status"] == "failed"
        assert result["http_status"] is None

    async def test_inactive_webhook_skipped(self):
        """Inactive webhook → skipped, no HTTP call."""
        db = _make_supabase(_make_webhook_row(is_active=False))

        result = await deliver_webhook(
            db,
            webhook_id=WEBHOOK_ID,
            event_type=EVENT_TYPE,
            payload=PAYLOAD,
            organization_id=ORG_ID,
        )

        assert result["status"] == "skipped"

    async def test_missing_webhook_skipped(self):
        """Unknown webhook_id → skipped."""
        db = _make_supabase(webhook_row=None)

        result = await deliver_webhook(
            db,
            webhook_id=str(uuid.uuid4()),
            event_type=EVENT_TYPE,
            payload=PAYLOAD,
            organization_id=ORG_ID,
        )

        assert result["status"] == "skipped"


# ─── _schedule_retry ────────────────────────────────────────────


@pytest.mark.asyncio
class TestRetryScheduling:
    async def test_retry_under_max_creates_job(self):
        """Attempt < MAX_RETRY_ATTEMPTS → new job created."""
        db = _make_supabase()

        with patch(
            "apps.worker.app.services.webhook_dispatcher.create_job",
            new=AsyncMock(return_value={"id": str(uuid.uuid4())}),
        ) as mock_create:
            await _schedule_retry(
                db,
                webhook_id=WEBHOOK_ID,
                event_type=EVENT_TYPE,
                payload=PAYLOAD,
                organization_id=ORG_ID,
                attempt=1,
            )

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["payload"]["attempt"] == 2

    async def test_retry_at_max_does_not_create_job(self):
        """Attempt >= MAX_RETRY_ATTEMPTS → no new job."""
        db = _make_supabase()

        with patch(
            "apps.worker.app.services.webhook_dispatcher.create_job",
            new=AsyncMock(),
        ) as mock_create:
            await _schedule_retry(
                db,
                webhook_id=WEBHOOK_ID,
                event_type=EVENT_TYPE,
                payload=PAYLOAD,
                organization_id=ORG_ID,
                attempt=MAX_RETRY_ATTEMPTS,
            )

        mock_create.assert_not_called()

    def test_retry_delays_are_exponential(self):
        """RETRY_DELAYS follows 1min → 5min → 30min pattern."""
        assert RETRY_DELAYS[0] == 60
        assert RETRY_DELAYS[1] == 300
        assert RETRY_DELAYS[2] == 1800


# ─── trigger_webhooks ───────────────────────────────────────────


@pytest.mark.asyncio
class TestTriggerWebhooks:
    async def test_triggers_subscribed_webhooks(self):
        """2 subscribed webhooks → 2 jobs created."""
        wh1 = {"id": str(uuid.uuid4())}
        wh2 = {"id": str(uuid.uuid4())}

        db = MagicMock()
        chain = MagicMock()
        for m in ("select", "eq", "contains"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[wh1, wh2])
        db.table.return_value = chain

        with patch(
            "apps.worker.app.services.webhook_trigger.create_job",
            new=AsyncMock(return_value={"id": str(uuid.uuid4())}),
        ) as mock_create:
            count = await trigger_webhooks(
                db,
                organization_id=ORG_ID,
                event_type=EVENT_TYPE,
                data=PAYLOAD,
            )

        assert count == 2
        assert mock_create.call_count == 2

    async def test_no_subscribed_webhooks_returns_zero(self):
        """No webhooks → 0 jobs created, returns 0."""
        db = MagicMock()
        chain = MagicMock()
        for m in ("select", "eq", "contains"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        db.table.return_value = chain

        with patch(
            "apps.worker.app.services.webhook_trigger.create_job",
            new=AsyncMock(),
        ) as mock_create:
            count = await trigger_webhooks(
                db,
                organization_id=ORG_ID,
                event_type=EVENT_TYPE,
                data=PAYLOAD,
            )

        assert count == 0
        mock_create.assert_not_called()


# ─── _emit_webhook ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestEmitWebhook:
    async def test_does_not_raise_on_exception(self):
        """_emit_webhook swallows exceptions — pipeline must not crash."""
        db = MagicMock()

        with patch(
            "apps.worker.app.services.webhook_trigger.trigger_webhooks",
            new=AsyncMock(side_effect=RuntimeError("network down")),
        ):
            # Must not raise
            await _emit_webhook(
                db,
                organization_id=ORG_ID,
                event_type=EVENT_TYPE,
                data=PAYLOAD,
            )

    async def test_calls_trigger_webhooks_with_correct_args(self):
        """_emit_webhook delegates to trigger_webhooks with all kwargs."""
        db = MagicMock()

        with patch(
            "apps.worker.app.services.webhook_trigger.trigger_webhooks",
            new=AsyncMock(return_value=1),
        ) as mock_trigger:
            await _emit_webhook(
                db,
                organization_id=ORG_ID,
                event_type=EVENT_TYPE,
                data=PAYLOAD,
            )

        mock_trigger.assert_called_once_with(
            db,
            organization_id=ORG_ID,
            event_type=EVENT_TYPE,
            data=PAYLOAD,
        )
