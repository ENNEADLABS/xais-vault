"""
Tests for apps/api/app/routers/workspaces.py

All external dependencies are mocked:
  - Supabase DB via dependency override
  - Auth via dependency override (bypasses JWT)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
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
NOW = datetime.now(timezone.utc).isoformat()


# ─── Helpers ───────────────────────────────────────────────────


def _make_deal(**overrides) -> dict:
    base = {
        "id": DEAL_ID,
        "name": "Acme Corp",
        "emoji": "🚀",
        "description": "Test workspace",
        "status": "active",
        "deal_type": "equity",
        "sector": "tech",
        "target_company": "Acme SAS",
        "scan_status": "pending",
        "scan_summary": None,
        "organization_id": ORG_ID,
        "created_by": USER_ID,
        "created_at": NOW,
        "updated_at": NOW,
    }
    return {**base, **overrides}


def _make_auth(role: str = "analyst") -> AuthContext:
    return AuthContext(
        user_id=USER_ID, organization_id=ORG_ID, role=role, auth_method="jwt"
    )


def _db_with_insert(row: dict) -> MagicMock:
    db = MagicMock()
    chain = MagicMock()
    chain.insert.return_value = chain
    chain.execute.return_value = MagicMock(data=[row])
    db.table.return_value = chain
    return db


def _db_with_select(rows: list[dict], count: int | None = None) -> MagicMock:
    db = MagicMock()
    chain = MagicMock()
    for m in ("select", "eq", "order", "range", "update", "delete", "neq", "in_"):
        getattr(chain, m).return_value = chain
    result = MagicMock(data=rows)
    result.count = count if count is not None else len(rows)
    chain.execute.return_value = result
    db.table.return_value = chain
    return db


def _db_with_table_dispatch(
    table_rows: dict[str, list],
    counts: dict[str, int] | None = None,
) -> MagicMock:
    """Mock DB returning different data per table name."""
    db = MagicMock()

    def make_chain(rows: list, count: int) -> MagicMock:
        chain = MagicMock()
        for m in ("select", "eq", "order", "range", "update", "delete", "neq", "in_"):
            getattr(chain, m).return_value = chain
        result = MagicMock(data=rows)
        result.count = count
        chain.execute.return_value = result
        return chain

    def side_effect(name: str) -> MagicMock:
        rows = table_rows.get(name, [])
        count = (counts or {}).get(name, len(rows))
        return make_chain(rows, count)

    db.table.side_effect = side_effect
    return db


def _override_auth(role: str = "analyst"):
    auth = _make_auth(role)

    async def _dep():
        return auth

    # Scope deps (require_scope_dep) depend on require_auth — override it too
    # so they resolve against the same stub AuthContext.
    app.dependency_overrides[require_auth] = _dep
    return _dep


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ─── Create ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestCreateDeal:
    async def test_create_success(self, client):
        """POST / creates a workspace and returns 201."""
        workspace = _make_deal()
        db = _db_with_insert(workspace)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            with patch(
                "apps.api.app.routers.workspaces.check_workspace_limit", new_callable=AsyncMock
            ):
                r = await client.post("/api/v2/workspaces/", json={"name": "Acme Corp"})
            assert r.status_code == 201
            data = r.json()["data"]
            assert data["id"] == DEAL_ID
            assert data["name"] == "Acme Corp"
            assert data["status"] == "active"
        finally:
            app.dependency_overrides.clear()

    async def test_create_missing_name(self, client):
        """POST / without name returns 422."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.post("/api/v2/workspaces/", json={})
            assert r.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_create_empty_name(self, client):
        """POST / with empty name returns 422."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.post("/api/v2/workspaces/", json={"name": ""})
            assert r.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_create_with_optional_fields(self, client):
        """POST / with optional fields returns 201 with those fields."""
        workspace = _make_deal(sector="FinTech", deal_type="equity")
        db = _db_with_insert(workspace)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            with patch(
                "apps.api.app.routers.workspaces.check_workspace_limit", new_callable=AsyncMock
            ):
                r = await client.post(
                    "/api/v2/workspaces/",
                    json={
                        "name": "Acme Corp",
                        "sector": "FinTech",
                        "deal_type": "equity",
                    },
                )
            assert r.status_code == 201
            assert r.json()["data"]["sector"] == "FinTech"
        finally:
            app.dependency_overrides.clear()

    async def test_create_deal_limit_exceeded(self, client):
        """POST / returns 403 when workspace limit is reached."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            with patch(
                "apps.api.app.routers.workspaces.check_workspace_limit",
                new_callable=AsyncMock,
                side_effect=HTTPException(status_code=403, detail="Workspace limit reached"),
            ):
                r = await client.post("/api/v2/workspaces/", json={"name": "X"})
            assert r.status_code == 403
        finally:
            app.dependency_overrides.clear()

    async def test_create_invalid_deal_type(self, client):
        """POST / with deal_type not in enum → 422 validation error."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.post(
                "/api/v2/workspaces/",
                json={"name": "Acme", "deal_type": "invalid"},
            )
            assert r.status_code == 422
        finally:
            app.dependency_overrides.clear()


# ─── List ───────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestListDeals:
    async def test_list_empty(self, client):
        """GET / returns empty list with total=0."""
        db = _db_with_table_dispatch(
            {"workspaces_with_counts": []}, counts={"workspaces_with_counts": 0}
        )
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get("/api/v2/workspaces/")
            assert r.status_code == 200
            body = r.json()
            assert body["data"] == []
            assert body["total"] == 0
        finally:
            app.dependency_overrides.clear()

    async def test_list_pagination(self, client):
        """GET /?per_page=5 returns pages=4 for 20 total."""
        workspaces = [
            _make_deal(id=str(uuid.uuid4()), source_count=0, insight_count=0)
            for _ in range(5)
        ]
        db = _db_with_table_dispatch(
            {"workspaces_with_counts": workspaces},
            counts={"workspaces_with_counts": 20},
        )
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get("/api/v2/workspaces/?per_page=5")
            assert r.status_code == 200
            body = r.json()
            assert body["total"] == 20
            assert body["pages"] == 4
        finally:
            app.dependency_overrides.clear()

    async def test_list_enriches_counts(self, client):
        """GET / les counts viennent directement de la vue workspaces_with_counts."""
        workspace = _make_deal(source_count=3, insight_count=5)
        db = _db_with_table_dispatch(
            {"workspaces_with_counts": [workspace]},
            counts={"workspaces_with_counts": 1},
        )
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get("/api/v2/workspaces/")
            assert r.status_code == 200
            item = r.json()["data"][0]
            assert item["source_count"] == 3
            assert item["insight_count"] == 5
        finally:
            app.dependency_overrides.clear()

    async def test_list_invalid_status(self, client):
        """GET /?status=invalid returns 422."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get("/api/v2/workspaces/?status=invalid")
            assert r.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_list_filter_by_status(self, client):
        """GET /?status=active returns only matching workspaces."""
        workspace = _make_deal(source_count=0, insight_count=0)
        db = _db_with_table_dispatch(
            {"workspaces_with_counts": [workspace]},
            counts={"workspaces_with_counts": 1},
        )
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get("/api/v2/workspaces/?status=active")
            assert r.status_code == 200
            assert len(r.json()["data"]) == 1
        finally:
            app.dependency_overrides.clear()


