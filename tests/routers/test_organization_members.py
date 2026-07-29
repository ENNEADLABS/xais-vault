"""
Tests for organization member endpoints (apps/api/app/routers/organization_members.py).

Covers: invite, leave, delete org, update role, remove member.
All dependencies mocked.
"""

import uuid
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from apps.api.app.dependencies import get_db
from apps.api.app.main import app
from apps.api.app.services.auth import AuthContext

# ─── Constants ─────────────────────────────────────────────

ORG_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
MEMBER_ID = str(uuid.uuid4())
OTHER_USER_ID = str(uuid.uuid4())
OTHER_MEMBER_ID = str(uuid.uuid4())


def _make_admin_auth() -> AuthContext:
    return AuthContext(user_id=USER_ID, organization_id=ORG_ID, role="admin")


def _make_viewer_auth() -> AuthContext:
    return AuthContext(user_id=USER_ID, organization_id=ORG_ID, role="viewer")


def _make_member(**overrides) -> dict:
    base = {
        "id": MEMBER_ID,
        "user_id": USER_ID,
        "organization_id": ORG_ID,
        "role": "analyst",
        "joined_at": "2026-01-01T00:00:00Z",
        "display_name": None,
    }
    return {**base, **overrides}


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


def _override_auth(auth: AuthContext):
    async def _dep():
        return auth

    return _dep


def _override_admin_as_forbidden():
    """Simulates the 403 that require_admin raises for non-admin users."""

    async def _dep():
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions. Required: admin",
        )

    return _dep


# ─── Invite member ─────────────────────────────────────────


@pytest.mark.asyncio
class TestInviteMember:
    async def test_invite_member_success(self, client):
        """POST /invite returns 201 for admin."""
        member = _make_member(user_id=OTHER_USER_ID)
        db = MagicMock()

        # Mock org exists
        db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": ORG_ID}]
        )

        # Mock supabase auth admin invite
        invited_user = MagicMock()
        invited_user.id = OTHER_USER_ID
        invited_response = MagicMock()
        invited_response.user = invited_user
        db.auth.admin.invite_user_by_email.return_value = invited_response

        # Mock not already a member, then insert
        call_n = [0]

        def execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                return MagicMock(data=[{"id": ORG_ID}])  # org exists
            if n == 1:
                return MagicMock(data=[])  # not yet member
            return MagicMock(data=[member])  # insert result

        chain = MagicMock()
        for m in ("select", "eq", "insert", "in_"):
            getattr(chain, m).return_value = chain
        chain.execute.side_effect = execute
        db.table.return_value = chain

        from apps.api.app.dependencies import require_admin

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_admin] = _override_auth(_make_admin_auth())
        try:
            r = await client.post(
                f"/api/v2/organizations/{ORG_ID}/members/invite",
                json={"email": "new@example.com", "role": "analyst"},
            )
            assert r.status_code == 201
        finally:
            app.dependency_overrides.clear()

    async def test_invite_already_member_returns_409(self, client):
        """POST /invite returns 409 if user is already a member."""
        db = MagicMock()
        call_n = [0]

        def execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                return MagicMock(data=[{"id": ORG_ID}])  # org exists
            return MagicMock(data=[{"id": MEMBER_ID}])  # already member

        chain = MagicMock()
        for m in ("select", "eq"):
            getattr(chain, m).return_value = chain
        chain.execute.side_effect = execute
        db.table.return_value = chain

        invited_user = MagicMock()
        invited_user.id = OTHER_USER_ID
        invited_response = MagicMock()
        invited_response.user = invited_user
        db.auth.admin.invite_user_by_email.return_value = invited_response

        from apps.api.app.dependencies import require_admin

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_admin] = _override_auth(_make_admin_auth())
        try:
            r = await client.post(
                f"/api/v2/organizations/{ORG_ID}/members/invite",
                json={"email": "existing@example.com", "role": "analyst"},
            )
            assert r.status_code == 409
        finally:
            app.dependency_overrides.clear()

    async def test_invite_non_admin_returns_403(self, client):
        """POST /invite by non-admin returns 403."""
        db = MagicMock()

        from apps.api.app.dependencies import require_admin

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_admin] = _override_admin_as_forbidden()
        try:
            r = await client.post(
                f"/api/v2/organizations/{ORG_ID}/members/invite",
                json={"email": "user@example.com", "role": "analyst"},
            )
            assert r.status_code == 403
        finally:
            app.dependency_overrides.clear()


# ─── Leave organization ────────────────────────────────────


