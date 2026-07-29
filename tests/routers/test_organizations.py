"""
Tests for apps/api/app/routers/organizations.py

Auth dependencies overridden — no JWT or Supabase in tests.
"""

import uuid
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from apps.api.app.dependencies import (
    get_db,
    require_admin,
    require_auth,
    require_authenticated,
)
from apps.api.app.main import app
from apps.api.app.services.auth import AuthContext

# ─── Constants ─────────────────────────────────────────────────

ORG_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
NOW = "2026-03-17T00:00:00+00:00"


# ─── Helpers ───────────────────────────────────────────────────


def _make_auth(role: str = "admin") -> AuthContext:
    return AuthContext(
        user_id=USER_ID,
        organization_id=ORG_ID,
        role=role,
        auth_method="jwt",
    )


def _make_auth_no_org() -> AuthContext:
    """AuthContext without organization (for create/list endpoints)."""
    return AuthContext(
        user_id=USER_ID,
        organization_id=None,
        role=None,
        auth_method="jwt",
    )


def _make_org(**overrides) -> dict:
    base = {
        "id": ORG_ID,
        "name": "XAIS Capital",
        "slug": "xais-capital",
        "plan": "trial",
        "created_at": NOW,
        "updated_at": NOW,
    }
    return {**base, **overrides}


def _db_chain(
    rows: list[dict] | None = None, insert_row: dict | None = None
) -> MagicMock:
    """Generic fluent chain mock. All methods return self, execute returns rows."""
    db = MagicMock()
    chain = MagicMock()
    for m in (
        "select",
        "insert",
        "update",
        "delete",
        "upsert",
        "eq",
        "in_",
        "order",
        "range",
    ):
        getattr(chain, m).return_value = chain
    data = [insert_row] if insert_row else (rows or [])
    chain.execute.return_value = MagicMock(data=data)
    db.table.return_value = chain
    db.rpc.return_value = chain
    return db


def _db_sequence(*row_lists) -> MagicMock:
    """DB mock where successive execute() calls return different row lists."""
    db = MagicMock()
    chain = MagicMock()
    for m in (
        "select",
        "insert",
        "update",
        "delete",
        "upsert",
        "eq",
        "in_",
        "order",
        "range",
    ):
        getattr(chain, m).return_value = chain

    call_n = [0]
    results = list(row_lists)

    def _execute():
        idx = min(call_n[0], len(results) - 1)
        call_n[0] += 1
        return MagicMock(data=results[idx])

    chain.execute.side_effect = _execute
    db.table.return_value = chain
    return db


@pytest_asyncio.fixture
async def client():
    unique_token = f"test-{uuid.uuid4()}"
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {unique_token}"},
    ) as c:
        yield c


