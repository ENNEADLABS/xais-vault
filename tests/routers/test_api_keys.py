"""
Tests for apps/api/app/routers/api_keys.py

All external dependencies are mocked:
  - Supabase DB via dependency override
  - Auth via dependency override (bypasses JWT)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from apps.api.app.dependencies import get_db, require_analyst
from apps.api.app.main import app
from apps.api.app.services.auth import AuthContext

# ─── Constants ─────────────────────────────────────────────────

ORG_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
KEY_ID = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()


# ─── Helpers ───────────────────────────────────────────────────


def _make_jwt_auth() -> AuthContext:
    return AuthContext(
        user_id=USER_ID,
        organization_id=ORG_ID,
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


def _make_key(**overrides) -> dict:
    base = {
        "id": KEY_ID,
        "organization_id": ORG_ID,
        "created_by": USER_ID,
        "name": "My Key",
        "key_hash": "abc123",
        "key_prefix": "xv_live_deadbeef",
        "scopes": ["*"],
        "rpm_limit": 60,
        "rpd_limit": 1000,
        "is_active": True,
        "last_used_at": None,
        "expires_at": None,
        "created_at": NOW,
    }
    return {**base, **overrides}


def _db_with_insert(row: dict) -> MagicMock:
    """Mock DB that returns row on insert."""
    db = MagicMock()
    chain = MagicMock()
    chain.insert.return_value = chain
    chain.execute.return_value = MagicMock(data=[row])
    db.table.return_value = chain
    return db


def _db_with_select(rows: list[dict], count: int | None = None) -> MagicMock:
    """Mock DB that returns rows on select."""
    db = MagicMock()
    chain = MagicMock()
    for m in ("select", "eq", "order", "range", "update", "delete"):
        getattr(chain, m).return_value = chain
    result = MagicMock(data=rows)
    result.count = count if count is not None else len(rows)
    chain.execute.return_value = result
    db.table.return_value = chain
    return db


def _db_empty() -> MagicMock:
    return _db_with_select([])


def override_jwt_auth():
    auth = _make_jwt_auth()

    async def _dep():
        return auth

    return _dep


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# ─── Create ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestCreateApiKey:
    async def test_returns_secret_once(self, client):
        """POST / returns key starting with xv_live_ and key_prefix."""
        row = _make_key()
        db = _db_with_insert(row)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            with patch(
                "apps.api.app.services.api_key_service.generate_api_key",
                return_value=(
                    "xv_live_abcdef1234567890abcdef1234567890",
                    "hash",
                    "xv_live_deadbeef",
                ),
            ):
                r = await client.post("/api/v2/api-keys/", json={"name": "My Key"})
            assert r.status_code == 201
            data = r.json()["data"]
            assert "key" in data
            assert data["key"].startswith("xv_live_")
            assert "key_hash" not in data
        finally:
            app.dependency_overrides.clear()

    async def test_no_secret_in_list(self, client):
        """GET / response has no 'key' field."""
        row = _make_key()
        db = _db_with_select([row], count=1)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.get("/api/v2/api-keys/")
            assert r.status_code == 200
            for item in r.json()["data"]:
                assert "key" not in item
                assert "key_hash" not in item
        finally:
            app.dependency_overrides.clear()

    async def test_custom_limits(self, client):
        """POST / with custom rpm/rpd limits."""
        row = _make_key(rpm_limit=100, rpd_limit=5000)
        db = _db_with_insert(row)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            with patch(
                "apps.api.app.services.api_key_service.generate_api_key",
                return_value=("xv_live_" + "a" * 32, "hash", "xv_live_aaaaaaaa"),
            ):
                r = await client.post(
                    "/api/v2/api-keys/",
                    json={"name": "Fast Key", "rpm_limit": 100, "rpd_limit": 5000},
                )
            assert r.status_code == 201
            data = r.json()["data"]
            assert data["rpm_limit"] == 100
            assert data["rpd_limit"] == 5000
        finally:
            app.dependency_overrides.clear()

    async def test_validation_empty_name(self, client):
        """POST / with empty name returns 422."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.post("/api/v2/api-keys/", json={"name": ""})
            assert r.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_validation_rpm_zero(self, client):
        """POST / with rpm_limit=0 returns 422."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.post(
                "/api/v2/api-keys/", json={"name": "X", "rpm_limit": 0}
            )
            assert r.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_validation_invalid_scope_rejected(self, client):
        """POST / with an unknown scope returns 422 (Pydantic validator)."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.post(
                "/api/v2/api-keys/",
                json={"name": "X", "scopes": ["admin:destroy-everything"]},
            )
            assert r.status_code == 422
            # Error detail must mention the invalid scope
            assert "admin:destroy-everything" in str(r.json())
        finally:
            app.dependency_overrides.clear()

    async def test_validation_valid_scopes_accepted(self):
        """ApiKeyCreate with valid scopes passes Pydantic validation (unit test)."""
        from apps.api.app.models.api_key import ApiKeyCreate

        body = ApiKeyCreate(name="X", scopes=["workspaces:read", "sources:read"])
        assert body.scopes == ["workspaces:read", "sources:read"]

        body = ApiKeyCreate(name="Y", scopes=["*"])
        assert body.scopes == ["*"]

        # Default
        body = ApiKeyCreate(name="Z")
        assert body.scopes == ["*"]

    async def test_validation_invalid_scope_raises(self):
        """ApiKeyCreate with invalid scope raises ValidationError (unit test)."""
        from pydantic import ValidationError

        from apps.api.app.models.api_key import ApiKeyCreate

        with pytest.raises(ValidationError) as exc_info:
            ApiKeyCreate(name="X", scopes=["admin:destroy-everything"])
        assert "admin:destroy-everything" in str(exc_info.value)