@pytest.mark.asyncio
class TestLeaveOrganization:
    async def test_leave_organization_success(self, client):
        """POST /leave returns 204 for non-last-admin."""
        db = MagicMock()
        call_n = [0]

        def execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                return MagicMock(
                    data=[_make_member(role="analyst")]
                )  # membership found
            if n == 1:
                return MagicMock(data=[])  # delete OK
            return MagicMock(data=[{"default_organization_id": None}])  # profile

        chain = MagicMock()
        for m in ("select", "eq", "delete", "update"):
            getattr(chain, m).return_value = chain
        chain.execute.side_effect = execute
        db.table.return_value = chain

        from apps.api.app.dependencies import require_authenticated

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_authenticated] = _override_auth(
            AuthContext(user_id=USER_ID)
        )
        try:
            r = await client.post(f"/api/v2/organizations/{ORG_ID}/members/leave")
            assert r.status_code == 204
        finally:
            app.dependency_overrides.clear()

    async def test_leave_last_admin_returns_400(self, client):
        """POST /leave returns 400 when user is last admin."""
        db = MagicMock()
        call_n = [0]

        def execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                return MagicMock(data=[_make_member(role="admin")])  # admin membership
            return MagicMock(data=[{"id": MEMBER_ID}])  # only one admin

        chain = MagicMock()
        for m in ("select", "eq"):
            getattr(chain, m).return_value = chain
        chain.execute.side_effect = execute
        db.table.return_value = chain

        from apps.api.app.dependencies import require_authenticated

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_authenticated] = _override_auth(
            AuthContext(user_id=USER_ID)
        )
        try:
            r = await client.post(f"/api/v2/organizations/{ORG_ID}/members/leave")
            assert r.status_code == 400
            assert "last admin" in r.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()


# ─── Delete organization ───────────────────────────────────


@pytest.mark.asyncio
class TestDeleteOrganization:
    async def test_delete_organization_success(self, client):
        """DELETE /{org_id} returns 204 for admin."""
        db = MagicMock()
        call_n = [0]

        def execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                return MagicMock(data=[{"id": ORG_ID}])  # org exists
            return MagicMock(data=[])

        chain = MagicMock()
        for m in ("select", "eq", "delete", "update"):
            getattr(chain, m).return_value = chain
        chain.execute.side_effect = execute
        db.table.return_value = chain

        from apps.api.app.dependencies import require_admin

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_admin] = _override_auth(_make_admin_auth())
        try:
            r = await client.delete(f"/api/v2/organizations/{ORG_ID}")
            assert r.status_code == 204
        finally:
            app.dependency_overrides.clear()

    async def test_delete_organization_non_admin_returns_403(self, client):
        """DELETE /{org_id} by non-admin returns 403."""
        db = MagicMock()

        from apps.api.app.dependencies import require_admin

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_admin] = _override_admin_as_forbidden()
        try:
            r = await client.delete(f"/api/v2/organizations/{ORG_ID}")
            assert r.status_code == 403
        finally:
            app.dependency_overrides.clear()


# ─── List members ──────────────────────────────────────────


@pytest.mark.asyncio
class TestListMembers:
    async def test_list_members_returns_200(self, client):
        """GET /members retourne la liste des membres avec display_name."""
        member = _make_member()
        call_n = [0]

        db = MagicMock()
        chain = MagicMock()
        for m in ("select", "eq", "order", "in_"):
            getattr(chain, m).return_value = chain

        def execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                return MagicMock(data=[member])  # members list
            return MagicMock(
                data=[{"id": USER_ID, "display_name": "Alice"}]
            )  # profiles

        chain.execute.side_effect = execute
        db.table.return_value = chain

        from apps.api.app.dependencies import require_auth

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_auth] = _override_auth(_make_admin_auth())
        try:
            r = await client.get(f"/api/v2/organizations/{ORG_ID}/members")
            assert r.status_code == 200
            data = r.json()["data"]
            assert len(data) == 1
            assert data[0]["display_name"] == "Alice"
        finally:
            app.dependency_overrides.clear()

    async def test_list_members_empty_org(self, client):
        """GET /members sur org vide → liste vide."""
        db = MagicMock()
        chain = MagicMock()
        for m in ("select", "eq", "order", "in_"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        db.table.return_value = chain

        from apps.api.app.dependencies import require_auth

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_auth] = _override_auth(_make_admin_auth())
        try:
            r = await client.get(f"/api/v2/organizations/{ORG_ID}/members")
            assert r.status_code == 200
            assert r.json()["data"] == []
        finally:
            app.dependency_overrides.clear()


# ─── Update member role ────────────────────────────────────


