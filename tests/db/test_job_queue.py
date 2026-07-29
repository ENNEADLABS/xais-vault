"""
Tests for the job queue (packages/db/job_queue.py).

Covers create_job, claim_next_job, complete_job, fail_job, and recover_stuck_jobs.
All Supabase calls are mocked.
"""

import uuid
from unittest.mock import MagicMock

import pytest

from packages.db.job_queue import (
    JOB_TYPES,
    claim_next_job,
    complete_job,
    create_job,
    fail_job,
    recover_stuck_jobs,
)

ORG_ID = str(uuid.uuid4())
JOB_ID = str(uuid.uuid4())


def _make_job(**overrides) -> dict:
    base = {
        "id": JOB_ID,
        "type": "scan_workspace",
        "payload": {"workspace_id": "d1"},
        "organization_id": ORG_ID,
        "status": "pending",
        "attempts": 0,
        "max_attempts": 3,
    }
    return {**base, **overrides}


# ─── create_job ───────────────────────────────────────────────


class TestCreateJob:
    @pytest.mark.asyncio
    async def test_creates_job_successfully(self):
        """create_job inserts and returns the job dict."""
        db = MagicMock()
        job = _make_job()
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[job])

        result = await create_job(
            db,
            type="scan_workspace",
            payload={"workspace_id": "d1"},
            organization_id=ORG_ID,
        )

        assert result["id"] == JOB_ID
        assert result["type"] == "scan_workspace"
        db.table.assert_called_with("jobs")

    @pytest.mark.asyncio
    async def test_rejects_unknown_job_type(self):
        """create_job raises ValueError for unknown types."""
        db = MagicMock()

        with pytest.raises(ValueError, match="Unknown job type"):
            await create_job(
                db,
                type="invalid_type",
                payload={},
                organization_id=ORG_ID,
            )

    @pytest.mark.asyncio
    async def test_raises_on_insert_failure(self):
        """create_job raises RuntimeError when insert returns no data."""
        db = MagicMock()
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])

        with pytest.raises(RuntimeError, match="Failed to create job"):
            await create_job(
                db,
                type="scan_workspace",
                payload={},
                organization_id=ORG_ID,
            )

    @pytest.mark.asyncio
    async def test_all_job_types_accepted(self):
        """All defined JOB_TYPES are accepted."""
        for jt in JOB_TYPES:
            db = MagicMock()
            job = _make_job(type=jt)
            db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[job])

            result = await create_job(
                db, type=jt, payload={}, organization_id=ORG_ID
            )
            assert result["type"] == jt


# ─── claim_next_job ───────────────────────────────────────────


class TestClaimNextJob:
    @pytest.mark.asyncio
    async def test_returns_job_when_available(self):
        """claim_next_job returns job dict when one is pending."""
        db = MagicMock()
        job = _make_job(status="processing")
        db.rpc.return_value.execute.return_value = MagicMock(data=[job])

        result = await claim_next_job(db)
        assert result["id"] == JOB_ID
        db.rpc.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_empty(self):
        """claim_next_job returns None when no jobs available."""
        db = MagicMock()
        db.rpc.return_value.execute.return_value = MagicMock(data=[])

        result = await claim_next_job(db)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_data_is_none(self):
        """claim_next_job returns None when RPC returns None data."""
        db = MagicMock()
        db.rpc.return_value.execute.return_value = MagicMock(data=None)

        result = await claim_next_job(db)
        assert result is None


# ─── complete_job ─────────────────────────────────────────────


class TestCompleteJob:
    @pytest.mark.asyncio
    async def test_marks_job_completed(self):
        """complete_job updates status to 'completed'."""
        db = MagicMock()
        db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        await complete_job(db, JOB_ID, result={"summary": "done"})

        db.table.assert_called_with("jobs")
        update_call = db.table.return_value.update.call_args[0][0]
        assert update_call["status"] == "completed"
        assert update_call["result"] == {"summary": "done"}
        assert "completed_at" in update_call


# ─── fail_job ─────────────────────────────────────────────────


