"""
Tests for apps/api/app/routers/webhooks.py

All external dependencies are mocked:
  - Supabase DB via dependency override
  - Auth via dependency override (bypasses JWT)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from apps.api.app.dependencies import get_db, require_analyst
from apps.api.app.main import app
from apps.api.app.services.auth import AuthContext

# ─── Constants ─────────────────────────────────────────────────

ORG_ID = str(uuid.uuid4())
ORG_ID_OTHER = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
WEBHOOK_ID = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()


# ─── Helpers ───────────────────────────────────────────────────

def _make_jwt_auth(org_id: str = ORG_ID) -> AuthContext:
    return AuthContext(
        user_id=USER_ID,
        organization_id=org_id,
        role="analyst",
        auth_method="jwt",
    )


def _make_api_key_auth() -> AuthContext:
    return AuthContext(
        user_id=USER_ID,
        organization_id=ORG_ID,
        role="analyst",
        auth_method="api_key",
        api_key_id=str(uuid.uuid4()),
    )


def _make_webhook(**overrides) -> dict:
    base = {
        "id": WEBHOOK_ID,
        "organization_id": ORG_ID,
        "created_by": USER_ID,
        "url": "https://example.com/hook",
        "events": ["source.ready", "scan.completed"],
        "secret": "whsec_" + "a" * 32,
        "is_active": True,
        "created_at": NOW,
        "updated_at": NOW,
    }
    return {**base, **overrides}


def _make_delivery(**overrides) -> dict:
    base = {
        "id": str(uuid.uuid4()),
        "webhook_id": WEBHOOK_ID,
        "event_type": "source.ready",
        "payload": {"event": "source.ready"},
        "status": "delivered",
        "attempt": 1,
        "http_status": 200,
        "response_body": "OK",
        "next_retry_at": None,
        "created_at": NOW,
        "delivered_at": NOW,
    }
    return {**base, **overrides}


def _db_with_insert(row: dict) -> MagicMock:
    db = MagicMock()
    chain = MagicMock()
    for m in ("insert", "select", "eq", "update", "delete", "order", "range"):
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(data=[row])
    db.table.return_value = chain
    return db


def _db_with_select(rows: list[dict], count: int | None = None) -> MagicMock:
    db = MagicMock()
    chain = MagicMock()
    for m in ("select", "eq", "order", "range", "update", "delete", "insert"):
        getattr(chain, m).return_value = chain
    result = MagicMock(data=rows)
    result.count = count if count is not None else len(rows)
    chain.execute.return_value = result
    db.table.return_value = chain
    return db


def _db_empty() -> MagicMock:
    return _db_with_select([])


def override_jwt_auth(org_id: str = ORG_ID):
    auth = _make_jwt_auth(org_id)

    async def _dep():
        return auth

    return _dep


@pytest_asyncio.fixture
async def client():
    # Unique token per test so the rate limiter uses a separate bucket
    unique_token = f"test-{uuid.uuid4()}"
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {unique_token}"},
    ) as c:
        yield c


# ─── Create ─────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestCreateWebhook:
    async def test_create_returns_secret_once(self, client):
        """POST / returns whsec_ secret and webhook data."""
        row = _make_webhook()
        db = _db_with_insert(row)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            with patch(
                "apps.api.app.services.webhook_service.generate_webhook_secret",
                return_value="whsec_" + "b" * 32,
            ):
                r = await client.post(
                    "/api/v2/webhooks/",
                    json={"url": "https://example.com/hook", "events": ["source.ready"]},
                )
            assert r.status_code == 201
            data = r.json()["data"]
            assert "secret" in data
            assert data["secret"].startswith("whsec_")
            assert len(data["secret"]) == len("whsec_") + 32
        finally:
            app.dependency_overrides.clear()

    async def test_create_invalid_events(self, client):
        """POST / with unknown event type returns 422."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.post(
                "/api/v2/webhooks/",
                json={"url": "https://example.com/hook", "events": ["invalid.event"]},
            )
            assert r.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_create_empty_events(self, client):
        """POST / with empty events list returns 422."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.post(
                "/api/v2/webhooks/",
                json={"url": "https://example.com/hook", "events": []},
            )
            assert r.status_code == 422
        finally:
            app.dependency_overrides.clear()


# ─── List ───────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestListWebhooks:
    async def test_list_no_secret(self, client):
        """GET / response does not include 'secret' field."""
        row = _make_webhook()
        db = _db_with_select([row], count=1)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.get("/api/v2/webhooks/")
            assert r.status_code == 200
            for item in r.json()["data"]:
                assert "secret" not in item
        finally:
            app.dependency_overrides.clear()

    async def test_list_pagination(self, client):
        """GET /?page=1&per_page=5 returns correct pagination metadata."""
        rows = [_make_webhook(id=str(uuid.uuid4())) for _ in range(5)]
        db = _db_with_select(rows, count=15)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.get("/api/v2/webhooks/?page=1&per_page=5")
            assert r.status_code == 200
            body = r.json()
            assert body["total"] == 15
            assert body["pages"] == 3
        finally:
            app.dependency_overrides.clear()

    async def test_list_empty(self, client):
        """GET / returns empty list when no webhooks."""
        db = _db_with_select([], count=0)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.get("/api/v2/webhooks/")
            assert r.status_code == 200
            assert r.json()["data"] == []
        finally:
            app.dependency_overrides.clear()


# ─── Get Detail ─────────────────────────────────────────────────

@pytest.mark.asyncio
class TestGetWebhook:
    async def test_get_no_secret(self, client):
        """GET /{id} returns detail without secret."""
        row = _make_webhook()
        db = _db_with_select([row])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.get(f"/api/v2/webhooks/{WEBHOOK_ID}")
            assert r.status_code == 200
            data = r.json()["data"]
            assert data["id"] == WEBHOOK_ID
            assert "secret" not in data
        finally:
            app.dependency_overrides.clear()

    async def test_get_not_found(self, client):
        """GET /{id} returns 404 for unknown webhook."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.get(f"/api/v2/webhooks/{uuid.uuid4()}")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ─── Update ─────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestUpdateWebhook:
    async def test_update_events(self, client):
        """PATCH /{id} updates events."""
        updated = _make_webhook(events=["insight.created"])
        db = _db_with_select([updated])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.patch(
                f"/api/v2/webhooks/{WEBHOOK_ID}",
                json={"events": ["insight.created"]},
            )
            assert r.status_code == 200
            assert r.json()["data"]["events"] == ["insight.created"]
        finally:
            app.dependency_overrides.clear()

    async def test_update_invalid_events(self, client):
        """PATCH /{id} with invalid events returns 422."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.patch(
                f"/api/v2/webhooks/{WEBHOOK_ID}",
                json={"events": ["not.a.real.event"]},
            )
            assert r.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_update_empty_body(self, client):
        """PATCH /{id} with empty body returns 400."""
        db = _db_with_select([_make_webhook()])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.patch(f"/api/v2/webhooks/{WEBHOOK_ID}", json={})
            assert r.status_code == 400
        finally:
            app.dependency_overrides.clear()


# ─── Delete ─────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestDeleteWebhook:
    async def test_delete_returns_204(self, client):
        """DELETE /{id} returns 204."""
        db = _db_with_select([_make_webhook()])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.delete(f"/api/v2/webhooks/{WEBHOOK_ID}")
            assert r.status_code == 204
        finally:
            app.dependency_overrides.clear()

    async def test_delete_not_found(self, client):
        """DELETE /{id} returns 404 for unknown webhook."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.delete(f"/api/v2/webhooks/{uuid.uuid4()}")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ─── Rotate Secret ──────────────────────────────────────────────

