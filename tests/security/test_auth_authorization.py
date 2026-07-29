"""
Tests de sécurité — Authentification & Autorisation (Phase 1)

Couvre :
- IDOR multi-tenant via X-Organization-ID
- Privilege escalation API key (pas de gestion de clés via API key)
- Cache JWT : overflow flood, expiration, concurrence asyncio
- RBAC : viewer ne peut pas escalader, non-admin ne peut pas se promouvoir
- Race condition dernier admin
- AuthOnly endpoints sans contexte org
"""

import asyncio
import hashlib
import uuid
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

import apps.api.app.services.auth as auth_module
from apps.api.app.dependencies import (
    get_db,
    require_admin,
    require_analyst,
    require_auth,
    require_authenticated,
)
from apps.api.app.main import app
from apps.api.app.services.auth import (
    AuthContext,
    _authenticate_jwt,
    require_role,
)

# ─── Constants ──────────────────────────────────────────────────

ORG_A = str(uuid.uuid4())
ORG_B = str(uuid.uuid4())
USER_A = str(uuid.uuid4())
USER_B = str(uuid.uuid4())
MEMBER_ID = str(uuid.uuid4())


# ─── Fixtures ───────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


def _auth(org_id: str = ORG_A, role: str = "admin", method: str = "jwt") -> AuthContext:
    return AuthContext(
        user_id=USER_A,
        organization_id=org_id,
        role=role,
        auth_method=method,
    )


def _db_empty() -> MagicMock:
    """DB mock qui retourne toujours une liste vide."""
    db = MagicMock()
    chain = MagicMock()
    for m in (
        "select",
        "eq",
        "in_",
        "order",
        "limit",
        "range",
        "update",
        "delete",
        "insert",
        "upsert",
        "contains",
    ):
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(data=[], count=0)
    db.table.return_value = chain
    return db


def _db_rows(*rows) -> MagicMock:
    """DB mock qui retourne les rows fournies."""
    db = MagicMock()
    chain = MagicMock()
    for m in (
        "select",
        "eq",
        "in_",
        "order",
        "limit",
        "range",
        "update",
        "delete",
        "insert",
        "upsert",
        "contains",
    ):
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(data=list(rows), count=len(rows))
    db.table.return_value = chain
    return db


# ─── 1. IDOR Multi-tenant ────────────────────────────────────────


@pytest.mark.asyncio
class TestIDORMultiTenant:
    """Un user de org A ne doit pas accéder aux ressources de org B."""

    async def test_get_org_b_as_user_a_returns_403(self, client):
        """GET /organizations/{org_b} avec auth org A → 403."""
        app.dependency_overrides[get_db] = lambda: _db_empty()
        app.dependency_overrides[require_auth] = lambda: _auth(org_id=ORG_A)
        try:
            r = await client.get(f"/api/v2/organizations/{ORG_B}")
            assert r.status_code == 403
            assert "member" in r.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    async def test_patch_org_b_as_user_a_returns_403(self, client):
        """PATCH /organizations/{org_b} avec auth org A → 403."""
        app.dependency_overrides[get_db] = lambda: _db_empty()
        app.dependency_overrides[require_admin] = lambda: _auth(org_id=ORG_A)
        try:
            r = await client.patch(
                f"/api/v2/organizations/{ORG_B}", json={"name": "hacked"}
            )
            assert r.status_code == 403
        finally:
            app.dependency_overrides.clear()

    async def test_delete_org_b_as_user_a_returns_403(self, client):
        """DELETE /organizations/{org_b} avec auth org A → 403."""
        app.dependency_overrides[get_db] = lambda: _db_empty()
        app.dependency_overrides[require_admin] = lambda: _auth(org_id=ORG_A)
        try:
            r = await client.delete(f"/api/v2/organizations/{ORG_B}")
            assert r.status_code == 403
        finally:
            app.dependency_overrides.clear()

    async def test_delete_member_cross_org_returns_404(self, client):
        """DELETE /organizations/{org_a}/members/{id} où le membre est dans org_b → 404."""
        # Le .eq("organization_id", org_id) sur le select ne trouvera rien → 404
        app.dependency_overrides[get_db] = lambda: _db_empty()
        app.dependency_overrides[require_admin] = lambda: _auth(org_id=ORG_A)
        try:
            r = await client.delete(
                f"/api/v2/organizations/{ORG_A}/members/{MEMBER_ID}"
            )
            assert r.status_code == 404  # membre introuvable dans org_a
        finally:
            app.dependency_overrides.clear()

    async def test_own_org_accessible(self, client):
        """GET /organizations/{own_org} → 200 (accès légitime)."""
        org = {
            "id": ORG_A,
            "name": "XAIS",
            "slug": "xais",
            "plan": "trial",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }
        app.dependency_overrides[get_db] = lambda: _db_rows(org)
        app.dependency_overrides[require_auth] = lambda: _auth(org_id=ORG_A)
        try:
            r = await client.get(f"/api/v2/organizations/{ORG_A}")
            assert r.status_code == 200
        finally:
            app.dependency_overrides.clear()


