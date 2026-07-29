"""
Tests for the Investigations router (apps/api/app/routers/investigations.py).

All external dependencies are mocked:
  - Supabase DB via dependency override
  - Auth via dependency override (bypasses JWT)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from apps.api.app.dependencies import get_db, require_auth, require_viewer
from apps.api.app.main import app
from apps.api.app.services.auth import AuthContext

# ─── Fixtures ──────────────────────────────────────────────────

ORG_ID = str(uuid.uuid4())
DEAL_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
FINDING_ID = str(uuid.uuid4())
INVESTIGATION_ID = str(uuid.uuid4())

NOW = datetime.now(timezone.utc).isoformat()


def _make_auth() -> AuthContext:
    return AuthContext(user_id=USER_ID, organization_id=ORG_ID, role="analyst")


def _make_investigation(**overrides) -> dict:
    base = {
        "id": INVESTIGATION_ID,
        "workspace_id": DEAL_ID,
        "organization_id": ORG_ID,
        "insight_id": FINDING_ID,
        "requested_by": USER_ID,
        "question": "What is the revenue trend?",
        "scope": "documents",
        "status": "completed",
        "report": "## Revenue Analysis\n\nThe revenue shows...",
        "web_sources": None,
        "doc_references": [
            {"source_id": "src-1", "page": 5, "section": "Financials", "quote": "..."}
        ],
        "input_tokens": 12000,
        "output_tokens": 3500,
        "cost_usd": 0.045,
        "model_used": "claude-sonnet-4-20250514",
        "created_at": NOW,
        "started_at": NOW,
        "completed_at": NOW,
    }
    return {**base, **overrides}


def _make_chain(*, deal_exists: bool = True, results: list | None = None):
    """Build a chain mock for list endpoints (workspace check + list query)."""
    call_n = [0]
    chain = MagicMock()
    for m in ("select", "eq", "order"):
        getattr(chain, m).return_value = chain

    def execute():
        n = call_n[0]
        call_n[0] += 1
        if n == 0:
            return MagicMock(data=[{"id": DEAL_ID}] if deal_exists else [])
        return MagicMock(data=results or [])

    chain.execute.side_effect = execute
    db = MagicMock()
    db.table.return_value = chain
    return db, chain


def _make_single_chain(*, result: dict | None = None):
    """Build a chain mock for detail endpoints (single query)."""
    chain = MagicMock()
    for m in ("select", "eq", "order"):
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(data=[result] if result is not None else [])
    db = MagicMock()
    db.table.return_value = chain
    return db, chain


def override_auth():
    auth = _make_auth()

    async def _dep():
        return auth

    app.dependency_overrides[require_auth] = _dep
    return _dep


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# ─── Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestListInvestigations:
    async def test_list_investigations_empty(self, client):
        """GET returns [] when no investigations exist."""
        db, _ = _make_chain(results=[])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = override_auth()
        try:
            r = await client.get(f"/api/v2/workspaces/{DEAL_ID}/investigations/")
            assert r.status_code == 200
            assert r.json()["data"] == []
        finally:
            app.dependency_overrides.clear()

    async def test_list_investigations_with_results(self, client):
        """GET returns existing investigations."""
        inv = [_make_investigation(), _make_investigation(id=str(uuid.uuid4()))]
        db, _ = _make_chain(results=inv)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = override_auth()
        try:
            r = await client.get(f"/api/v2/workspaces/{DEAL_ID}/investigations/")
            assert r.status_code == 200
            assert len(r.json()["data"]) == 2
        finally:
            app.dependency_overrides.clear()

    async def test_list_investigations_filter_by_status(self, client):
        """GET ?status=completed applies eq filter."""
        inv = [_make_investigation()]
        db, chain = _make_chain(results=inv)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = override_auth()
        try:
            r = await client.get(
                f"/api/v2/workspaces/{DEAL_ID}/investigations/?status=completed"
            )
            assert r.status_code == 200
            assert len(r.json()["data"]) == 1
            chain.eq.assert_any_call("status", "completed")
        finally:
            app.dependency_overrides.clear()

    async def test_list_investigations_filter_by_finding_id(self, client):
        """GET ?insight_id=xxx applies eq filter."""
        inv = [_make_investigation()]
        db, chain = _make_chain(results=inv)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = override_auth()
        try:
            r = await client.get(
                f"/api/v2/workspaces/{DEAL_ID}/investigations/?insight_id={FINDING_ID}"
            )
            assert r.status_code == 200
            chain.eq.assert_any_call("insight_id", FINDING_ID)
        finally:
            app.dependency_overrides.clear()

    async def test_list_investigations_deal_not_found(self, client):
        """GET returns 404 if workspace not in org."""
        db, _ = _make_chain(deal_exists=False)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = override_auth()
        try:
            r = await client.get(f"/api/v2/workspaces/{DEAL_ID}/investigations/")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestGetInvestigation:
    async def test_get_investigation_completed(self, client):
        """GET detail returns investigation with report."""
        inv = _make_investigation()
        db, _ = _make_single_chain(result=inv)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = override_auth()
        try:
            r = await client.get(
                f"/api/v2/workspaces/{DEAL_ID}/investigations/{INVESTIGATION_ID}"
            )
            assert r.status_code == 200
            assert r.json()["data"]["report"] == inv["report"]
            assert r.json()["data"]["status"] == "completed"
        finally:
            app.dependency_overrides.clear()

    async def test_get_investigation_pending(self, client):
        """GET detail returns investigation with report=null when pending."""
        inv = _make_investigation(status="pending", report=None, completed_at=None)
        db, _ = _make_single_chain(result=inv)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = override_auth()
        try:
            r = await client.get(
                f"/api/v2/workspaces/{DEAL_ID}/investigations/{INVESTIGATION_ID}"
            )
            assert r.status_code == 200
            assert r.json()["data"]["report"] is None
            assert r.json()["data"]["status"] == "pending"
        finally:
            app.dependency_overrides.clear()

    async def test_get_investigation_not_found(self, client):
        """GET returns 404 if investigation does not exist."""
        db, _ = _make_single_chain(result=None)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = override_auth()
        try:
            r = await client.get(
                f"/api/v2/workspaces/{DEAL_ID}/investigations/{str(uuid.uuid4())}"
            )
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()
