"""
Tests for apps/api/app/services/webhook_service.py

DB fully mocked. Covers all service functions.
"""

import uuid
from unittest.mock import MagicMock

import pytest

from apps.api.app.services.webhook_service import (
    SECRET_PREFIX,
    create_webhook,
    generate_webhook_secret,
    list_webhook_deliveries,
    list_webhooks,
    rotate_webhook_secret,
)

ORG_ID = str(uuid.uuid4())
WEBHOOK_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
NOW = "2026-03-17T00:00:00+00:00"


def _make_webhook_row(**overrides) -> dict:
    base = {
        "id": WEBHOOK_ID,
        "organization_id": ORG_ID,
        "created_by": USER_ID,
        "url": "https://example.com/hook",
        "events": ["source.ready"],
        "secret": SECRET_PREFIX + "a" * 32,
        "is_active": True,
        "created_at": NOW,
        "updated_at": NOW,
    }
    return {**base, **overrides}


def _db_chain(rows: list[dict], count: int | None = None) -> MagicMock:
    """Fluent Supabase chain mock."""
    db = MagicMock()
    chain = MagicMock()
    for m in ("select", "insert", "update", "delete", "eq", "order", "range"):
        getattr(chain, m).return_value = chain
    result = MagicMock(data=rows)
    result.count = count if count is not None else len(rows)
    chain.execute.return_value = result
    db.table.return_value = chain
    return db


# ─── generate_webhook_secret ────────────────────────────────────


class TestGenerateWebhookSecret:
    def test_starts_with_prefix(self):
        """Secret starts with 'whsec_'."""
        secret = generate_webhook_secret()
        assert secret.startswith(SECRET_PREFIX)

    def test_correct_total_length(self):
        """Secret is prefix + 32 hex chars (16 bytes)."""
        secret = generate_webhook_secret()
        expected_len = len(SECRET_PREFIX) + 32  # 16 bytes = 32 hex chars
        assert len(secret) == expected_len

    def test_hex_part_is_hexadecimal(self):
        """The hex part contains only valid hex characters."""
        secret = generate_webhook_secret()
        hex_part = secret[len(SECRET_PREFIX) :]
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_secrets_are_unique(self):
        """Two successive calls produce different secrets."""
        assert generate_webhook_secret() != generate_webhook_secret()


# ─── create_webhook ─────────────────────────────────────────────


@pytest.mark.asyncio
class TestCreateWebhook:
    async def test_returns_row_and_secret(self):
        """Returns (row, secret) tuple with valid secret."""
        row = _make_webhook_row()
        db = _db_chain([row])
        result_row, secret = await create_webhook(
            db,
            url="https://example.com/hook",
            events=["source.ready"],
            is_active=True,
            organization_id=ORG_ID,
            created_by=USER_ID,
        )
        assert result_row["id"] == WEBHOOK_ID
        assert secret.startswith(SECRET_PREFIX)
        assert len(secret) == len(SECRET_PREFIX) + 32

    async def test_secret_stored_in_insert(self):
        """The generated secret is included in the DB insert."""
        row = _make_webhook_row()
        db = MagicMock()
        chain = MagicMock()
        for m in ("update", "delete", "eq", "order", "range"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[row])

        inserted_data = [None]

        def _insert(payload):
            inserted_data[0] = payload
            mock_c = MagicMock()
            mock_c.execute.return_value = MagicMock(data=[row])
            return mock_c

        chain.insert.side_effect = _insert
        db.table.return_value = chain

        _, secret = await create_webhook(
            db,
            url="https://example.com/hook",
            events=["source.ready"],
            is_active=True,
            organization_id=ORG_ID,
            created_by=USER_ID,
        )
        assert inserted_data[0]["secret"] == secret
        assert inserted_data[0]["organization_id"] == ORG_ID


# ─── rotate_webhook_secret ──────────────────────────────────────