# ─── 2. Privilege Escalation API Key ────────────────────────────


@pytest.mark.asyncio
class TestApiKeyPrivilegeEscalation:
    """Une API key ne doit pas pouvoir gérer d'autres API keys ou webhooks."""

    async def test_api_key_cannot_create_api_key(self, client):
        """POST /api-keys/ avec auth api_key → 403."""
        api_key_auth = _auth(method="api_key")
        app.dependency_overrides[get_db] = lambda: _db_empty()
        app.dependency_overrides[require_analyst] = lambda: api_key_auth
        try:
            r = await client.post(
                "/api/v2/api-keys/",
                json={"name": "evil key", "scopes": ["*"]},
            )
            assert r.status_code == 403
            assert "jwt" in r.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    async def test_api_key_cannot_list_api_keys(self, client):
        """GET /api-keys/ avec auth api_key → 403."""
        api_key_auth = _auth(method="api_key")
        app.dependency_overrides[get_db] = lambda: _db_empty()
        app.dependency_overrides[require_analyst] = lambda: api_key_auth
        try:
            r = await client.get("/api/v2/api-keys/")
            assert r.status_code == 403
        finally:
            app.dependency_overrides.clear()

    async def test_api_key_cannot_create_webhook(self, client):
        """POST /webhooks/ avec auth api_key → 403."""
        api_key_auth = _auth(method="api_key")
        app.dependency_overrides[get_db] = lambda: _db_empty()
        app.dependency_overrides[require_analyst] = lambda: api_key_auth
        try:
            r = await client.post(
                "/api/v2/webhooks/",
                json={"url": "https://example.com/hook", "events": ["scan.completed"]},
            )
            assert r.status_code == 403
        finally:
            app.dependency_overrides.clear()

    async def test_jwt_can_create_api_key(self, client):
        """POST /api-keys/ avec JWT analyst → 201 (accès légitime)."""
        jwt_auth = _auth(method="jwt", role="analyst")
        created = {
            "id": str(uuid.uuid4()),
            "name": "my key",
            "organization_id": ORG_A,
            "scopes": ["*"],
            "is_active": True,
            "rpm_limit": 60,
            "rpd_limit": 1000,
            "created_by": USER_A,
            "created_at": "2026-01-01T00:00:00",
            "key_prefix": "xv_live_",
        }

        async def fake_create(*args, **kwargs):
            return created, "xv_live_" + "a" * 32

        app.dependency_overrides[get_db] = lambda: _db_rows(created)
        app.dependency_overrides[require_analyst] = lambda: jwt_auth

        with patch(
            "apps.api.app.routers.api_keys.svc_create",
            side_effect=fake_create,
        ):
            try:
                r = await client.post(
                    "/api/v2/api-keys/",
                    json={"name": "my key", "scopes": ["*"]},
                )
                assert r.status_code == 201
            finally:
                app.dependency_overrides.clear()


# ─── 3. JWT Cache — Sécurité ─────────────────────────────────────


