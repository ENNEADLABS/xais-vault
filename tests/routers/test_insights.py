"""
Tests for apps/api/app/routers/insights.py

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

from apps.api.app.dependencies import (
    get_db,
    require_analyst,
    require_auth,
    require_viewer,
)
from apps.api.app.main import app
from apps.api.app.services.auth import AuthContext

# ─── Constants ─────────────────────────────────────────────────

ORG_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
DEAL_ID = str(uuid.uuid4())
FINDING_ID = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()
BASE = f"/api/v2/workspaces/{DEAL_ID}/insights"


# ─── Helpers ───────────────────────────────────────────────────


def _make_insight(**overrides) -> dict:
    base = {
        "id": FINDING_ID,
        "workspace_id": DEAL_ID,
        "organization_id": ORG_ID,
        "type": "red_flag",
        "severity": "high",
        "confidence_score": 85,
        "title": "Incohérence",
        "description": "Desc",
        "source_id": None,
        "source_page": None,
        "source_section": None,
        "source_quote": None,
        "status": "pending",
        "reviewed_by": None,
        "reviewed_at": None,
        "verification": None,
        "metadata": {},
        "created_at": NOW,
        "updated_at": NOW,
    }
    return {**base, **overrides}


def _make_auth(role: str = "analyst") -> AuthContext:
    return AuthContext(
        user_id=USER_ID, organization_id=ORG_ID, role=role, auth_method="jwt"
    )


def _db_with_select(rows: list[dict]) -> MagicMock:
    db = MagicMock()
    chain = MagicMock()
    for m in ("select", "eq", "order", "update"):
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(data=rows)
    db.table.return_value = chain
    return db


def _override_auth(role: str = "analyst"):
    auth = _make_auth(role)

    async def _dep():
        return auth

    app.dependency_overrides[require_auth] = _dep
    return _dep


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ─── List Insights ─────────────────────────────────────────────


@pytest.mark.asyncio
class TestListInsights:
    async def test_list_empty(self, client):
        """GET / returns 200 with empty list."""
        db = _db_with_select([])
        # First call: workspace check, second: insights
        call_count = [0]
        original_execute = db.table.return_value.execute

        def side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(data=[{"id": DEAL_ID}])  # workspace exists
            return MagicMock(data=[])  # no insights

        db.table.return_value.execute.side_effect = side_effect
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get(f"{BASE}/")
            assert r.status_code == 200
            assert r.json()["data"] == []
        finally:
            app.dependency_overrides.clear()

    async def test_list_with_insights(self, client):
        """GET / returns insights list."""
        insight = _make_insight()
        db = _db_with_select([])
        call_count = [0]

        def side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(data=[{"id": DEAL_ID}])
            return MagicMock(data=[insight])

        db.table.return_value.execute.side_effect = side_effect
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get(f"{BASE}/")
            assert r.status_code == 200
            assert r.json()["data"][0]["id"] == FINDING_ID
        finally:
            app.dependency_overrides.clear()

    async def test_list_deal_not_found(self, client):
        """GET / returns 404 if workspace doesn't belong to org."""
        db = _db_with_select([])
        db.table.return_value.execute.return_value = MagicMock(data=[])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get(f"{BASE}/")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ─── Get Insight ───────────────────────────────────────────────


@pytest.mark.asyncio
class TestGetInsight:
    async def test_get_success(self, client):
        """GET /{insight_id} returns 200."""
        db = _db_with_select([_make_insight()])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get(f"{BASE}/{FINDING_ID}")
            assert r.status_code == 200
            assert r.json()["data"]["id"] == FINDING_ID
        finally:
            app.dependency_overrides.clear()

    async def test_get_not_found(self, client):
        """GET /{insight_id} returns 404 for unknown ID."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get(f"{BASE}/{uuid.uuid4()}")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ─── Update Insight Status ────────────────────────────────────


@pytest.mark.asyncio
class TestUpdateInsight:
    async def test_confirm(self, client):
        """PATCH /{insight_id} with action=confirm returns confirmed insight."""
        insight = _make_insight()
        confirmed = _make_insight(status="confirmed", reviewed_by=USER_ID)
        db = _db_with_select([])
        call_count = [0]

        def side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(data=[insight])  # require_one check
            return MagicMock(data=[confirmed])  # after update

        db.table.return_value.execute.side_effect = side_effect
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.patch(f"{BASE}/{FINDING_ID}", json={"action": "confirm"})
            assert r.status_code == 200
            assert r.json()["data"]["status"] == "confirmed"
        finally:
            app.dependency_overrides.clear()

    async def test_reject(self, client):
        """PATCH /{insight_id} with action=reject returns rejected insight."""
        insight = _make_insight()
        rejected = _make_insight(status="rejected", reviewed_by=USER_ID)
        db = _db_with_select([])
        call_count = [0]

        def side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(data=[insight])
            return MagicMock(data=[rejected])

        db.table.return_value.execute.side_effect = side_effect
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.patch(f"{BASE}/{FINDING_ID}", json={"action": "reject"})
            assert r.status_code == 200
            assert r.json()["data"]["status"] == "rejected"
        finally:
            app.dependency_overrides.clear()

    async def test_investigate(self, client):
        """PATCH /{insight_id} with action=investigate returns 200 with job_id."""
        insight = _make_insight()
        investigating = _make_insight(status="investigating")
        db = _db_with_select([])
        call_count = [0]

        def side_effect():
            call_count[0] += 1
            if call_count[0] <= 2:
                return MagicMock(data=[insight])
            return MagicMock(data=[investigating])

        db.table.return_value.execute.side_effect = side_effect
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            with (
                patch(
                    "apps.api.app.routers.insights.check_analysis_limit",
                    new_callable=AsyncMock,
                ),
                patch(
                    "apps.api.app.routers.insights.create_job",
                    new_callable=AsyncMock,
                    return_value={"id": "job-verify-1"},
                ),
            ):
                r = await client.patch(
                    f"{BASE}/{FINDING_ID}", json={"action": "investigate"}
                )
            assert r.status_code == 200
            assert r.json()["meta"]["job_id"] == "job-verify-1"
        finally:
            app.dependency_overrides.clear()

    async def test_update_not_found(self, client):
        """PATCH /{insight_id} returns 404 for unknown insight."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.patch(f"{BASE}/{uuid.uuid4()}", json={"action": "confirm"})
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_invalid_action(self, client):
        """PATCH /{insight_id} with invalid action returns 422."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.patch(f"{BASE}/{FINDING_ID}", json={"action": "invalid"})
            assert r.status_code == 422
        finally:
            app.dependency_overrides.clear()