@pytest.mark.asyncio
class TestRotateWebhookSecret:
    async def test_returns_new_secret(self):
        """Returns a new secret different from the original."""
        original_secret = SECRET_PREFIX + "a" * 32
        row = _make_webhook_row(secret=SECRET_PREFIX + "b" * 32)
        # First call: verify webhook exists; second call: update
        db = MagicMock()
        chain = MagicMock()
        for m in ("select", "update", "eq", "order", "range"):
            getattr(chain, m).return_value = chain
        call_n = [0]

        def _execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                return MagicMock(data=[{"id": WEBHOOK_ID}])
            return MagicMock(data=[row])

        chain.execute.side_effect = _execute
        db.table.return_value = chain

        result_row, new_secret = await rotate_webhook_secret(
            db,
            webhook_id=WEBHOOK_ID,
            organization_id=ORG_ID,
        )
        assert new_secret.startswith(SECRET_PREFIX)
        assert new_secret != original_secret

    async def test_not_found_raises_404(self):
        """Raises HTTPException 404 if webhook not found."""
        from fastapi import HTTPException

        db = _db_chain([])
        with pytest.raises(HTTPException) as exc_info:
            await rotate_webhook_secret(
                db,
                webhook_id=str(uuid.uuid4()),
                organization_id=ORG_ID,
            )
        assert exc_info.value.status_code == 404


# ─── list_webhooks ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestListWebhooks:
    async def test_returns_items_and_total(self):
        """Returns (items, total) tuple."""
        rows = [_make_webhook_row(), _make_webhook_row(id=str(uuid.uuid4()))]
        db = _db_chain(rows, count=10)
        items, total = await list_webhooks(
            db, organization_id=ORG_ID, page=1, per_page=5
        )
        assert len(items) == 2
        assert total == 10

    async def test_empty_returns_zero_total(self):
        """Empty org returns empty list and total 0."""
        db = _db_chain([], count=0)
        items, total = await list_webhooks(
            db, organization_id=ORG_ID, page=1, per_page=10
        )
        assert items == []
        assert total == 0

    async def test_pagination_offset_computed_correctly(self):
        """Offset is computed as (page-1) * per_page."""
        db = MagicMock()
        chain = MagicMock()
        for m in ("select", "eq", "order"):
            getattr(chain, m).return_value = chain

        range_args = [None]

        def _range(start, end):
            range_args[0] = (start, end)
            mock_c = MagicMock()
            mock_c.execute.return_value = MagicMock(data=[], count=0)
            return mock_c

        chain.range.side_effect = _range
        db.table.return_value = chain

        await list_webhooks(db, organization_id=ORG_ID, page=3, per_page=5)
        # page=3, per_page=5 → offset=10
        assert range_args[0] == (10, 14)


# ─── list_webhook_deliveries ────────────────────────────────────


@pytest.mark.asyncio
class TestListWebhookDeliveries:
    async def test_returns_deliveries_and_total(self):
        """Returns (deliveries, total) for a webhook."""
        delivery = {
            "id": str(uuid.uuid4()),
            "webhook_id": WEBHOOK_ID,
            "status": "delivered",
            "http_status": 200,
        }
        db = _db_chain([delivery], count=1)
        items, total = await list_webhook_deliveries(
            db, webhook_id=WEBHOOK_ID, page=1, per_page=10
        )
        assert len(items) == 1
        assert total == 1
        assert items[0]["webhook_id"] == WEBHOOK_ID

    async def test_empty_deliveries_returns_zero(self):
        """No deliveries returns empty list and total 0."""
        db = _db_chain([], count=0)
        items, total = await list_webhook_deliveries(
            db, webhook_id=WEBHOOK_ID, page=1, per_page=10
        )
        assert items == []
        assert total == 0

    async def test_pagination_offset_for_deliveries(self):
        """Offset computed correctly for page 2."""
        db = MagicMock()
        chain = MagicMock()
        for m in ("select", "eq", "order"):
            getattr(chain, m).return_value = chain

        range_args = [None]

        def _range(start, end):
            range_args[0] = (start, end)
            mock_c = MagicMock()
            mock_c.execute.return_value = MagicMock(data=[], count=0)
            return mock_c

        chain.range.side_effect = _range
        db.table.return_value = chain

        await list_webhook_deliveries(db, webhook_id=WEBHOOK_ID, page=2, per_page=10)
        # page=2, per_page=10 → offset=10
        assert range_args[0] == (10, 19)
