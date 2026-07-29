"""
Tests for the Profile router (apps/api/app/routers/profile.py).

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

from apps.api.app.dependencies import get_db
from apps.api.app.main import app
from apps.api.app.services.auth import AuthContext

# ─── Constants ─────────────────────────────────────────────

USER_ID = str(uuid.uuid4())
EMAIL = "test@example.com"
NOW = datetime.now(timezone.utc).isoformat()


def _make_auth(email: str = EMAIL) -> AuthContext:
    return AuthContext(user_id=USER_ID, email=email)


def _make_profile(**overrides) -> dict:
    base = {
        "id": USER_ID,
        "display_name": None,
        "avatar_url": None,
        "default_organization_id": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    return {**base, **overrides}


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


def _override_auth(email: str = EMAIL):
    auth = _make_auth(email)

    async def _dep():
        return auth

    return _dep


# ─── GET /profile ──────────────────────────────────────────


@pytest.mark.asyncio
class TestGetProfile:
    async def test_get_profile_existing(self, client):
        """GET /profile returns existing profile enriched with email."""
        profile = _make_profile(display_name="Alice")
        db = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.execute.return_value = MagicMock(data=[profile])
        db.table.return_value = chain

        from apps.api.app.dependencies import require_authenticated
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_authenticated] = _override_auth()
        try:
            r = await client.get("/api/v2/profile/")
            assert r.status_code == 200
            assert r.json()["data"]["display_name"] == "Alice"
            assert r.json()["data"]["email"] == EMAIL
        finally:
            app.dependency_overrides.clear()

    async def test_get_profile_auto_creates(self, client):
        """GET /profile auto-creates profile when missing."""
        profile = _make_profile()
        db = MagicMock()
        call_n = [0]

        def execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                return MagicMock(data=[])  # Profile does not exist
            return MagicMock(data=[profile])  # Insert result

        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.insert.return_value = chain
        chain.execute.side_effect = execute
        db.table.return_value = chain

        from apps.api.app.dependencies import require_authenticated
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_authenticated] = _override_auth()
        try:
            r = await client.get("/api/v2/profile/")
            assert r.status_code == 200
            assert r.json()["data"]["id"] == USER_ID
        finally:
            app.dependency_overrides.clear()

    async def test_get_profile_unauthenticated(self, client):
        """GET /profile without token returns 401."""
        r = await client.get("/api/v2/profile/")
        assert r.status_code == 401


# ─── PATCH /profile ────────────────────────────────────────


@pytest.mark.asyncio
class TestUpdateProfile:
    async def test_update_display_name(self, client):
        """PATCH /profile updates display_name."""
        updated = _make_profile(display_name="Bob")
        db = MagicMock()
        chain = MagicMock()
        chain.update.return_value = chain
        chain.eq.return_value = chain
        chain.execute.return_value = MagicMock(data=[updated])
        db.table.return_value = chain

        from apps.api.app.dependencies import require_authenticated
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_authenticated] = _override_auth()
        try:
            r = await client.patch("/api/v2/profile/", json={"display_name": "Bob"})
            assert r.status_code == 200
            assert r.json()["data"]["display_name"] == "Bob"
        finally:
            app.dependency_overrides.clear()

    async def test_update_empty_body_returns_400(self, client):
        """PATCH /profile with no fields returns 400."""
        db = MagicMock()
        from apps.api.app.dependencies import require_authenticated
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_authenticated] = _override_auth()
        try:
            r = await client.patch("/api/v2/profile/", json={})
            assert r.status_code == 400
        finally:
            app.dependency_overrides.clear()

    async def test_update_avatar_url(self, client):
        """PATCH /profile updates avatar_url."""
        updated = _make_profile(avatar_url="https://example.com/avatar.png")
        db = MagicMock()
        chain = MagicMock()
        chain.update.return_value = chain
        chain.eq.return_value = chain
        chain.execute.return_value = MagicMock(data=[updated])
        db.table.return_value = chain

        from apps.api.app.dependencies import require_authenticated
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_authenticated] = _override_auth()
        try:
            r = await client.patch(
                "/api/v2/profile/",
                json={"avatar_url": "https://example.com/avatar.png"},
            )
            assert r.status_code == 200
            assert r.json()["data"]["avatar_url"] == "https://example.com/avatar.png"
        finally:
            app.dependency_overrides.clear()
