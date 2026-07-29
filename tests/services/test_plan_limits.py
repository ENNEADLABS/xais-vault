"""
Tests for plan limits enforcement (apps/api/app/services/plan_limits.py).

All DB calls are mocked — no external dependencies.
"""

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from apps.api.app.services.plan_limits import (
    PLAN_LIMITS,
    check_analysis_limit,
    check_workspace_limit,
    is_analysis_limit_reached,
)

ORG_ID = str(uuid.uuid4())


def _make_db(
    *, plan: str = "starter", org_exists: bool = True, count: int = 0
) -> MagicMock:
    """Build a Supabase mock for plan_limits tests."""
    db = MagicMock()
    call_n = [0]

    def _execute():
        n = call_n[0]
        call_n[0] += 1
        if n == 0:
            # First call = org lookup
            if not org_exists:
                return MagicMock(data=[])
            return MagicMock(data=[{"id": ORG_ID, "plan": plan}])
        # Second call = count query (workspaces or jobs)
        return MagicMock(data=[], count=count)

    chain = MagicMock()
    for m in ("select", "eq", "neq", "in_", "gte"):
        getattr(chain, m).return_value = chain
    chain.execute.side_effect = _execute
    db.table.return_value = chain
    return db


# ─── check_workspace_limit ─────────────────────────────────────────


class TestCheckDealLimit:
    @pytest.mark.asyncio
    async def test_under_limit_passes(self):
        """No exception when workspace count is below limit."""
        db = _make_db(plan="starter", count=3)
        await check_workspace_limit(db, ORG_ID)  # should not raise

    @pytest.mark.asyncio
    async def test_at_limit_raises_403(self):
        """HTTPException 403 when workspace count equals limit."""
        db = _make_db(plan="starter", count=5)
        with pytest.raises(HTTPException) as exc:
            await check_workspace_limit(db, ORG_ID)
        assert exc.value.status_code == 403
        assert "Workspace limit reached" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_over_limit_raises_403(self):
        """HTTPException 403 when workspace count exceeds limit."""
        db = _make_db(plan="starter", count=10)
        with pytest.raises(HTTPException) as exc:
            await check_workspace_limit(db, ORG_ID)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_enterprise_unlimited(self):
        """Enterprise plan has no workspace limit."""
        db = _make_db(plan="enterprise", count=999)
        await check_workspace_limit(db, ORG_ID)  # should not raise

    @pytest.mark.asyncio
    async def test_team_plan_limit(self):
        """Team plan allows up to 20 workspaces."""
        db = _make_db(plan="team", count=19)
        await check_workspace_limit(db, ORG_ID)  # under limit

        db2 = _make_db(plan="team", count=20)
        with pytest.raises(HTTPException) as exc:
            await check_workspace_limit(db2, ORG_ID)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_premium_plan_limit(self):
        """Premium plan allows up to 10 workspaces."""
        db = _make_db(plan="premium", count=9)
        await check_workspace_limit(db, ORG_ID)  # sous la limite

        db2 = _make_db(plan="premium", count=10)
        with pytest.raises(HTTPException) as exc:
            await check_workspace_limit(db2, ORG_ID)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_unknown_plan_defaults_to_starter(self):
        """Unknown plan falls back to starter limits."""
        db = _make_db(plan="nonexistent", count=5)
        with pytest.raises(HTTPException) as exc:
            await check_workspace_limit(db, ORG_ID)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_org_not_found_raises_404(self):
        """Missing organization raises 404."""
        db = _make_db(org_exists=False)
        with pytest.raises(HTTPException) as exc:
            await check_workspace_limit(db, ORG_ID)
        assert exc.value.status_code == 404


# ─── check_analysis_limit ─────────────────────────────────────


class TestCheckAnalysisLimit:
    @pytest.mark.asyncio
    async def test_under_limit_passes(self):
        """No exception when analysis count is below limit."""
        db = _make_db(plan="starter", count=10)
        await check_analysis_limit(db, ORG_ID)

    @pytest.mark.asyncio
    async def test_at_limit_raises_403(self):
        """HTTPException 403 when monthly analyses reach limit."""
        db = _make_db(plan="starter", count=50)
        with pytest.raises(HTTPException) as exc:
            await check_analysis_limit(db, ORG_ID)
        assert exc.value.status_code == 403
        assert "Monthly analysis limit" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_enterprise_unlimited(self):
        """Enterprise plan has no analysis limit."""
        db = _make_db(plan="enterprise", count=9999)
        await check_analysis_limit(db, ORG_ID)

    @pytest.mark.asyncio
    async def test_premium_plan_limit(self):
        """Premium plan allows up to 100 analyses per month."""
        db = _make_db(plan="premium", count=99)
        await check_analysis_limit(db, ORG_ID)  # sous la limite

        db2 = _make_db(plan="premium", count=100)
        with pytest.raises(HTTPException) as exc:
            await check_analysis_limit(db2, ORG_ID)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_trial_same_as_team(self):
        """Trial plan has same limits as team (PRD: 14-day full-featured trial)."""
        assert PLAN_LIMITS["trial"] == PLAN_LIMITS["team"]

        db = _make_db(plan="trial", count=200)
        with pytest.raises(HTTPException) as exc:
            await check_analysis_limit(db, ORG_ID)
        assert exc.value.status_code == 403


# ─── is_analysis_limit_reached ─────────────────────────────────


class TestIsAnalysisLimitReached:
    @pytest.mark.asyncio
    async def test_returns_false_when_under_limit(self):
        db = _make_db(plan="starter", count=10)
        assert await is_analysis_limit_reached(db, ORG_ID) is False

    @pytest.mark.asyncio
    async def test_returns_true_when_at_limit(self):
        db = _make_db(plan="starter", count=50)
        assert await is_analysis_limit_reached(db, ORG_ID) is True