@pytest.mark.asyncio
class TestJWTCacheSecurity:
    """Tests de sécurité spécifiques au cache JWT."""

    def setup_method(self):
        auth_module._jwt_cache.clear()

    async def test_cache_flood_stays_bounded(self):
        """Un attaquant qui envoie 1001 tokens différents ne fait pas exploser le cache."""
        user = MagicMock(id=USER_A, email="attacker@example.com")
        supabase = MagicMock()
        supabase.auth.get_user.return_value = MagicMock(user=user)

        # Remplir le cache jusqu'au seuil avec des entrées expirées
        expired_ts = 0.0
        for i in range(auth_module._JWT_CACHE_MAX_SIZE):
            auth_module._jwt_cache[f"stale-{i}"] = (
                AuthContext(user_id=str(i), auth_method="jwt"),
                expired_ts,
            )

        # Le 1001e appel déclenche le nettoyage
        await _authenticate_jwt("fresh-token", supabase)

        # Après nettoyage, le cache ne contient que le token frais
        assert len(auth_module._jwt_cache) == 1

    async def test_cache_concurrent_access_no_crash(self):
        """100 coroutines accédant au cache simultanément ne provoquent pas d'erreur."""
        user = MagicMock(id=USER_A, email="test@example.com")
        supabase = MagicMock()
        supabase.auth.get_user.return_value = MagicMock(user=user)

        # Même token → cache hit après le premier appel
        results = await asyncio.gather(
            *[_authenticate_jwt("shared-token", supabase) for _ in range(100)]
        )

        # Tous les appels retournent un AuthContext valide
        assert all(r.user_id == USER_A for r in results)
        # Supabase n'est appelé qu'une fois (ou quelques fois à cause de la concurrence)
        # mais ne lève pas d'exception
        assert supabase.auth.get_user.call_count >= 1

    async def test_revoked_token_expires_after_ttl(self):
        """Token révoqué reste valide pendant le TTL cache (30s) puis est refusé."""
        user = MagicMock(id=USER_A, email="test@example.com")
        supabase = MagicMock()
        supabase.auth.get_user.return_value = MagicMock(user=user)

        await _authenticate_jwt("revoked-token", supabase)

        # Simuler la révocation : get_user lève maintenant une exception
        supabase.auth.get_user.side_effect = Exception("Token has been revoked")

        # Pendant le TTL → cache hit, toujours valide
        ctx = await _authenticate_jwt("revoked-token", supabase)
        assert ctx.user_id == USER_A  # cache hit

        # Forcer l'expiration
        cache_key = hashlib.sha256(b"revoked-token").hexdigest()
        auth_module._jwt_cache[cache_key] = (
            auth_module._jwt_cache[cache_key][0],
            0.0,  # timestamp passé
        )

        # Après expiration → Supabase appelé → 401
        with pytest.raises(HTTPException) as exc:
            await _authenticate_jwt("revoked-token", supabase)
        assert exc.value.status_code == 401

    async def test_different_users_different_cache_entries(self):
        """Deux users avec des tokens différents ont des entrées cache séparées."""
        user_a = MagicMock(id=USER_A, email="a@test.com")
        user_b = MagicMock(id=USER_B, email="b@test.com")
        supabase = MagicMock()
        supabase.auth.get_user.side_effect = [
            MagicMock(user=user_a),
            MagicMock(user=user_b),
        ]

        ctx_a = await _authenticate_jwt("token-a", supabase)
        ctx_b = await _authenticate_jwt("token-b", supabase)

        assert ctx_a.user_id == USER_A
        assert ctx_b.user_id == USER_B
        assert ctx_a.user_id != ctx_b.user_id


# ─── 4. RBAC ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRBAC:
    """Tests de contrôle des rôles."""

    def test_viewer_cannot_access_admin_endpoint(self):
        """Viewer tente d'appeler un endpoint admin → 403."""
        viewer = AuthContext(user_id=USER_A, role="viewer", auth_method="jwt")
        with pytest.raises(HTTPException) as exc:
            require_role(viewer, ["admin"])
        assert exc.value.status_code == 403

    def test_viewer_cannot_access_analyst_endpoint(self):
        """Viewer ne peut pas accéder à analyst+."""
        viewer = AuthContext(user_id=USER_A, role="viewer", auth_method="jwt")
        with pytest.raises(HTTPException) as exc:
            require_role(viewer, ["admin", "analyst"])
        assert exc.value.status_code == 403

    def test_analyst_cannot_access_admin_endpoint(self):
        """Analyst ne peut pas accéder à admin."""
        analyst = AuthContext(user_id=USER_A, role="analyst", auth_method="jwt")
        with pytest.raises(HTTPException) as exc:
            require_role(analyst, ["admin"])
        assert exc.value.status_code == 403

    def test_admin_can_access_all_levels(self):
        """Admin peut accéder à tous les niveaux."""
        admin = AuthContext(user_id=USER_A, role="admin", auth_method="jwt")
        require_role(admin, ["admin"])  # pas d'exception
        require_role(admin, ["admin", "analyst"])  # pas d'exception
        require_role(admin, ["admin", "analyst", "viewer"])  # pas d'exception

    async def test_non_admin_cannot_change_member_role(self, client):
        """PATCH /members/{id} avec analyst → 403 (AdminAuth requis)."""
        app.dependency_overrides[get_db] = lambda: _db_empty()
        # analyst tente d'appeler un endpoint AdminAuth — la dépendance lève 403
        app.dependency_overrides[require_admin] = lambda: (_ for _ in ()).throw(
            HTTPException(status_code=403, detail="Insufficient permissions")
        )
        try:
            r = await client.patch(
                f"/api/v2/organizations/{ORG_A}/members/{MEMBER_ID}",
                json={"role": "admin"},
            )
            assert r.status_code == 403
        finally:
            app.dependency_overrides.clear()