@pytest.mark.asyncio
class TestUpdateMemberRole:
    async def test_update_role_success(self, client):
        """PATCH /{member_id} met à jour le rôle et retourne 200."""
        updated_member = _make_member(role="viewer")
        db = MagicMock()
        chain = MagicMock()
        for m in ("update", "eq"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[updated_member])
        db.table.return_value = chain

        from apps.api.app.dependencies import require_admin

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_admin] = _override_auth(_make_admin_auth())
        try:
            r = await client.patch(
                f"/api/v2/organizations/{ORG_ID}/members/{MEMBER_ID}",
                json={"role": "viewer"},
            )
            assert r.status_code == 200
            assert r.json()["data"]["role"] == "viewer"
        finally:
            app.dependency_overrides.clear()

    async def test_update_role_not_found_returns_404(self, client):
        """PATCH /{member_id} sur membre inexistant → 404."""
        db = MagicMock()
        chain = MagicMock()
        for m in ("update", "eq"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        db.table.return_value = chain

        from apps.api.app.dependencies import require_admin

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_admin] = _override_auth(_make_admin_auth())
        try:
            r = await client.patch(
                f"/api/v2/organizations/{ORG_ID}/members/{uuid.uuid4()}",
                json={"role": "analyst"},
            )
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_update_role_non_admin_returns_403(self, client):
        """PATCH /{member_id} par non-admin → 403."""
        db = MagicMock()

        from apps.api.app.dependencies import require_admin

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_admin] = _override_admin_as_forbidden()
        try:
            r = await client.patch(
                f"/api/v2/organizations/{ORG_ID}/members/{MEMBER_ID}",
                json={"role": "viewer"},
            )
            assert r.status_code == 403
        finally:
            app.dependency_overrides.clear()


# ─── Remove member ─────────────────────────────────────────


@pytest.mark.asyncio
class TestRemoveMember:
    async def test_remove_analyst_success(self, client):
        """DELETE /{member_id} sur analyst → 204."""
        db = MagicMock()
        call_n = [0]

        def execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                return MagicMock(data=[_make_member(role="analyst")])  # member found
            return MagicMock(data=[])  # delete OK

        chain = MagicMock()
        for m in ("select", "eq", "delete"):
            getattr(chain, m).return_value = chain
        chain.execute.side_effect = execute
        db.table.return_value = chain

        from apps.api.app.dependencies import require_admin

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_admin] = _override_auth(_make_admin_auth())
        try:
            r = await client.delete(
                f"/api/v2/organizations/{ORG_ID}/members/{MEMBER_ID}"
            )
            assert r.status_code == 204
        finally:
            app.dependency_overrides.clear()

    async def test_remove_last_admin_returns_400(self, client):
        """DELETE /{member_id} sur dernier admin → 400."""
        db = MagicMock()
        call_n = [0]

        def execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                return MagicMock(data=[_make_member(role="admin")])  # admin member
            return MagicMock(data=[{"id": MEMBER_ID}])  # only one admin

        chain = MagicMock()
        for m in ("select", "eq"):
            getattr(chain, m).return_value = chain
        chain.execute.side_effect = execute
        db.table.return_value = chain

        from apps.api.app.dependencies import require_admin

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_admin] = _override_auth(_make_admin_auth())
        try:
            r = await client.delete(
                f"/api/v2/organizations/{ORG_ID}/members/{MEMBER_ID}"
            )
            assert r.status_code == 400
            assert "last admin" in r.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    async def test_remove_member_not_found_returns_404(self, client):
        """DELETE /{member_id} inexistant → 404."""
        db = MagicMock()
        chain = MagicMock()
        for m in ("select", "eq"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        db.table.return_value = chain

        from apps.api.app.dependencies import require_admin

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_admin] = _override_auth(_make_admin_auth())
        try:
            r = await client.delete(
                f"/api/v2/organizations/{ORG_ID}/members/{uuid.uuid4()}"
            )
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ─── IDOR multi-tenant defense ─────────────────────────────
# Regression tests for OWASP A01: ensure the URL org_id matches auth.organization_id.


@pytest.mark.asyncio
class TestCrossTenantAccessBlocked:
    """Auth context belongs to ORG_ID (aaa), request targets OTHER_ORG (bbb) → 403."""

    async def _assert_cross_tenant_403(self, client, method, url, auth_dep, **kwargs):
        db = MagicMock()
        from apps.api.app.dependencies import require_admin, require_auth

        dep = {"admin": require_admin, "auth": require_auth}[auth_dep]
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[dep] = _override_auth(_make_admin_auth())
        try:
            r = await getattr(client, method)(url, **kwargs)
            assert r.status_code == 403
            assert "not a member" in r.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    async def test_list_members_blocks_cross_tenant(self, client):
        other_org = str(uuid.uuid4())
        await self._assert_cross_tenant_403(
            client, "get", f"/api/v2/organizations/{other_org}/members", "auth"
        )

    async def test_invite_member_blocks_cross_tenant(self, client):
        other_org = str(uuid.uuid4())
        await self._assert_cross_tenant_403(
            client,
            "post",
            f"/api/v2/organizations/{other_org}/members/invite",
            "admin",
            json={"email": "x@example.com", "role": "analyst"},
        )

    async def test_update_role_blocks_cross_tenant(self, client):
        other_org = str(uuid.uuid4())
        await self._assert_cross_tenant_403(
            client,
            "patch",
            f"/api/v2/organizations/{other_org}/members/{MEMBER_ID}",
            "admin",
            json={"role": "viewer"},
        )

    async def test_remove_member_blocks_cross_tenant(self, client):
        other_org = str(uuid.uuid4())
        await self._assert_cross_tenant_403(
            client,
            "delete",
            f"/api/v2/organizations/{other_org}/members/{MEMBER_ID}",
            "admin",
        )