# ─── List ───────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestListApiKeys:
    async def test_empty_list(self, client):
        """GET / returns empty list."""
        db = _db_with_select([], count=0)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.get("/api/v2/api-keys/")
            assert r.status_code == 200
            assert r.json()["data"] == []
            assert r.json()["total"] == 0
        finally:
            app.dependency_overrides.clear()

    async def test_pagination(self, client):
        """GET /?page=1&per_page=5 applies pagination."""
        rows = [_make_key(id=str(uuid.uuid4())) for _ in range(5)]
        db = _db_with_select(rows, count=20)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.get("/api/v2/api-keys/?page=1&per_page=5")
            assert r.status_code == 200
            body = r.json()
            assert body["total"] == 20
            assert body["pages"] == 4
        finally:
            app.dependency_overrides.clear()


# ─── Get Detail ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestGetApiKey:
    async def test_returns_detail_with_usage(self, client):
        """GET /{key_id} returns key with usage fields."""
        row = _make_key()
        db = _db_with_select([row])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.get(f"/api/v2/api-keys/{KEY_ID}")
            assert r.status_code == 200
            data = r.json()["data"]
            assert data["id"] == KEY_ID
            assert "usage_today" in data
            assert "usage_this_month" in data
            assert "key" not in data
        finally:
            app.dependency_overrides.clear()

    async def test_not_found(self, client):
        """GET /{key_id} returns 404 for unknown key."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.get(f"/api/v2/api-keys/{uuid.uuid4()}")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ─── Update ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestUpdateApiKey:
    async def test_update_name(self, client):
        """PATCH /{key_id} updates name."""
        updated = _make_key(name="New Name")
        db = _db_with_select([updated])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.patch(
                f"/api/v2/api-keys/{KEY_ID}", json={"name": "New Name"}
            )
            assert r.status_code == 200
            assert r.json()["data"]["name"] == "New Name"
        finally:
            app.dependency_overrides.clear()

    async def test_deactivate(self, client):
        """PATCH /{key_id} with is_active=false deactivates key."""
        updated = _make_key(is_active=False)
        db = _db_with_select([updated])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.patch(
                f"/api/v2/api-keys/{KEY_ID}", json={"is_active": False}
            )
            assert r.status_code == 200
            assert r.json()["data"]["is_active"] is False
        finally:
            app.dependency_overrides.clear()

    async def test_empty_body(self, client):
        """PATCH with empty body returns 400."""
        db = _db_with_select([_make_key()])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.patch(f"/api/v2/api-keys/{KEY_ID}", json={})
            assert r.status_code == 400
        finally:
            app.dependency_overrides.clear()


# ─── Revoke ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRevokeApiKey:
    async def test_revoke(self, client):
        """DELETE /{key_id} returns 204."""
        db = _db_with_select([_make_key()])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.delete(f"/api/v2/api-keys/{KEY_ID}")
            assert r.status_code == 204
        finally:
            app.dependency_overrides.clear()

    async def test_revoke_not_found(self, client):
        """DELETE /{key_id} returns 404 for unknown key."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.delete(f"/api/v2/api-keys/{uuid.uuid4()}")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ─── Rotate ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRotateApiKey:
    async def _make_rotate_db(self, old_row: dict, new_row: dict) -> MagicMock:
        """DB mock for rotate: first select returns old_row, insert returns new_row."""
        db = MagicMock()
        call_n = [0]

        chain = MagicMock()
        for m in ("select", "eq", "update", "insert"):
            getattr(chain, m).return_value = chain

        def execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                return MagicMock(data=[old_row])
            return MagicMock(data=[new_row])

        chain.execute.side_effect = execute
        db.table.return_value = chain
        return db

    async def test_rotate_creates_new_key(self, client):
        """POST /{key_id}/rotate deactivates old, returns new key."""
        old = _make_key()
        new = _make_key(id=str(uuid.uuid4()), key_prefix="xv_live_newprefix")
        db = await self._make_rotate_db(old, new)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            with patch(
                "apps.api.app.services.api_key_service.generate_api_key",
                return_value=("xv_live_" + "b" * 32, "newhash", "xv_live_bbbbbbbb"),
            ):
                r = await client.post(f"/api/v2/api-keys/{KEY_ID}/rotate")
            assert r.status_code == 201
            data = r.json()["data"]
            assert "key" in data
            assert data["key"].startswith("xv_live_")
        finally:
            app.dependency_overrides.clear()

    async def test_rotate_inactive_fails(self, client):
        """POST rotate on inactive key returns 400."""
        old = _make_key(is_active=False)
        db = _db_with_select([old])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_jwt_auth()
        try:
            r = await client.post(f"/api/v2/api-keys/{KEY_ID}/rotate")
            assert r.status_code == 400
        finally:
            app.dependency_overrides.clear()


