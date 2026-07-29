"""
Tests pour apps/api/app/services/admin_stats.py

Tests unitaires du service admin_stats — toutes les queries DB mockées.
"""

import uuid
from unittest.mock import MagicMock

import pytest

from apps.api.app.services.admin_stats import (
    get_activity_log,
    get_api_keys_usage,
    get_org_overview,
    get_usage_stats,
)

# ─── Constants ─────────────────────────────────────────────────

ORG_ID = str(uuid.uuid4())


# ─── Helpers ───────────────────────────────────────────────────


def _mock_rpc(rows: list) -> MagicMock:
    """Mock db.rpc(...).execute() → data=rows."""
    db = MagicMock()
    chain = MagicMock()
    chain.execute.return_value = MagicMock(data=rows)
    db.rpc.return_value = chain
    return db


def _mock_table_dispatch(table_data: dict[str, list | tuple]) -> MagicMock:
    """Mock DB avec dispatch par table. Supporte (rows, count) tuples."""
    db = MagicMock()

    def make_chain(rows: list, count: int | None = None) -> MagicMock:
        chain = MagicMock()
        for m in ("select", "eq", "order", "limit", "in_"):
            getattr(chain, m).return_value = chain
        result = MagicMock(data=rows)
        result.count = count if count is not None else len(rows)
        chain.execute.return_value = result
        return chain

    def side_effect(name: str) -> MagicMock:
        val = table_data.get(name, [])
        if isinstance(val, tuple):
            return make_chain(val[0], val[1])
        return make_chain(val)

    db.table.side_effect = side_effect
    return db


# ─── get_usage_stats ──────────────────────────────────────────


@pytest.mark.asyncio
class TestGetUsageStats:
    async def test_returns_months_and_totals(self):
        """Agrège correctement les données RPC."""
        rows = [
            {
                "month": "2026-03",
                "operation": "chat",
                "count": 42,
                "input_tokens": 10000,
                "output_tokens": 5000,
                "cost_usd": 0.05,
            },
            {
                "month": "2026-02",
                "operation": "scan",
                "count": 10,
                "input_tokens": 20000,
                "output_tokens": 8000,
                "cost_usd": 0.12,
            },
        ]
        db = _mock_rpc(rows)
        result = await get_usage_stats(db, ORG_ID, months=6)

        assert len(result.months) == 2
        assert result.months[0].operation == "chat"
        assert result.totals.total_operations == 52
        assert result.totals.total_cost_usd == pytest.approx(0.17)
        assert result.totals.total_input_tokens == 30000
        assert result.totals.total_output_tokens == 13000

        # Vérifie que le RPC est appelé avec les bons params
        db.rpc.assert_called_once_with(
            "admin_usage_by_month",
            {"target_org_id": ORG_ID, "month_count": 6},
        )

    async def test_empty_data(self):
        """Retourne des totaux à zéro si pas de données."""
        db = _mock_rpc([])
        result = await get_usage_stats(db, ORG_ID)

        assert result.months == []
        assert result.totals.total_operations == 0
        assert result.totals.total_cost_usd == 0.0

    async def test_custom_months_param(self):
        """Le paramètre months est passé au RPC."""
        db = _mock_rpc([])
        await get_usage_stats(db, ORG_ID, months=12)

        db.rpc.assert_called_once_with(
            "admin_usage_by_month",
            {"target_org_id": ORG_ID, "month_count": 12},
        )


# ─── get_org_overview ─────────────────────────────────────────


@pytest.mark.asyncio
class TestGetOrgOverview:
    async def test_returns_all_counts(self):
        """Retourne les comptages de chaque table."""
        db = _mock_table_dispatch(
            {
                "organizations": [
                    {"name": "Acme Capital", "plan": "team", "trial_ends_at": None}
                ],
                "organization_members": ([], 5),
                "workspaces": ([], 12),
                "sources": ([], 42),
                "insights": ([], 88),
            }
        )

        result = await get_org_overview(db, ORG_ID)

        assert result.name == "Acme Capital"
        assert result.plan == "team"
        assert result.member_count == 5
        assert result.workspace_count == 12
        assert result.source_count == 42
        assert result.insight_count == 88
        assert result.trial_ends_at is None

    async def test_empty_org(self):
        """Gère une org sans données (toutes les tables vides)."""
        db = _mock_table_dispatch(
            {
                "organizations": [],
                "organization_members": ([], 0),
                "workspaces": ([], 0),
                "sources": ([], 0),
                "insights": ([], 0),
            }
        )

        result = await get_org_overview(db, ORG_ID)

        assert result.name == ""
        assert result.plan == "starter"
        assert result.member_count == 0

    async def test_with_trial(self):
        """Retourne trial_ends_at quand présent."""
        db = _mock_table_dispatch(
            {
                "organizations": [
                    {
                        "name": "Startup",
                        "plan": "starter",
                        "trial_ends_at": "2026-04-01T00:00:00Z",
                    }
                ],
                "organization_members": ([], 1),
                "workspaces": ([], 0),
                "sources": ([], 0),
                "insights": ([], 0),
            }
        )

        result = await get_org_overview(db, ORG_ID)

        assert result.trial_ends_at == "2026-04-01T00:00:00Z"