# ─── Get ────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestGetDeal:
    async def test_get_success(self, client):
        """GET /{workspace_id} returns 200 with enriched workspace (counts from view)."""
        workspace = _make_deal(source_count=2, insight_count=1)
        db = _db_with_table_dispatch(
            {"workspaces_with_counts": [workspace]},
            counts={"workspaces_with_counts": 1},
        )
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get(f"/api/v2/workspaces/{DEAL_ID}")
            assert r.status_code == 200
            data = r.json()["data"]
            assert data["id"] == DEAL_ID
            assert data["source_count"] == 2
            assert data["insight_count"] == 1
        finally:
            app.dependency_overrides.clear()

    async def test_get_not_found(self, client):
        """GET /{workspace_id} returns 404 for unknown ID."""
        db = _db_with_table_dispatch(
            {"workspaces_with_counts": []}, counts={"workspaces_with_counts": 0}
        )
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get(f"/api/v2/workspaces/{uuid.uuid4()}")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ─── Update ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestUpdateDeal:
    async def test_update_name(self, client):
        """PATCH /{workspace_id} updates name and returns 200."""
        updated = _make_deal(name="New Name")
        db = _db_with_select([updated])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.patch(
                f"/api/v2/workspaces/{DEAL_ID}", json={"name": "New Name"}
            )
            assert r.status_code == 200
            assert r.json()["data"]["name"] == "New Name"
        finally:
            app.dependency_overrides.clear()

    async def test_update_status(self, client):
        """PATCH /{workspace_id} updates status and returns 200."""
        updated = _make_deal(status="archived")
        db = _db_with_select([updated])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.patch(
                f"/api/v2/workspaces/{DEAL_ID}", json={"status": "archived"}
            )
            assert r.status_code == 200
            assert r.json()["data"]["status"] == "archived"
        finally:
            app.dependency_overrides.clear()

    async def test_update_empty_body(self, client):
        """PATCH /{workspace_id} with empty body returns 400."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.patch(f"/api/v2/workspaces/{DEAL_ID}", json={})
            assert r.status_code == 400
        finally:
            app.dependency_overrides.clear()

    async def test_update_not_found(self, client):
        """PATCH /{workspace_id} returns 404 for unknown workspace."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.patch(f"/api/v2/workspaces/{uuid.uuid4()}", json={"name": "X"})
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_update_invalid_status(self, client):
        """PATCH /{workspace_id} with status not in enum → 422 validation error."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.patch(
                f"/api/v2/workspaces/{DEAL_ID}", json={"status": "invalid"}
            )
            assert r.status_code == 422
        finally:
            app.dependency_overrides.clear()


# ─── Delete ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDeleteDeal:
    async def test_delete_success(self, client):
        """DELETE /{workspace_id} returns 204."""
        db = _db_with_select([{"id": DEAL_ID}])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.delete(f"/api/v2/workspaces/{DEAL_ID}")
            assert r.status_code == 204
        finally:
            app.dependency_overrides.clear()

    async def test_delete_not_found(self, client):
        """DELETE /{workspace_id} returns 404 for unknown ID."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.delete(f"/api/v2/workspaces/{uuid.uuid4()}")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ─── Suggested questions ───────────────────────────────────────


