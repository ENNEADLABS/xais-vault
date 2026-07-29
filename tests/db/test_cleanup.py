"""
Tests unitaires pour packages/db/cleanup.py.

Vérifie que les fonctions de GC appellent les bonnes opérations Supabase
avec les bons filtres de date et retournent les bons compteurs.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from packages.db.cleanup import (
    cleanup_old_jobs,
    cleanup_old_traces,
    cleanup_old_webhook_deliveries,
)

# ─── Helpers ─────────────────────────────────────────────────────


def _make_supabase(deleted_rows: list | None = None) -> MagicMock:
    """Supabase mock retournant deleted_rows sur .execute()."""
    supabase = MagicMock()
    result = MagicMock()
    result.data = deleted_rows if deleted_rows is not None else []

    # Chaîne fluide : .table().delete().eq().lt().execute()
    table = MagicMock()
    delete_chain = MagicMock()
    delete_chain.eq.return_value = delete_chain
    delete_chain.lt.return_value = delete_chain
    delete_chain.in_.return_value = delete_chain
    delete_chain.execute.return_value = result
    table.delete.return_value = delete_chain
    supabase.table.return_value = table

    return supabase


# ─── cleanup_old_jobs ─────────────────────────────────────────────


class TestCleanupOldJobs:
    @pytest.mark.asyncio
    async def test_returns_zero_when_no_rows_deleted(self):
        supabase = _make_supabase(deleted_rows=[])
        result = await cleanup_old_jobs(supabase)
        assert result == {"completed_deleted": 0, "failed_deleted": 0}

    @pytest.mark.asyncio
    async def test_returns_correct_counts(self):
        supabase = MagicMock()
        completed_result = MagicMock()
        completed_result.data = [{"id": "1"}, {"id": "2"}]
        failed_result = MagicMock()
        failed_result.data = [{"id": "3"}]

        # Premier appel delete → completed, second → failed
        delete_chain = MagicMock()
        delete_chain.eq.return_value = delete_chain
        delete_chain.lt.return_value = delete_chain
        delete_chain.execute.side_effect = [completed_result, failed_result]
        table = MagicMock()
        table.delete.return_value = delete_chain
        supabase.table.return_value = table

        result = await cleanup_old_jobs(supabase)
        assert result == {"completed_deleted": 2, "failed_deleted": 1}

    @pytest.mark.asyncio
    async def test_filters_by_completed_status(self):
        supabase = _make_supabase(deleted_rows=[])
        await cleanup_old_jobs(supabase, completed_retention_days=7)

        # Vérifier que .eq("status", "completed") est appelé
        table = supabase.table.return_value
        delete_chain = table.delete.return_value
        eq_calls = [str(c) for c in delete_chain.eq.call_args_list]
        assert any("completed" in c for c in eq_calls)

    @pytest.mark.asyncio
    async def test_cutoff_date_respected(self):
        """La date coupure doit être dans le passé (< now - retention_days)."""
        supabase = _make_supabase(deleted_rows=[])
        now_before = datetime.now(timezone.utc)

        await cleanup_old_jobs(supabase, completed_retention_days=7)

        table = supabase.table.return_value
        delete_chain = table.delete.return_value
        lt_call = delete_chain.lt.call_args_list[0]
        cutoff_str = lt_call[0][1]  # second arg de .lt("completed_at", cutoff)

        cutoff_dt = datetime.fromisoformat(cutoff_str)
        assert cutoff_dt < now_before

    @pytest.mark.asyncio
    async def test_none_data_counts_as_zero(self):
        supabase = _make_supabase(deleted_rows=None)
        result = await cleanup_old_jobs(supabase)
        assert result["completed_deleted"] == 0
        assert result["failed_deleted"] == 0


# ─── cleanup_old_traces ───────────────────────────────────────────


class TestCleanupOldTraces:
    @pytest.mark.asyncio
    async def test_returns_zero_when_no_rows(self):
        supabase = _make_supabase(deleted_rows=[])
        result = await cleanup_old_traces(supabase)
        assert result == 0

    @pytest.mark.asyncio
    async def test_returns_count_of_deleted(self):
        supabase = _make_supabase(deleted_rows=[{"id": "t1"}, {"id": "t2"}])
        result = await cleanup_old_traces(supabase)
        assert result == 2

    @pytest.mark.asyncio
    async def test_uses_agent_traces_table(self):
        supabase = _make_supabase(deleted_rows=[])
        await cleanup_old_traces(supabase)
        supabase.table.assert_called_with("agent_traces")

    @pytest.mark.asyncio
    async def test_none_data_counts_as_zero(self):
        supabase = _make_supabase(deleted_rows=None)
        result = await cleanup_old_traces(supabase)
        assert result == 0


# ─── cleanup_old_webhook_deliveries ──────────────────────────────


class TestCleanupOldWebhookDeliveries:
    @pytest.mark.asyncio
    async def test_returns_zero_when_no_rows(self):
        supabase = _make_supabase(deleted_rows=[])
        result = await cleanup_old_webhook_deliveries(supabase)
        assert result == 0

    @pytest.mark.asyncio
    async def test_returns_count_of_deleted(self):
        supabase = _make_supabase(
            deleted_rows=[{"id": "w1"}, {"id": "w2"}, {"id": "w3"}]
        )
        result = await cleanup_old_webhook_deliveries(supabase)
        assert result == 3

    @pytest.mark.asyncio
    async def test_uses_webhook_deliveries_table(self):
        supabase = _make_supabase(deleted_rows=[])
        await cleanup_old_webhook_deliveries(supabase)
        supabase.table.assert_called_with("webhook_deliveries")

    @pytest.mark.asyncio
    async def test_filters_delivered_and_failed_status(self):
        supabase = _make_supabase(deleted_rows=[])
        await cleanup_old_webhook_deliveries(supabase)

        table = supabase.table.return_value
        delete_chain = table.delete.return_value
        in_call = delete_chain.in_.call_args
        # .in_("status", ["delivered", "failed"])
        assert in_call[0][0] == "status"
        assert set(in_call[0][1]) == {"delivered", "failed"}

    @pytest.mark.asyncio
    async def test_none_data_counts_as_zero(self):
        supabase = _make_supabase(deleted_rows=None)
        result = await cleanup_old_webhook_deliveries(supabase)
        assert result == 0
