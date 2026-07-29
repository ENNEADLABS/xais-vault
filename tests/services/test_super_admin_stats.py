"""
Tests pour apps/api/app/services/super_admin_stats.py

DB mockée — on vérifie la logique d'agrégation et de mapping.
"""

import uuid
from unittest.mock import MagicMock

import pytest

from apps.api.app.services.super_admin_stats import (
    get_error_log,
    get_global_activity,
    get_org_metrics,
    get_platform_overview,
    get_user_activity,
)

# ─── Helpers ───────────────────────────────────────────────────

ORG_ID = str(uuid.uuid4())
ORG_ID_2 = str(uuid.uuid4())
DEAL_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())


def _db_for_overview(
    orgs: int = 3,
    workspaces: int = 10,
    sources: int = 25,
    insights: int = 15,
    deliverables: int = 5,
    chat_msgs: int = 100,
    active_orgs_7d: int = 1,
    failed_24h: int = 1,
    success_rate: float = 96.0,
) -> MagicMock:
    """Mock DB pour get_platform_overview via RPC."""
    db = MagicMock()
    db.rpc.return_value.execute.return_value = MagicMock(
        data={
            "total_organizations": orgs,
            "total_workspaces": workspaces,
            "total_sources": sources,
            "total_insights": insights,
            "total_deliverables": deliverables,
            "total_chat_messages": chat_msgs,
            "active_orgs_7d": active_orgs_7d,
            "failed_jobs_24h": failed_24h,
            "job_success_rate_7d": success_rate,
        }
    )
    return db


def _db_for_rpc(rpc_data: list) -> MagicMock:
    """Mock DB pour un appel RPC simple."""
    db = MagicMock()
    db.rpc.return_value.execute.return_value = MagicMock(data=rpc_data)
    return db


def _db_for_activity(job_rows: list, org_rows: list, deal_rows: list) -> MagicMock:
    """Mock DB pour get_global_activity / get_error_log (3 tables)."""
    db = MagicMock()
    call_idx = {"n": 0}

    def table_side_effect(name: str):
        chain = MagicMock()
        for m in ("select", "eq", "gte", "in_", "order", "limit"):
            getattr(chain, m).return_value = chain

        idx = call_idx["n"]
        call_idx["n"] += 1

        if idx == 0:
            # jobs
            chain.execute.return_value = MagicMock(data=job_rows)
        elif idx == 1:
            # organizations
            chain.execute.return_value = MagicMock(data=org_rows)
        elif idx == 2:
            # workspaces
            chain.execute.return_value = MagicMock(data=deal_rows)
        else:
            chain.execute.return_value = MagicMock(data=[])

        return chain

    db.table.side_effect = table_side_effect
    return db


# ─── get_platform_overview ────────────────────────────────────


@pytest.mark.asyncio
async def test_platform_overview_counts():
    """Retourne les bons comptages globaux depuis le RPC."""
    db = _db_for_overview(orgs=5, workspaces=42, sources=150, insights=80, deliverables=12, chat_msgs=320)
    result = await get_platform_overview(db)

    assert result.total_organizations == 5
    assert result.total_workspaces == 42
    assert result.total_sources == 150
    assert result.total_insights == 80
    assert result.total_deliverables == 12
    assert result.total_chat_messages == 320
    db.rpc.assert_called_once_with("super_admin_platform_overview")


@pytest.mark.asyncio
async def test_platform_overview_active_orgs():
    """Retourne le nombre d'orgs actives depuis le RPC."""
    db = _db_for_overview(active_orgs_7d=2)
    result = await get_platform_overview(db)
    assert result.active_orgs_7d == 2


@pytest.mark.asyncio
async def test_platform_overview_success_rate():
    """Retourne le taux de succès depuis le RPC."""
    db = _db_for_overview(success_rate=95.0)
    result = await get_platform_overview(db)
    assert result.job_success_rate_7d == 95.0


@pytest.mark.asyncio
async def test_platform_overview_success_rate_zero_jobs():
    """Taux de succès 100% quand aucun job (calculé côté SQL)."""
    db = _db_for_overview(success_rate=100.0)
    result = await get_platform_overview(db)
    assert result.job_success_rate_7d == 100.0


@pytest.mark.asyncio
async def test_platform_overview_failed_count():
    """Retourne le bon nombre de jobs failed 24h."""
    db = _db_for_overview(failed_24h=7)
    result = await get_platform_overview(db)
    assert result.failed_jobs_24h == 7


