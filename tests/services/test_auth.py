"""
Tests for apps/api/app/services/auth.py

Tests authentication logic in isolation — no HTTP clients.
All Supabase calls are mocked via MagicMock.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

import apps.api.app.services.auth as auth_module
from apps.api.app.services.auth import (
    AuthContext,
    _authenticate_api_key,
    _authenticate_jwt,
    authenticate,
    require_role,
    require_scope,
    resolve_organization,
)

# ─── Constants ─────────────────────────────────────────────────

ORG_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
KEY_ID = str(uuid.uuid4())
VALID_KEY = "xv_live_" + "a" * 32  # valid format


# ─── Helpers ───────────────────────────────────────────────────


def _supabase_with_key(key_data: dict) -> MagicMock:
    """Supabase mock returning key_data on api_keys lookup."""
    supabase = MagicMock()
    chain = MagicMock()
    for m in ("select", "eq", "update"):
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(data=[key_data] if key_data else [])
    supabase.table.return_value = chain
    return supabase


def _make_key_data(**overrides) -> dict:
    base = {
        "id": KEY_ID,
        "organization_id": ORG_ID,
        "scopes": ["*"],
        "rpm_limit": 60,
        "rpd_limit": 1000,
        "is_active": True,
        "created_by": USER_ID,
    }
    return {**base, **overrides}


# ─── JWT Authentication ─────────────────────────────────────────


@pytest.mark.asyncio
class TestAuthenticateJWT:
    async def test_jwt_valid(self):
        """Valid token returns AuthContext with correct user_id."""
        user = MagicMock(id=USER_ID, email="test@example.com")
        supabase = MagicMock()
        supabase.auth.get_user.return_value = MagicMock(user=user)

        ctx = await _authenticate_jwt("valid-token", supabase)

        assert ctx.user_id == USER_ID
        assert ctx.email == "test@example.com"
        assert ctx.auth_method == "jwt"

    async def test_jwt_invalid(self):
        """Supabase exception → HTTPException 401."""
        supabase = MagicMock()
        supabase.auth.get_user.side_effect = Exception("Token expired")

        with pytest.raises(HTTPException) as exc:
            await _authenticate_jwt("bad-token", supabase)
        assert exc.value.status_code == 401

    async def test_jwt_no_user(self):
        """Response with user=None → HTTPException 401."""
        supabase = MagicMock()
        supabase.auth.get_user.return_value = MagicMock(user=None)

        with pytest.raises(HTTPException) as exc:
            await _authenticate_jwt("token", supabase)
        assert exc.value.status_code == 401

    async def test_no_auth_header(self):
        """Request without Authorization or X-API-Key → HTTPException 401."""
        request = MagicMock()
        request.headers = {}
        supabase = MagicMock()

        with pytest.raises(HTTPException) as exc:
            await authenticate(request, supabase)
        assert exc.value.status_code == 401

    async def test_malformed_bearer(self):
        """'Bearer ' header with empty token → HTTPException 401."""
        request = MagicMock()
        request.headers = {"Authorization": "Bearer "}
        supabase = MagicMock()
        supabase.auth.get_user.return_value = MagicMock(user=None)

        with pytest.raises(HTTPException) as exc:
            await authenticate(request, supabase)
        assert exc.value.status_code == 401


# ─── JWT Cache ──────────────────────────────────────────────────


@pytest.mark.asyncio
class TestJWTCache:
    def setup_method(self):
        """Vider le cache avant chaque test."""
        auth_module._jwt_cache.clear()

    async def test_cache_hit_skips_supabase(self):
        """Deuxième appel avec le même token ne contacte pas Supabase."""
        user = MagicMock(id=USER_ID, email="test@example.com")
        supabase = MagicMock()
        supabase.auth.get_user.return_value = MagicMock(user=user)

        await _authenticate_jwt("token-abc", supabase)
        await _authenticate_jwt("token-abc", supabase)

        # Supabase appelé une seule fois (le 2e passe par le cache)
        supabase.auth.get_user.assert_called_once()

    async def test_cache_miss_calls_supabase(self):
        """Tokens différents → Supabase appelé à chaque fois."""
        user = MagicMock(id=USER_ID, email="test@example.com")
        supabase = MagicMock()
        supabase.auth.get_user.return_value = MagicMock(user=user)

        await _authenticate_jwt("token-1", supabase)
        await _authenticate_jwt("token-2", supabase)

        assert supabase.auth.get_user.call_count == 2

    async def test_cache_expiry(self):
        """Token expiré dans le cache → Supabase rappelé."""
        user = MagicMock(id=USER_ID, email="test@example.com")
        supabase = MagicMock()
        supabase.auth.get_user.return_value = MagicMock(user=user)

        import hashlib

        await _authenticate_jwt("token-exp", supabase)

        # Forcer l'expiration en antidatant le cache
        cache_key = hashlib.sha256(b"token-exp").hexdigest()
        auth_module._jwt_cache[cache_key] = (
            auth_module._jwt_cache[cache_key][0],
            0.0,  # timestamp dans le passé
        )

        await _authenticate_jwt("token-exp", supabase)
        assert supabase.auth.get_user.call_count == 2

    async def test_cache_cleanup_on_overflow(self):
        """Au-delà de MAX_SIZE entrées, les entrées expirées sont supprimées."""
        user = MagicMock(id=USER_ID, email="test@example.com")
        supabase = MagicMock()
        supabase.auth.get_user.return_value = MagicMock(user=user)

        # Remplir le cache avec des entrées expirées
        now = 0.0  # passé lointain → toutes expirées
        for i in range(auth_module._JWT_CACHE_MAX_SIZE):
            auth_module._jwt_cache[f"stale-{i}"] = (
                AuthContext(user_id=str(i), auth_method="jwt"),
                now,
            )

        # Un nouvel appel déclenche le cleanup
        await _authenticate_jwt("fresh-token", supabase)

        # Toutes les entrées expirées ont été supprimées, seule fresh-token reste
        assert len(auth_module._jwt_cache) == 1


# ─── API Key Authentication ─────────────────────────────────────


@pytest.mark.asyncio
class TestAuthenticateApiKey:
    async def test_api_key_valid(self):
        """Valid active key → AuthContext with api_key auth_method."""
        key_data = _make_key_data()
        supabase = _supabase_with_key(key_data)

        with patch(
            "apps.api.app.services.api_key_rate_limit.check_api_key_rate_limit",
            return_value=(True, ""),
        ):
            ctx = await _authenticate_api_key(VALID_KEY, supabase)

        assert ctx.auth_method == "api_key"
        assert ctx.organization_id == ORG_ID
        assert ctx.api_key_id == KEY_ID

    async def test_api_key_invalid_format(self):
        """Key without xv_live_/xv_test_ prefix → HTTPException 401."""
        supabase = MagicMock()
        with pytest.raises(HTTPException) as exc:
            await _authenticate_api_key("bad_format_key", supabase)
        assert exc.value.status_code == 401

    async def test_api_key_not_found(self):
        """Key hash not in DB → HTTPException 401."""
        supabase = _supabase_with_key({})  # empty data
        chain = MagicMock()
        for m in ("select", "eq"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        supabase.table.return_value = chain

        with pytest.raises(HTTPException) as exc:
            await _authenticate_api_key(VALID_KEY, supabase)
        assert exc.value.status_code == 401

    async def test_api_key_inactive(self):
        """Inactive key → HTTPException 403."""
        key_data = _make_key_data(is_active=False)
        supabase = _supabase_with_key(key_data)

        with pytest.raises(HTTPException) as exc:
            await _authenticate_api_key(VALID_KEY, supabase)
        assert exc.value.status_code == 403

    async def test_api_key_rate_limited(self):
        """Rate limit exceeded → HTTPException 429."""
        key_data = _make_key_data()
        supabase = _supabase_with_key(key_data)

        with patch(
            "apps.api.app.services.api_key_rate_limit.check_api_key_rate_limit",
            return_value=(False, "RPM limit exceeded"),
        ):
            with pytest.raises(HTTPException) as exc:
                await _authenticate_api_key(VALID_KEY, supabase)
        assert exc.value.status_code == 429

    async def test_updates_last_used_at(self):
        """Valid key → update({'last_used_at': 'now()'}) is called on api_keys."""
        key_data = _make_key_data()
        supabase = _supabase_with_key(key_data)

        with patch(
            "apps.api.app.services.api_key_rate_limit.check_api_key_rate_limit",
            return_value=(True, ""),
        ):
            await _authenticate_api_key(VALID_KEY, supabase)

        chain = supabase.table.return_value
        chain.update.assert_called_once_with({"last_used_at": "now()"})


# ─── Resolve Organization ───────────────────────────────────────


@pytest.mark.asyncio
class TestResolveOrganization:
    async def test_already_resolved_via_api_key(self):
        """Auth already has org + role → returned as-is."""
        auth = AuthContext(
            user_id=USER_ID,
            organization_id=ORG_ID,
            role="analyst",
            auth_method="api_key",
        )
        result = await resolve_organization(auth, MagicMock())
        assert result.organization_id == ORG_ID
        assert result.role == "analyst"

    async def test_resolve_with_org_header(self):
        """JWT auth + org_id provided → verifies membership and sets role."""
        auth = AuthContext(user_id=USER_ID, auth_method="jwt")
        supabase = MagicMock()
        chain = MagicMock()
        for m in ("select", "eq"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[{"role": "analyst"}])
        supabase.table.return_value = chain

        result = await resolve_organization(auth, supabase, organization_id=ORG_ID)
        assert result.organization_id == ORG_ID
        assert result.role == "analyst"

    async def test_resolve_not_member(self):
        """Not a member of the org → HTTPException 403."""
        auth = AuthContext(user_id=USER_ID, auth_method="jwt")
        supabase = MagicMock()
        chain = MagicMock()
        for m in ("select", "eq"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        supabase.table.return_value = chain

        with pytest.raises(HTTPException) as exc:
            await resolve_organization(auth, supabase, organization_id=ORG_ID)
        assert exc.value.status_code == 403

    async def test_resolve_default_org(self):
        """No org header → uses default_organization_id from profile."""
        auth = AuthContext(user_id=USER_ID, auth_method="jwt")
        supabase = MagicMock()
        call_n = [0]
        chain = MagicMock()
        for m in ("select", "eq"):
            getattr(chain, m).return_value = chain

        def execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                return MagicMock(data=[{"default_organization_id": ORG_ID}])
            return MagicMock(data=[{"role": "viewer"}])

        chain.execute.side_effect = execute
        supabase.table.return_value = chain

        result = await resolve_organization(auth, supabase)
        assert result.organization_id == ORG_ID
        assert result.role == "viewer"

    async def test_no_org_at_all(self):
        """No org header, no default in profile → organization_id stays None."""
        auth = AuthContext(user_id=USER_ID, auth_method="jwt")
        supabase = MagicMock()
        chain = MagicMock()
        for m in ("select", "eq"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[{"default_organization_id": None}])
        supabase.table.return_value = chain

        result = await resolve_organization(auth, supabase)
        assert result.organization_id is None
        assert result.role is None


# ─── require_role ───────────────────────────────────────────────


class TestRequireRole:
    def test_role_allowed(self):
        """Analyst role is allowed when analyst is in allowed list."""
        auth = AuthContext(user_id=USER_ID, role="analyst", auth_method="jwt")
        require_role(auth, ["admin", "analyst"])  # Should not raise

    def test_role_denied(self):
        """Viewer role is denied when only admin is allowed."""
        auth = AuthContext(user_id=USER_ID, role="viewer", auth_method="jwt")
        with pytest.raises(HTTPException) as exc:
            require_role(auth, ["admin"])
        assert exc.value.status_code == 403

    def test_no_role(self):
        """role=None → HTTPException 403."""
        auth = AuthContext(user_id=USER_ID, role=None, auth_method="jwt")
        with pytest.raises(HTTPException) as exc:
            require_role(auth, ["admin"])
        assert exc.value.status_code == 403


# ─── require_scope ──────────────────────────────────────────────


class TestRequireScope:
    def test_jwt_always_passes(self):
        """JWT users always pass scope check."""
        auth = AuthContext(user_id=USER_ID, auth_method="jwt")
        require_scope(auth, "webhooks:write")  # Should not raise

    def test_wildcard_scope_passes(self):
        """API key with wildcard scope passes any check."""
        auth = AuthContext(user_id=USER_ID, auth_method="api_key", scopes=["*"])
        require_scope(auth, "webhooks:write")  # Should not raise

    def test_matching_scope_passes(self):
        """API key with exact matching scope passes the check."""
        auth = AuthContext(
            user_id=USER_ID, auth_method="api_key", scopes=["workspaces:read"]
        )
        require_scope(auth, "workspaces:read")  # Should not raise

    def test_missing_scope_raises(self):
        """API key missing required scope → HTTPException 403."""
        auth = AuthContext(
            user_id=USER_ID, auth_method="api_key", scopes=["workspaces:read"]
        )
        with pytest.raises(HTTPException) as exc:
            require_scope(auth, "webhooks:write")
        assert exc.value.status_code == 403