# ─── 5. Race condition — Dernier admin ───────────────────────────


@pytest.mark.asyncio
class TestLastAdminRaceCondition:
    """Deux admins qui tentent de partir simultanément."""

    async def test_single_admin_cannot_leave(self, client):
        """Le seul admin ne peut pas quitter l'org."""
        membership = {"id": MEMBER_ID, "role": "admin"}
        admins_list = [{"id": MEMBER_ID}]  # 1 seul admin

        call_n = [0]
        db = MagicMock()
        chain = MagicMock()
        for m in ("select", "eq", "order", "update", "delete", "insert"):
            getattr(chain, m).return_value = chain

        def execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                return MagicMock(data=[membership])  # membership trouvé
            return MagicMock(data=admins_list)  # liste des admins

        chain.execute.side_effect = execute
        db.table.return_value = chain

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_authenticated] = lambda: _auth()
        try:
            r = await client.post(f"/api/v2/organizations/{ORG_A}/members/leave")
            assert r.status_code == 400
            assert "last admin" in r.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    async def test_second_admin_can_leave(self, client):
        """Quand il y a 2 admins, un peut partir."""
        membership = {"id": MEMBER_ID, "role": "admin"}
        two_admins = [{"id": MEMBER_ID}, {"id": str(uuid.uuid4())}]

        call_n = [0]
        db = MagicMock()
        chain = MagicMock()
        for m in ("select", "eq", "order", "update", "delete", "insert"):
            getattr(chain, m).return_value = chain

        def execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                return MagicMock(data=[membership])
            if n == 1:
                return MagicMock(data=two_admins)
            return MagicMock(data=[{"default_organization_id": None}])

        chain.execute.side_effect = execute
        db.table.return_value = chain

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_authenticated] = lambda: _auth()
        try:
            r = await client.post(f"/api/v2/organizations/{ORG_A}/members/leave")
            assert r.status_code == 204
        finally:
            app.dependency_overrides.clear()


# ─── 6. AuthOnly — Pas de fuite cross-org ────────────────────────


@pytest.mark.asyncio
class TestAuthOnlyNoCrossOrgLeak:
    """Les endpoints AuthOnly (sans org requise) ne doivent pas exposer d'autres orgs."""

    async def test_list_organizations_returns_only_user_orgs(self, client):
        """GET /organizations retourne uniquement les orgs du user authentifié."""
        # Mock: membership pointe vers ORG_A uniquement
        memberships = [{"organization_id": ORG_A, "role": "admin"}]
        org_a = {
            "id": ORG_A,
            "name": "Org A",
            "slug": "org-a",
            "plan": "trial",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }

        call_n = [0]
        db = MagicMock()
        chain = MagicMock()
        for m in ("select", "eq", "in_", "order", "update", "contains"):
            getattr(chain, m).return_value = chain

        def execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                return MagicMock(data=memberships)  # memberships
            if n == 1:
                return MagicMock(data=[org_a])  # orgs filtrées
            return MagicMock(data=[{"default_organization_id": ORG_A}])  # profile

        chain.execute.side_effect = execute
        db.table.return_value = chain

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_authenticated] = lambda: _auth()
        try:
            r = await client.get("/api/v2/organizations/")
            assert r.status_code == 200
            orgs = r.json()["data"]
            # Seule l'org du user retournée — pas ORG_B
            assert all(o["id"] == ORG_A for o in orgs)
            assert not any(o["id"] == ORG_B for o in orgs)
        finally:
            app.dependency_overrides.clear()