# ─── Auth Guards ────────────────────────────────────────────────


@pytest.mark.asyncio
class TestAuthGuards:
    async def test_api_key_auth_rejected(self, client):
        """Requests authenticated via API key cannot manage API keys."""
        auth = _make_api_key_auth()
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = lambda: auth
        try:
            r = await client.post("/api/v2/api-keys/", json={"name": "X"})
            assert r.status_code == 403
        finally:
            app.dependency_overrides.clear()

    async def test_api_key_auth_rejected_on_list(self, client):
        """API key auth rejected on list endpoint too."""
        auth = _make_api_key_auth()
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = lambda: auth
        try:
            r = await client.get("/api/v2/api-keys/")
            assert r.status_code == 403
        finally:
            app.dependency_overrides.clear()


# ─── Rate Limiting ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestPerKeyRateLimit:
    @pytest.fixture(autouse=True)
    def fresh_cache(self, monkeypatch):
        """Injecte un backend in-memory frais pour isoler les tests."""
        import packages.db.redis_client as cache_module
        from packages.db.redis_client import InMemoryCacheBackend

        backend = InMemoryCacheBackend()
        monkeypatch.setattr(cache_module, "_cache_backend", backend)
        return backend

    async def test_rpm_limit_enforced(self):
        """check_api_key_rate_limit returns False after rpm_limit+1 calls."""
        from apps.api.app.services.api_key_rate_limit import check_api_key_rate_limit

        key_id = str(uuid.uuid4())

        for _ in range(5):
            allowed, _ = await check_api_key_rate_limit(
                key_id, rpm_limit=5, rpd_limit=1000
            )
        assert allowed is True

        allowed, msg = await check_api_key_rate_limit(
            key_id, rpm_limit=5, rpd_limit=1000
        )
        assert allowed is False
        assert "RPM" in msg

    async def test_rpd_limit_enforced(self):
        """check_api_key_rate_limit returns False after rpd_limit+1 calls."""
        from apps.api.app.services.api_key_rate_limit import check_api_key_rate_limit

        key_id = str(uuid.uuid4())

        for _ in range(3):
            allowed, _ = await check_api_key_rate_limit(
                key_id, rpm_limit=1000, rpd_limit=3
            )
        assert allowed is True

        allowed, msg = await check_api_key_rate_limit(
            key_id, rpm_limit=1000, rpd_limit=3
        )
        assert allowed is False
        assert "RPD" in msg