# ─── Create ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestCreateOrganization:
    async def test_create_returns_201(self, client):
        """POST / creates org, makes user admin, returns 201."""
        org = _make_org()
        # Calls: slug check (empty), insert org (org), insert member, get profile (empty), upsert profile
        db = _db_sequence([], [org], [{"id": str(uuid.uuid4())}], [], [])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_authenticated] = lambda: _make_auth_no_org()
        try:
            r = await client.post(
                "/api/v2/organizations/",
                json={"name": "XAIS Capital", "slug": "xais-capital"},
            )
            assert r.status_code == 201
            data = r.json()["data"]
            assert data["id"] == ORG_ID
            assert data["member_count"] == 1
        finally:
            app.dependency_overrides.clear()

    async def test_create_slug_conflict_returns_409(self, client):
        """POST / with existing slug returns 409."""
        db = _db_chain(rows=[_make_org()])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_authenticated] = lambda: _make_auth_no_org()
        try:
            r = await client.post(
                "/api/v2/organizations/", json={"name": "Other", "slug": "xais-capital"}
            )
            assert r.status_code == 409
        finally:
            app.dependency_overrides.clear()

    async def test_create_missing_name_returns_422(self, client):
        """POST / without name returns 422."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_authenticated] = lambda: _make_auth_no_org()
        try:
            r = await client.post(
                "/api/v2/organizations/", json={"slug": "xais-capital"}
            )
            assert r.status_code == 422
        finally:
            app.dependency_overrides.clear()


# ─── List ───────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestListOrganizations:
    async def test_list_returns_orgs(self, client):
        """GET / returns organizations the user belongs to."""
        membership = {"organization_id": ORG_ID, "role": "admin"}
        org = _make_org()
        profile = {"default_organization_id": ORG_ID}
        db = _db_sequence([membership], [org], [profile])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_authenticated] = lambda: _make_auth_no_org()
        try:
            r = await client.get("/api/v2/organizations/")
            assert r.status_code == 200
            data = r.json()["data"]
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["id"] == ORG_ID
        finally:
            app.dependency_overrides.clear()

    async def test_list_no_memberships_returns_empty(self, client):
        """GET / returns empty list when user has no memberships."""
        db = _db_chain(rows=[])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_authenticated] = lambda: _make_auth_no_org()
        try:
            r = await client.get("/api/v2/organizations/")
            assert r.status_code == 200
            assert r.json()["data"] == []
        finally:
            app.dependency_overrides.clear()


# ─── Get Detail ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestGetOrganization:
    async def test_get_returns_org(self, client):
        """GET /{org_id} returns org with member_count."""
        org = _make_org()
        member = {"id": str(uuid.uuid4())}
        db = _db_sequence([org], [member])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_auth] = lambda: _make_auth()
        try:
            r = await client.get(f"/api/v2/organizations/{ORG_ID}")
            assert r.status_code == 200
            data = r.json()["data"]
            assert data["id"] == ORG_ID
            assert data["member_count"] == 1
        finally:
            app.dependency_overrides.clear()

    async def test_get_other_org_returns_403(self, client):
        """GET /{org_id} returns 403 when user is not a member (IDOR protection)."""
        db = _db_chain(rows=[])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_auth] = lambda: _make_auth()
        try:
            r = await client.get(f"/api/v2/organizations/{uuid.uuid4()}")
            assert r.status_code == 403
        finally:
            app.dependency_overrides.clear()


# ─── Update ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestUpdateOrganization:
    async def test_update_name(self, client):
        """PATCH /{org_id} updates org name."""
        updated = _make_org(name="XAIS Capital v2")
        db = _db_chain(rows=[updated])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_admin] = lambda: _make_auth()
        try:
            r = await client.patch(
                f"/api/v2/organizations/{ORG_ID}", json={"name": "XAIS Capital v2"}
            )
            assert r.status_code == 200
            assert r.json()["data"]["name"] == "XAIS Capital v2"
        finally:
            app.dependency_overrides.clear()

    async def test_update_empty_body_returns_400(self, client):
        """PATCH /{org_id} with no fields returns 400."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_admin] = lambda: _make_auth()
        try:
            r = await client.patch(f"/api/v2/organizations/{ORG_ID}", json={})
            assert r.status_code == 400
        finally:
            app.dependency_overrides.clear()

    async def test_update_chat_persona_general(self, client):
        """PATCH /{org_id} accepts chat_persona='general'."""
        updated = {**_make_org(), "chat_persona": "general"}
        db = _db_chain(rows=[updated])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_admin] = lambda: _make_auth()
        try:
            r = await client.patch(
                f"/api/v2/organizations/{ORG_ID}",
                json={"chat_persona": "general"},
            )
            assert r.status_code == 200
            assert r.json()["data"]["chat_persona"] == "general"
        finally:
            app.dependency_overrides.clear()

    async def test_update_chat_persona_dd(self, client):
        """PATCH /{org_id} accepts chat_persona='dd'."""
        updated = {**_make_org(), "chat_persona": "dd"}
        db = _db_chain(rows=[updated])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_admin] = lambda: _make_auth()
        try:
            r = await client.patch(
                f"/api/v2/organizations/{ORG_ID}",
                json={"chat_persona": "dd"},
            )
            assert r.status_code == 200
            assert r.json()["data"]["chat_persona"] == "dd"
        finally:
            app.dependency_overrides.clear()

    async def test_update_chat_persona_invalid_returns_422(self, client):
        """PATCH /{org_id} with unknown chat_persona returns 422."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_admin] = lambda: _make_auth()
        try:
            r = await client.patch(
                f"/api/v2/organizations/{ORG_ID}",
                json={"chat_persona": "lawyer"},
            )
            assert r.status_code == 422
        finally:
            app.dependency_overrides.clear()


# ─── Delete ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDeleteOrganization:
    async def test_delete_returns_204(self, client):
        """DELETE /{org_id} returns 204."""
        db = _db_sequence([_make_org()], [], [])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_admin] = lambda: _make_auth()
        try:
            r = await client.delete(f"/api/v2/organizations/{ORG_ID}")
            assert r.status_code == 204
        finally:
            app.dependency_overrides.clear()

    async def test_delete_other_org_returns_403(self, client):
        """DELETE /{org_id} returns 403 when user is not a member (IDOR protection)."""
        db = _db_chain(rows=[])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_admin] = lambda: _make_auth()
        try:
            r = await client.delete(f"/api/v2/organizations/{uuid.uuid4()}")
            assert r.status_code == 403
        finally:
            app.dependency_overrides.clear()