# ─── get_org_metrics ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_org_metrics_maps_rpc():
    """Mappe correctement les résultats RPC."""
    rpc_data = [
        {
            "org_id": ORG_ID,
            "org_name": "Acme Capital",
            "plan": "team",
            "member_count": 3,
            "workspace_count": 7,
            "source_count": 42,
            "insight_count": 15,
            "deliverable_count": 4,
            "chat_message_count": 120,
            "last_activity_at": "2026-03-24T10:00:00Z",
            "created_at": "2026-01-01T00:00:00Z",
        }
    ]
    db = _db_for_rpc(rpc_data)
    result = await get_org_metrics(db)

    assert len(result) == 1
    assert result[0].org_name == "Acme Capital"
    assert result[0].workspace_count == 7
    assert result[0].member_count == 3


@pytest.mark.asyncio
async def test_org_metrics_empty():
    """Retourne une liste vide si aucune org."""
    db = _db_for_rpc([])
    result = await get_org_metrics(db)
    assert result == []


# ─── get_user_activity ────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_activity_maps_rpc():
    """Mappe correctement les résultats RPC."""
    rpc_data = [
        {
            "user_id": USER_ID,
            "email": "alice@acme.com",
            "display_name": "Alice",
            "org_name": "Acme Capital",
            "workspaces_created": 5,
            "sources_uploaded": 20,
            "chat_messages_sent": 45,
            "deliverables_generated": 2,
            "last_active_at": "2026-03-24T09:00:00Z",
        }
    ]
    db = _db_for_rpc(rpc_data)
    result = await get_user_activity(db)

    assert len(result) == 1
    assert result[0].email == "alice@acme.com"
    assert result[0].workspaces_created == 5


@pytest.mark.asyncio
async def test_user_activity_with_org_filter():
    """Passe target_org_id au RPC si fourni."""
    db = _db_for_rpc([])
    await get_user_activity(db, org_id=ORG_ID, limit=50)

    db.rpc.assert_called_once_with(
        "super_admin_user_activity",
        {"row_limit": 50, "target_org_id": ORG_ID},
    )


@pytest.mark.asyncio
async def test_user_activity_without_org_filter():
    """N'inclut pas target_org_id si non fourni."""
    db = _db_for_rpc([])
    await get_user_activity(db, limit=100)

    db.rpc.assert_called_once_with(
        "super_admin_user_activity",
        {"row_limit": 100},
    )


# ─── get_global_activity ─────────────────────────────────────


@pytest.mark.asyncio
async def test_global_activity_with_data():
    """Retourne le feed avec noms résolus."""
    job_rows = [
        {
            "id": str(uuid.uuid4()),
            "type": "scan_workspace",
            "status": "completed",
            "organization_id": ORG_ID,
            "payload": {"workspace_id": DEAL_ID},
            "created_at": "2026-03-24T10:00:00Z",
            "completed_at": "2026-03-24T10:01:00Z",
            "error_message": None,
        }
    ]
    org_rows = [{"id": ORG_ID, "name": "Acme Capital"}]
    deal_rows = [{"id": DEAL_ID, "name": "ProjectAlpha"}]

    db = _db_for_activity(job_rows, org_rows, deal_rows)
    result = await get_global_activity(db, limit=100)

    assert len(result) == 1
    assert result[0].org_name == "Acme Capital"
    assert result[0].workspace_name == "ProjectAlpha"
    assert result[0].status == "completed"


@pytest.mark.asyncio
async def test_global_activity_empty():
    """Retourne une liste vide si aucun job."""
    db = _db_for_activity([], [], [])
    result = await get_global_activity(db)
    assert result == []


# ─── get_error_log ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_error_log_returns_failed():
    """Retourne les jobs en erreur avec noms résolus."""
    job_rows = [
        {
            "id": str(uuid.uuid4()),
            "type": "index_source",
            "organization_id": ORG_ID,
            "payload": {"workspace_id": DEAL_ID},
            "error_message": "PDF corrupted",
            "attempts": 3,
            "created_at": "2026-03-24T08:00:00Z",
            "completed_at": "2026-03-24T08:01:00Z",
        }
    ]
    org_rows = [{"id": ORG_ID, "name": "Acme Capital"}]
    deal_rows = [{"id": DEAL_ID, "name": "ProjectBeta"}]

    db = _db_for_activity(job_rows, org_rows, deal_rows)
    result = await get_error_log(db, limit=50)

    assert len(result) == 1
    assert result[0].type == "index_source"
    assert result[0].attempts == 3
    assert result[0].org_name == "Acme Capital"
    assert result[0].error_message == "PDF corrupted"


@pytest.mark.asyncio
async def test_error_log_empty():
    """Retourne une liste vide si aucun failed."""
    db = _db_for_activity([], [], [])
    result = await get_error_log(db)
    assert result == []