class TestFailJob:
    @pytest.mark.asyncio
    async def test_retries_under_max_attempts(self):
        """fail_job sets status back to 'pending' when retries remain."""
        db = MagicMock()
        db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        await fail_job(db, JOB_ID, error_message="timeout", attempts=1, max_attempts=3)

        update_call = db.table.return_value.update.call_args[0][0]
        assert update_call["status"] == "pending"
        assert update_call["attempts"] == 1
        assert "locked_until" in update_call

    @pytest.mark.asyncio
    async def test_permanently_fails_at_max_attempts(self):
        """fail_job sets status to 'failed' at max_attempts."""
        db = MagicMock()
        db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        await fail_job(db, JOB_ID, error_message="crash", attempts=3, max_attempts=3)

        update_call = db.table.return_value.update.call_args[0][0]
        assert update_call["status"] == "failed"
        assert update_call["error_message"] == "crash"
        assert "completed_at" in update_call

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Retry delay increases exponentially: 60s, 120s, 240s..."""
        db = MagicMock()
        db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        await fail_job(db, JOB_ID, error_message="err", attempts=1, max_attempts=5)
        call1 = db.table.return_value.update.call_args[0][0]["locked_until"]

        db.reset_mock()
        db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        await fail_job(db, JOB_ID, error_message="err", attempts=2, max_attempts=5)
        call2 = db.table.return_value.update.call_args[0][0]["locked_until"]

        # attempt 2 should have a later locked_until than attempt 1
        assert call2 > call1


# ─── recover_stuck_jobs ───────────────────────────────────────


class TestRecoverStuckJobs:
    @pytest.mark.asyncio
    async def test_no_stuck_jobs(self):
        """Returns 0 when no stuck jobs found."""
        db = MagicMock()
        chain = MagicMock()
        for m in ("select", "eq", "lt"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        db.table.return_value = chain

        result = await recover_stuck_jobs(db)
        assert result == 0

    @pytest.mark.asyncio
    async def test_recovers_stuck_job_under_max(self):
        """Stuck job with attempts < max is reset to 'pending'."""
        stuck_job = _make_job(
            id="stuck-1", status="processing", attempts=1, max_attempts=3
        )

        db = MagicMock()
        select_chain = MagicMock()
        for m in ("select", "eq", "lt"):
            getattr(select_chain, m).return_value = select_chain
        select_chain.execute.return_value = MagicMock(data=[stuck_job])
        db.table.return_value = select_chain

        update_chain = MagicMock()
        update_chain.eq.return_value = update_chain
        update_chain.execute.return_value = MagicMock(data=[])
        db.table.return_value.update.return_value = update_chain

        result = await recover_stuck_jobs(db)
        assert result == 1

        update_call = db.table.return_value.update.call_args[0][0]
        assert update_call["status"] == "pending"
        assert update_call["attempts"] == 2

    @pytest.mark.asyncio
    async def test_fails_stuck_job_at_max_attempts(self):
        """Stuck job at max_attempts is marked 'failed'."""
        stuck_job = _make_job(
            id="stuck-2", status="processing", attempts=2, max_attempts=3
        )

        db = MagicMock()
        select_chain = MagicMock()
        for m in ("select", "eq", "lt"):
            getattr(select_chain, m).return_value = select_chain
        select_chain.execute.return_value = MagicMock(data=[stuck_job])
        db.table.return_value = select_chain

        update_chain = MagicMock()
        update_chain.eq.return_value = update_chain
        update_chain.execute.return_value = MagicMock(data=[])
        db.table.return_value.update.return_value = update_chain

        result = await recover_stuck_jobs(db)
        # Job was failed, not recovered
        assert result == 0

        update_call = db.table.return_value.update.call_args[0][0]
        assert update_call["status"] == "failed"
        assert "max retries exceeded" in update_call["error_message"]

    @pytest.mark.asyncio
    async def test_mixed_stuck_jobs(self):
        """Mix of recoverable and permanently-failed jobs."""
        jobs = [
            _make_job(id="ok-1", attempts=0, max_attempts=3),
            _make_job(id="ok-2", attempts=1, max_attempts=3),
            _make_job(id="dead", attempts=2, max_attempts=3),
        ]

        db = MagicMock()
        select_chain = MagicMock()
        for m in ("select", "eq", "lt"):
            getattr(select_chain, m).return_value = select_chain
        select_chain.execute.return_value = MagicMock(data=jobs)
        db.table.return_value = select_chain

        update_chain = MagicMock()
        update_chain.eq.return_value = update_chain
        update_chain.execute.return_value = MagicMock(data=[])
        db.table.return_value.update.return_value = update_chain

        result = await recover_stuck_jobs(db)
        # 2 recovered (ok-1, ok-2), 1 failed (dead)
        assert result == 2