@pytest.mark.asyncio
class TestRotateSecret:
    async def test_rotate_returns_new_secret(self, client):
        """POST /{id}/rotate-secret returns new whsec_ secret."""
        row = _make_webhook(secret="whsec_" + "c" * 32)
        db = _db_with_select([row])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            with patch(
                "apps.api.app.services.webhook_service.generate_webhook_secret",
                return_value="whsec_" + "c" * 32,
            ):
                r = await client.post(f"/api/v2/webhooks/{WEBHOOK_ID}/rotate-secret")
            assert r.status_code == 201
            data = r.json()["data"]
            assert "secret" in data
            assert data["secret"].startswith("whsec_")
        finally:
            app.dependency_overrides.clear()

    async def test_rotate_not_found(self, client):
        """POST rotate-secret on unknown webhook returns 404."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.post(f"/api/v2/webhooks/{uuid.uuid4()}/rotate-secret")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ─── Deliveries ─────────────────────────────────────────────────

@pytest.mark.asyncio
class TestDeliveries:
    async def test_get_deliveries_empty(self, client):
        """GET /{id}/deliveries returns empty list by default."""
        webhook_row = _make_webhook()
        db = MagicMock()
        chain = MagicMock()
        call_n = [0]

        for m in ("select", "eq", "order", "range", "update", "delete"):
            getattr(chain, m).return_value = chain

        def execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                # First call: _require_webhook
                result = MagicMock(data=[webhook_row])
                result.count = 1
                return result
            # Second call: deliveries
            result = MagicMock(data=[])
            result.count = 0
            return result

        chain.execute.side_effect = execute
        db.table.return_value = chain
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.get(f"/api/v2/webhooks/{WEBHOOK_ID}/deliveries")
            assert r.status_code == 200
            assert r.json()["data"] == []
            assert r.json()["total"] == 0
        finally:
            app.dependency_overrides.clear()

    async def test_get_deliveries_not_found(self, client):
        """GET /{id}/deliveries on unknown webhook returns 404."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.get(f"/api/v2/webhooks/{uuid.uuid4()}/deliveries")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ─── Test Event ─────────────────────────────────────────────────

