"""
Tests pour apps/api/app/routers/super_admin.py

Auth et DB mockés via dependency override.
Service super_admin_stats mocké via patch.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.app.dependencies import get_db, require_authenticated, require_super_admin
from apps.api.app.main import app
from apps.api.app.models.super_admin import (
    ErrorItem,
    OrgMetrics,
    PlatformOverview,
    SummarizationStats,
    SuperAdminActivityItem,
    UserActivity,
)
from apps.api.app.services.auth import AuthContext

# ─── Constants ─────────────────────────────────────────────────

ADMIN_USER_ID = str(uuid.uuid4())
NORMAL_USER_ID = str(uuid.uuid4())
ORG_ID = str(uuid.uuid4())


# ─── Helpers ───────────────────────────────────────────────────


def _make_super_admin_auth() -> AuthContext:
    return AuthContext(
        user_id=ADMIN_USER_ID,
        auth_method="jwt",
    )


def _make_normal_auth() -> AuthContext:
    return AuthContext(
        user_id=NORMAL_USER_ID,
        auth_method="jwt",
    )


def _require_super_admin_403():
    from fastapi import HTTPException

    raise HTTPException(status_code=403, detail="Super-admin access required")


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def super_admin_client(mock_db):
    """Client avec auth super-admin."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_super_admin] = lambda: _make_super_admin_auth()
    app.dependency_overrides[require_authenticated] = lambda: _make_super_admin_auth()
    yield
    app.dependency_overrides.clear()


# ─── Fixtures de données ──────────────────────────────────────


def _make_overview() -> PlatformOverview:
    return PlatformOverview(
        total_organizations=5,
        total_workspaces=42,
        total_sources=150,
        total_insights=80,
        total_deliverables=12,
        total_chat_messages=320,
        active_orgs_7d=3,
        failed_jobs_24h=2,
        job_success_rate_7d=95.5,
    )


def _make_org_metrics() -> list[OrgMetrics]:
    return [
        OrgMetrics(
            org_id=str(uuid.uuid4()),
            org_name="Acme Capital",
            plan="team",
            member_count=3,
            workspace_count=7,
            source_count=42,
            insight_count=15,
            deliverable_count=4,
            chat_message_count=120,
            last_activity_at="2026-03-24T10:00:00Z",
            created_at="2026-01-01T00:00:00Z",
        )
    ]


def _make_user_activity() -> list[UserActivity]:
    return [
        UserActivity(
            user_id=str(uuid.uuid4()),
            email="analyst@acme.com",
            display_name="Alice",
            org_name="Acme Capital",
            workspaces_created=5,
            sources_uploaded=20,
            chat_messages_sent=45,
            deliverables_generated=2,
            last_active_at="2026-03-24T09:00:00Z",
        )
    ]


def _make_activity_items() -> list[SuperAdminActivityItem]:
    return [
        SuperAdminActivityItem(
            id=str(uuid.uuid4()),
            type="scan_workspace",
            status="completed",
            org_name="Acme Capital",
            workspace_name="ProjectAlpha",
            created_at="2026-03-24T10:00:00Z",
            completed_at="2026-03-24T10:01:00Z",
            error_message=None,
        )
    ]


def _make_error_items() -> list[ErrorItem]:
    return [
        ErrorItem(
            id=str(uuid.uuid4()),
            type="index_source",
            org_name="Acme Capital",
            workspace_name="ProjectBeta",
            error_message="PDF extraction failed: corrupted file",
            attempts=3,
            created_at="2026-03-24T08:00:00Z",
            failed_at="2026-03-24T08:01:00Z",
        )
    ]


# ─── GET /super-admin/check ──────────────────────────────────


@pytest.mark.asyncio
async def test_check_returns_true_for_super_admin(mock_db):
    """Un super-admin reçoit is_super_admin: true."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_authenticated] = lambda: _make_super_admin_auth()

    with patch("apps.api.app.routers.super_admin.load_config") as mock_config:
        mock_config.return_value.admin_user_ids = [ADMIN_USER_ID]
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/v2/super-admin/check")

    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["is_super_admin"] is True


@pytest.mark.asyncio
async def test_check_returns_false_for_normal_user(mock_db):
    """Un user normal reçoit is_super_admin: false (pas de 403)."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_authenticated] = lambda: _make_normal_auth()

    with patch("apps.api.app.routers.super_admin.load_config") as mock_config:
        mock_config.return_value.admin_user_ids = [ADMIN_USER_ID]
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/v2/super-admin/check")

    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["is_super_admin"] is False


def _make_summarization_stats() -> SummarizationStats:
    return SummarizationStats(
        total_count=42,
        count_24h=5,
        total_cost_usd=0.0523,
        cost_24h_usd=0.0062,
        avg_cost_usd=0.001245,
        avg_input_tokens=850,
        avg_output_tokens=320,
    )


# ─── GET /super-admin/summarization ─────────────────────────