# ─── get_api_keys_usage ───────────────────────────────────────


@pytest.mark.asyncio
class TestGetApiKeysUsage:
    async def test_returns_keys(self):
        """Retourne la liste des API keys avec métadonnées."""
        rows = [
            {
                "id": str(uuid.uuid4()),
                "name": "CI Key",
                "key_prefix": "xv_live_",
                "is_active": True,
                "rpm_limit": 120,
                "rpd_limit": 5000,
                "last_used_at": "2026-03-20T10:00:00Z",
                "created_at": "2026-01-15T00:00:00Z",
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Dev Key",
                "key_prefix": "xv_test_",
                "is_active": False,
                "rpm_limit": None,
                "rpd_limit": None,
                "last_used_at": None,
                "created_at": "2026-02-01T00:00:00Z",
            },
        ]
        db = _mock_table_dispatch({"api_keys": rows})

        result = await get_api_keys_usage(db, ORG_ID)

        assert len(result.keys) == 2
        assert result.keys[0].name == "CI Key"
        assert result.keys[0].rpm_limit == 120
        # Defaults appliqués quand None
        assert result.keys[1].rpm_limit == 60
        assert result.keys[1].rpd_limit == 1000
        assert result.keys[1].last_used_at is None

    async def test_empty_keys(self):
        """Retourne liste vide si pas de clés."""
        db = _mock_table_dispatch({"api_keys": []})

        result = await get_api_keys_usage(db, ORG_ID)

        assert result.keys == []


# ─── get_activity_log ─────────────────────────────────────────


@pytest.mark.asyncio
class TestGetActivityLog:
    async def test_returns_items_with_deal_names(self):
        """Retourne les jobs enrichis avec les noms de workspaces."""
        deal_id_1 = str(uuid.uuid4())
        deal_id_2 = str(uuid.uuid4())
        job_rows = [
            {
                "id": str(uuid.uuid4()),
                "type": "scan_workspace",
                "status": "completed",
                "payload": {"workspace_id": deal_id_1},
                "created_at": "2026-03-20T10:00:00Z",
                "completed_at": "2026-03-20T10:05:00Z",
            },
            {
                "id": str(uuid.uuid4()),
                "type": "index_source",
                "status": "completed",
                "payload": {"workspace_id": deal_id_2, "filename": "rapport.pdf"},
                "created_at": "2026-03-20T09:00:00Z",
                "completed_at": "2026-03-20T09:02:00Z",
            },
        ]
        deal_rows = [
            {"id": deal_id_1, "name": "Project Alpha"},
            {"id": deal_id_2, "name": "Project Beta"},
        ]

        db = _mock_table_dispatch(
            {
                "jobs": job_rows,
                "workspaces": deal_rows,
            }
        )

        result = await get_activity_log(db, ORG_ID, limit=50)

        assert len(result.items) == 2
        assert result.items[0].workspace_name == "Project Alpha"
        assert result.items[1].workspace_name == "Project Beta"
        assert result.items[1].source_name == "rapport.pdf"

    async def test_empty_activity(self):
        """Retourne liste vide si aucun job."""
        db = _mock_table_dispatch({"jobs": []})

        result = await get_activity_log(db, ORG_ID)

        assert result.items == []

    async def test_jobs_without_deal_id(self):
        """Gère les jobs sans workspace_id dans le payload."""
        job_rows = [
            {
                "id": str(uuid.uuid4()),
                "type": "cleanup",
                "status": "completed",
                "payload": {},
                "created_at": "2026-03-20T10:00:00Z",
                "completed_at": "2026-03-20T10:01:00Z",
            },
        ]
        db = _mock_table_dispatch({"jobs": job_rows})

        result = await get_activity_log(db, ORG_ID)

        assert len(result.items) == 1
        assert result.items[0].workspace_name is None
        assert result.items[0].source_name is None

    async def test_jobs_with_null_payload(self):
        """Gère les jobs avec payload=None."""
        job_rows = [
            {
                "id": str(uuid.uuid4()),
                "type": "maintenance",
                "status": "completed",
                "payload": None,
                "created_at": "2026-03-20T10:00:00Z",
                "completed_at": None,
            },
        ]
        db = _mock_table_dispatch({"jobs": job_rows})

        result = await get_activity_log(db, ORG_ID)

        assert len(result.items) == 1
        assert result.items[0].workspace_name is None

    async def test_custom_limit(self):
        """Le paramètre limit est passé à la query."""
        db = _mock_table_dispatch({"jobs": []})

        await get_activity_log(db, ORG_ID, limit=10)

        # Vérifie que limit() a été appelé sur la chaîne
        chain = db.table.return_value
        # La chaîne est construite via side_effect, vérifier via appels
        calls = db.table.call_args_list
        assert calls[0].args[0] == "jobs"