@pytest.mark.asyncio
class TestSendTestEvent:
    async def test_creates_dispatch_job(self, client):
        """POST /{id}/test creates a dispatch_webhook job and returns 202."""
        webhook_row = _make_webhook()
        db = _db_with_select([webhook_row])
        job_row = {
            "id": str(uuid.uuid4()),
            "type": "dispatch_webhook",
            "status": "pending",
        }
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            with patch(
                "apps.api.app.routers.webhooks.create_job",
                new=AsyncMock(return_value=job_row),
            ):
                r = await client.post(f"/api/v2/webhooks/{WEBHOOK_ID}/test")
            assert r.status_code == 202
            data = r.json()["data"]
            assert "job_id" in data
            assert data["status"] == "accepted"
        finally:
            app.dependency_overrides.clear()

    async def test_test_event_not_found(self, client):
        """POST /{id}/test on unknown webhook returns 404."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.post(f"/api/v2/webhooks/{uuid.uuid4()}/test")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ─── Auth Guards ────────────────────────────────────────────────

@pytest.mark.asyncio
class TestAuthGuards:
    async def test_api_key_auth_rejected_on_create(self, client):
        """API key auth cannot create webhooks."""
        auth = _make_api_key_auth()
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = lambda: auth
        try:
            r = await client.post(
                "/api/v2/webhooks/",
                json={"url": "https://example.com/hook", "events": ["source.ready"]},
            )
            assert r.status_code == 403
        finally:
            app.dependency_overrides.clear()

    async def test_api_key_auth_rejected_on_list(self, client):
        """API key auth cannot list webhooks."""
        auth = _make_api_key_auth()
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = lambda: auth
        try:
            r = await client.get("/api/v2/webhooks/")
            assert r.status_code == 403
        finally:
            app.dependency_overrides.clear()


# ─── Cross-org Isolation ─────────────────────────────────────────

@pytest.mark.asyncio
class TestCrossOrgIsolation:
    async def test_cannot_access_other_org_webhook(self, client):
        """User from org A cannot access webhook from org B."""
        # DB returns empty because org filter doesn't match
        db = _db_with_select([])
        # Auth with different org than the webhook's org
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth(ORG_ID_OTHER)
        try:
            r = await client.get(f"/api/v2/webhooks/{WEBHOOK_ID}")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()
