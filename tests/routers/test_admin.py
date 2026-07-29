"""
Tests pour apps/api/app/routers/admin.py

Auth et DB mockés via dependency override.
Service admin_stats mocké via patch.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.app.dependencies import get_db, require_admin
from apps.api.app.main import app
from apps.api.app.models.admin import (
    ActivityItem,
    ActivityLogResponse,
    ApiKeysUsageResponse,
    ApiKeyUsageItem,
    OrgOverviewResponse,
    UsageByMonth,
    UsageStatsResponse,
    UsageTotals,
)
from apps.api.app.services.auth import AuthContext

# ─── Constants ─────────────────────────────────────────────────

ORG_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())


# ─── Helpers ───────────────────────────────────────────────────


def _make_admin_auth() -> AuthContext:
    return AuthContext(
        user_id=USER_ID,
        organization_id=ORG_ID,
        role="admin",
        auth_method="jwt",
    )


def _make_analyst_auth() -> AuthContext:
    return AuthContext(
        user_id=USER_ID,
        organization_id=ORG_ID,
        role="analyst",
        auth_method="jwt",
    )


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def admin_client(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _make_admin_auth()
    yield
    app.dependency_overrides.clear()


# ─── GET /admin/usage ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_usage_stats_returns_data(admin_client):
    """Usage stats endpoint retourne des données correctement."""
    mock_response = UsageStatsResponse(
        months=[
            UsageByMonth(
                month="2026-03",
                operation="chat",
                count=42,
                input_tokens=10000,
                output_tokens=5000,
                cost_usd=0.05,
            )
        ],
        totals=UsageTotals(
            total_cost_usd=0.05,
            total_input_tokens=10000,
            total_output_tokens=5000,
            total_operations=42,
        ),
    )

    with patch(
        "apps.api.app.routers.admin.admin_stats.get_usage_stats",
        new=AsyncMock(return_value=mock_response),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v2/admin/usage",
                headers={"X-Organization-ID": ORG_ID},
            )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["months"]) == 1
    assert data["months"][0]["operation"] == "chat"
    assert data["totals"]["total_operations"] == 42


@pytest.mark.asyncio
async def test_get_usage_stats_months_param(admin_client):
    """Le paramètre months est transmis au service."""
    mock_response = UsageStatsResponse(
        months=[],
        totals=UsageTotals(
            total_cost_usd=0.0,
            total_input_tokens=0,
            total_output_tokens=0,
            total_operations=0,
        ),
    )

    with patch(
        "apps.api.app.routers.admin.admin_stats.get_usage_stats",
        new=AsyncMock(return_value=mock_response),
    ) as mock_svc:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            await ac.get(
                "/api/v2/admin/usage?months=3",
                headers={"X-Organization-ID": ORG_ID},
            )

    mock_svc.assert_called_once()
    call_kwargs = mock_svc.call_args.kwargs
    assert call_kwargs["months"] == 3


# ─── GET /admin/overview ───────────────────────────────────────


@pytest.mark.asyncio
async def test_get_org_overview_returns_data(admin_client):
    """Overview endpoint retourne les comptages org."""
    mock_response = OrgOverviewResponse(
        name="Acme Capital",
        plan="team",
        member_count=3,
        workspace_count=7,
        source_count=42,
        insight_count=15,
        trial_ends_at=None,
    )

    with patch(
        "apps.api.app.routers.admin.admin_stats.get_org_overview",
        new=AsyncMock(return_value=mock_response),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v2/admin/overview",
                headers={"X-Organization-ID": ORG_ID},
            )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["member_count"] == 3
    assert data["workspace_count"] == 7
    assert data["plan"] == "team"


# ─── GET /admin/api-keys/usage ─────────────────────────────────


@pytest.mark.asyncio
async def test_get_api_keys_usage_returns_keys(admin_client):
    """API keys usage endpoint retourne la liste des clés."""
    mock_response = ApiKeysUsageResponse(
        keys=[
            ApiKeyUsageItem(
                id=str(uuid.uuid4()),
                name="CI Key",
                key_prefix="xv_live_",
                is_active=True,
                rpm_limit=60,
                rpd_limit=1000,
                last_used_at="2026-03-19T10:00:00Z",
                created_at="2026-01-01T00:00:00Z",
            )
        ]
    )

    with patch(
        "apps.api.app.routers.admin.admin_stats.get_api_keys_usage",
        new=AsyncMock(return_value=mock_response),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v2/admin/api-keys/usage",
                headers={"X-Organization-ID": ORG_ID},
            )

    assert resp.status_code == 200
    keys = resp.json()["data"]["keys"]
    assert len(keys) == 1
    assert keys[0]["name"] == "CI Key"


# ─── GET /admin/activity ───────────────────────────────────────


@pytest.mark.asyncio
async def test_get_activity_log_returns_items(admin_client):
    """Activity log retourne les derniers jobs."""
    mock_response = ActivityLogResponse(
        items=[
            ActivityItem(
                id=str(uuid.uuid4()),
                type="scan_workspace",
                status="completed",
                created_at="2026-03-19T10:00:00Z",
                completed_at="2026-03-19T10:01:00Z",
                workspace_name="ProjectAlpha",
            )
        ]
    )

    with patch(
        "apps.api.app.routers.admin.admin_stats.get_activity_log",
        new=AsyncMock(return_value=mock_response),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v2/admin/activity",
                headers={"X-Organization-ID": ORG_ID},
            )

    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["type"] == "scan_workspace"


@pytest.mark.asyncio
async def test_get_activity_log_limit_param(admin_client):
    """Le paramètre limit est transmis au service."""
    mock_response = ActivityLogResponse(items=[])

    with patch(
        "apps.api.app.routers.admin.admin_stats.get_activity_log",
        new=AsyncMock(return_value=mock_response),
    ) as mock_svc:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            await ac.get(
                "/api/v2/admin/activity?limit=10",
                headers={"X-Organization-ID": ORG_ID},
            )

    mock_svc.assert_called_once()
    assert mock_svc.call_args.kwargs["limit"] == 10


# ─── Access control ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_non_admin_cannot_access_usage(mock_db):
    """Un non-admin ne peut pas accéder aux stats admin (403)."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = _require_admin_403

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get(
            "/api/v2/admin/usage",
            headers={"X-Organization-ID": ORG_ID},
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 403


def _require_admin_403():
    from fastapi import HTTPException

    raise HTTPException(status_code=403, detail="Admin role required")