@pytest.mark.asyncio
async def test_summarization_returns_stats(super_admin_client):
    """Summarization retourne les KPIs de coût."""
    with patch(
        "apps.api.app.routers.super_admin.super_admin_stats.get_summarization_stats",
        new=AsyncMock(return_value=_make_summarization_stats()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/v2/super-admin/summarization")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 42
    assert data["count_24h"] == 5
    assert data["avg_input_tokens"] == 850


@pytest.mark.asyncio
async def test_summarization_403_for_non_admin(mock_db):
    """Un non-admin reçoit 403 sur /summarization."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_super_admin] = _require_super_admin_403

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v2/super-admin/summarization")

    app.dependency_overrides.clear()
    assert resp.status_code == 403


# ─── GET /super-admin/overview ────────────────────────────────


@pytest.mark.asyncio
async def test_overview_returns_kpis(super_admin_client):
    """Overview retourne les KPIs globaux."""
    with patch(
        "apps.api.app.routers.super_admin.super_admin_stats.get_platform_overview",
        new=AsyncMock(return_value=_make_overview()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/v2/super-admin/overview")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_organizations"] == 5
    assert data["active_orgs_7d"] == 3
    assert data["job_success_rate_7d"] == 95.5


@pytest.mark.asyncio
async def test_overview_403_for_non_admin(mock_db):
    """Un non-admin reçoit 403 sur /overview."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_super_admin] = _require_super_admin_403

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v2/super-admin/overview")

    app.dependency_overrides.clear()
    assert resp.status_code == 403


# ─── GET /super-admin/organizations ───────────────────────────


@pytest.mark.asyncio
async def test_organizations_returns_list(super_admin_client):
    """Organizations retourne la liste avec métriques."""
    with patch(
        "apps.api.app.routers.super_admin.super_admin_stats.get_org_metrics",
        new=AsyncMock(return_value=_make_org_metrics()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/v2/super-admin/organizations")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["org_name"] == "Acme Capital"
    assert data[0]["workspace_count"] == 7


@pytest.mark.asyncio
async def test_organizations_403_for_non_admin(mock_db):
    """Un non-admin reçoit 403 sur /organizations."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_super_admin] = _require_super_admin_403

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v2/super-admin/organizations")

    app.dependency_overrides.clear()
    assert resp.status_code == 403


# ─── GET /super-admin/users ──────────────────────────────────


@pytest.mark.asyncio
async def test_users_returns_activity(super_admin_client):
    """Users retourne l'activité par utilisateur."""
    with patch(
        "apps.api.app.routers.super_admin.super_admin_stats.get_user_activity",
        new=AsyncMock(return_value=_make_user_activity()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/v2/super-admin/users")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["email"] == "analyst@acme.com"
    assert data[0]["workspaces_created"] == 5


@pytest.mark.asyncio
async def test_users_with_org_filter(super_admin_client):
    """Le paramètre org_id est transmis au service."""
    with patch(
        "apps.api.app.routers.super_admin.super_admin_stats.get_user_activity",
        new=AsyncMock(return_value=[]),
    ) as mock_svc:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            await ac.get(f"/api/v2/super-admin/users?org_id={ORG_ID}")

    mock_svc.assert_called_once()
    assert mock_svc.call_args.kwargs["org_id"] == ORG_ID


@pytest.mark.asyncio
async def test_users_403_for_non_admin(mock_db):
    """Un non-admin reçoit 403 sur /users."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_super_admin] = _require_super_admin_403

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v2/super-admin/users")

    app.dependency_overrides.clear()
    assert resp.status_code == 403


# ─── GET /super-admin/activity ────────────────────────────────


@pytest.mark.asyncio
async def test_activity_returns_feed(super_admin_client):
    """Activity retourne le feed chronologique."""
    with patch(
        "apps.api.app.routers.super_admin.super_admin_stats.get_global_activity",
        new=AsyncMock(return_value=_make_activity_items()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/v2/super-admin/activity")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["type"] == "scan_workspace"
    assert data[0]["org_name"] == "Acme Capital"


@pytest.mark.asyncio
async def test_activity_limit_param(super_admin_client):
    """Le paramètre limit est transmis au service."""
    with patch(
        "apps.api.app.routers.super_admin.super_admin_stats.get_global_activity",
        new=AsyncMock(return_value=[]),
    ) as mock_svc:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            await ac.get("/api/v2/super-admin/activity?limit=25")

    mock_svc.assert_called_once()
    assert mock_svc.call_args.kwargs["limit"] == 25


@pytest.mark.asyncio
async def test_activity_403_for_non_admin(mock_db):
    """Un non-admin reçoit 403 sur /activity."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_super_admin] = _require_super_admin_403

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v2/super-admin/activity")

    app.dependency_overrides.clear()
    assert resp.status_code == 403


# ─── GET /super-admin/errors ─────────────────────────────────


@pytest.mark.asyncio
async def test_errors_returns_failed_jobs(super_admin_client):
    """Errors retourne les jobs en erreur."""
    with patch(
        "apps.api.app.routers.super_admin.super_admin_stats.get_error_log",
        new=AsyncMock(return_value=_make_error_items()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/v2/super-admin/errors")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["type"] == "index_source"
    assert data[0]["attempts"] == 3
    assert "corrupted file" in data[0]["error_message"]


@pytest.mark.asyncio
async def test_errors_limit_param(super_admin_client):
    """Le paramètre limit est transmis au service."""
    with patch(
        "apps.api.app.routers.super_admin.super_admin_stats.get_error_log",
        new=AsyncMock(return_value=[]),
    ) as mock_svc:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            await ac.get("/api/v2/super-admin/errors?limit=10")

    mock_svc.assert_called_once()
    assert mock_svc.call_args.kwargs["limit"] == 10


@pytest.mark.asyncio
async def test_errors_403_for_non_admin(mock_db):
    """Un non-admin reçoit 403 sur /errors."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_super_admin] = _require_super_admin_403

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v2/super-admin/errors")

    app.dependency_overrides.clear()
    assert resp.status_code == 403