@pytest.mark.asyncio
class TestSuggestedQuestions:
    """GET /{workspace_id}/suggested-questions — aggregated pre-computed questions."""

    def _db_with_deal_and_sources(
        self, deal_exists: bool, sources: list[dict]
    ) -> MagicMock:
        """Mock DB that dispatches by table: workspaces → existence, sources → rows."""
        db = MagicMock()

        def _build_chain(rows: list[dict]) -> MagicMock:
            chain = MagicMock()
            for m in ("select", "eq", "order"):
                getattr(chain, m).return_value = chain
            chain.execute.return_value = MagicMock(data=rows)
            return chain

        deal_chain = _build_chain([{"id": DEAL_ID}] if deal_exists else [])
        sources_chain = _build_chain(sources)

        def side_effect(name: str) -> MagicMock:
            return deal_chain if name == "workspaces" else sources_chain

        db.table.side_effect = side_effect
        return db

    async def test_returns_200_with_questions(self, client):
        """Returns aggregated, deduped questions with source metadata."""
        sources = [
            {
                "id": "s1",
                "name": "Business Plan.pdf",
                "suggested_questions": ["Quel est le CA ?"],
            },
            {
                "id": "s2",
                "name": "Term Sheet.pdf",
                "suggested_questions": ["Quelle est la valorisation ?"],
            },
        ]
        db = self._db_with_deal_and_sources(True, sources)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth()
        try:
            r = await client.get(f"/api/v2/workspaces/{DEAL_ID}/suggested-questions")
            assert r.status_code == 200
            data = r.json()
            assert len(data) == 2
            assert data[0]["question"] == "Quel est le CA ?"
            assert data[0]["source_name"] == "Business Plan.pdf"
        finally:
            app.dependency_overrides.clear()

    async def test_deal_not_found_returns_404(self, client):
        """Workspace missing or belonging to another org → 404 (defense in depth)."""
        db = self._db_with_deal_and_sources(False, [])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth()
        try:
            r = await client.get(f"/api/v2/workspaces/{uuid.uuid4()}/suggested-questions")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_empty_sources_returns_empty_list(self, client):
        """Workspace exists but no ready sources → 200 with []."""
        db = self._db_with_deal_and_sources(True, [])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth()
        try:
            r = await client.get(f"/api/v2/workspaces/{DEAL_ID}/suggested-questions")
            assert r.status_code == 200
            assert r.json() == []
        finally:
            app.dependency_overrides.clear()

    async def test_limit_validated(self, client):
        """limit > 20 → 422 validation error."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_viewer] = _override_auth()
        try:
            r = await client.get(
                f"/api/v2/workspaces/{DEAL_ID}/suggested-questions?limit=100"
            )
            assert r.status_code == 422
        finally:
            app.dependency_overrides.clear()


# ─── API key scope enforcement ─────────────────────────────────
# Regression tests for OWASP A04: API keys must carry the required scope.


@pytest.mark.asyncio
class TestApiKeyScopeEnforcement:
    """API keys are `auth_method="api_key"` with a restricted scope list.
    Wildcard `*` keeps backward compat. JWT users bypass the check entirely."""

    def _api_key_auth(self, scopes: list[str]) -> AuthContext:
        return AuthContext(
            user_id=USER_ID,
            organization_id=ORG_ID,
            role="analyst",
            auth_method="api_key",
            api_key_id="key-123",
            scopes=scopes,
        )

    def _override_with(self, auth: AuthContext):
        async def _dep():
            return auth

        app.dependency_overrides[require_auth] = _dep
        return _dep

    async def test_read_only_key_blocked_on_write(self, client):
        """API key with only workspaces:read → 403 on POST /workspaces (workspaces:write)."""
        auth = self._api_key_auth(["workspaces:read"])
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = self._override_with(auth)
        try:
            with patch(
                "apps.api.app.routers.workspaces.check_workspace_limit", new_callable=AsyncMock
            ):
                r = await client.post("/api/v2/workspaces/", json={"name": "Acme"})
            assert r.status_code == 403
            assert "scope" in r.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    async def test_write_key_allowed_on_write(self, client):
        """API key with workspaces:write → 201 on POST /workspaces."""
        workspace = _make_deal()
        auth = self._api_key_auth(["workspaces:write"])
        db = _db_with_insert(workspace)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = self._override_with(auth)
        try:
            with patch(
                "apps.api.app.routers.workspaces.check_workspace_limit", new_callable=AsyncMock
            ):
                r = await client.post("/api/v2/workspaces/", json={"name": "Acme Corp"})
            assert r.status_code == 201
        finally:
            app.dependency_overrides.clear()

    async def test_wildcard_scope_allowed_everywhere(self, client):
        """API key with `*` scope works on any endpoint (legacy/admin key)."""
        workspace = _make_deal()
        auth = self._api_key_auth(["*"])
        db = _db_with_insert(workspace)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = self._override_with(auth)
        try:
            with patch(
                "apps.api.app.routers.workspaces.check_workspace_limit", new_callable=AsyncMock
            ):
                r = await client.post("/api/v2/workspaces/", json={"name": "Acme Corp"})
            assert r.status_code == 201
        finally:
            app.dependency_overrides.clear()

    async def test_jwt_user_bypasses_scope_check(self, client):
        """JWT users have no `scopes` — scope enforcement skips them entirely."""
        # Default _make_auth → auth_method="jwt", scopes=None
        workspace = _make_deal()
        db = _db_with_insert(workspace)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            with patch(
                "apps.api.app.routers.workspaces.check_workspace_limit", new_callable=AsyncMock
            ):
                r = await client.post("/api/v2/workspaces/", json={"name": "Acme Corp"})
            assert r.status_code == 201
        finally:
            app.dependency_overrides.clear()
