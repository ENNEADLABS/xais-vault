"""
Job Queue — PostgreSQL-based with SELECT ... FOR UPDATE SKIP LOCKED.

The API creates jobs. The Worker polls and executes them.
No Redis/Celery needed — Postgres IS the queue.

Usage (API side):
    job = await create_job(supabase, type="scan_workspace", payload={...}, org_id="...")

Usage (Worker side):
    job = await claim_next_job(supabase)
    if job:
        await process(job)
        await complete_job(supabase, job["id"], result={...})
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Job types — add new types here
JOB_TYPES = [
    "index_source",
    "scan_workspace",
    "verify_insight",
    "investigate",
    "generate_deliverable",
    "dispatch_webhook",
]


async def create_job(
    supabase,
    *,
    type: str,
    payload: dict[str, Any],
    organization_id: str,
    priority: int = 0,
    max_attempts: int = 3,
) -> dict:
    """Create a new job in the queue. Called by the API."""
    if type not in JOB_TYPES:
        raise ValueError(f"Unknown job type: {type}. Valid types: {JOB_TYPES}")

    result = supabase.table("jobs").insert({
        "type": type,
        "payload": payload,
        "organization_id": organization_id,
        "priority": priority,
        "max_attempts": max_attempts,
        "status": "pending",
    }).execute()

    if not result.data:
        raise RuntimeError("Failed to create job")

    job = result.data[0]
    logger.info(f"Created job {job['id']} type={type} org={organization_id}")
    return job


async def claim_next_job(supabase, lock_duration_seconds: int = 300) -> dict | None:
    """Claim the next pending job using FOR UPDATE SKIP LOCKED.

    This is atomic — only one worker can claim a job at a time.
    The job is locked for `lock_duration_seconds` to prevent re-processing
    if the worker crashes.
    """
    lock_until = datetime.now(timezone.utc) + timedelta(seconds=lock_duration_seconds)

    # Use RPC for atomic claim (SELECT FOR UPDATE SKIP LOCKED isn't available via PostgREST)
    result = supabase.rpc("claim_next_job", {
        "lock_until_ts": lock_until.isoformat(),
    }).execute()

    if not result.data:
        return None

    job = result.data
    if isinstance(job, list):
        job = job[0] if job else None

    if job:
        logger.info(f"Claimed job {job['id']} type={job['type']}")

    return job


async def complete_job(
    supabase,
    job_id: str,
    *,
    result: dict[str, Any] | None = None,
) -> None:
    """Mark a job as completed."""
    supabase.table("jobs").update({
        "status": "completed",
        "result": result,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", job_id).execute()

    logger.info(f"Completed job {job_id}")


async def recover_stuck_jobs(supabase) -> int:
    """Reset jobs stuck in 'processing' for more than 10 minutes.

    Returns the number of recovered jobs.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)

    result = (
        supabase.table("jobs")
        .select("id, type, attempts, max_attempts")
        .eq("status", "processing")
        .lt("started_at", cutoff.isoformat())
        .execute()
    )

    if not result.data:
        return 0

    recovered = 0
    for job in result.data:
        attempts = job.get("attempts", 0) + 1
        max_attempts = job.get("max_attempts", 3)

        if attempts >= max_attempts:
            supabase.table("jobs").update({
                "status": "failed",
                "error_message": "Job stuck in processing — max retries exceeded",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "attempts": attempts,
            }).eq("id", job["id"]).execute()
            logger.error(
                "Job %s (type=%s) permanently failed after stuck recovery",
                job["id"], job["type"],
            )
        else:
            supabase.table("jobs").update({
                "status": "pending",
                "error_message": "Recovered — was stuck in processing for >10 min",
                "locked_until": None,
                "attempts": attempts,
            }).eq("id", job["id"]).execute()
            logger.warning(
                "Recovered stuck job %s (type=%s, attempt %d/%d)",
                job["id"], job["type"], attempts, max_attempts,
            )
            recovered += 1

    return recovered


async def fail_job(
    supabase,
    job_id: str,
    *,
    error_message: str,
    attempts: int,
    max_attempts: int = 3,
) -> None:
    """Mark a job as failed. If under max_attempts, it will be retried."""
    if attempts < max_attempts:
        # Retry with exponential backoff
        retry_delay = 2 ** attempts * 30  # 30s, 60s, 120s
        locked_until = datetime.now(timezone.utc) + timedelta(seconds=retry_delay)
        supabase.table("jobs").update({
            "status": "pending",  # Back to pending for retry
            "error_message": error_message,
            "locked_until": locked_until.isoformat(),
            "attempts": attempts,
        }).eq("id", job_id).execute()
        logger.warning(f"Job {job_id} failed (attempt {attempts}/{max_attempts}), retrying in {retry_delay}s")
    else:
        # Max retries exceeded — permanently failed
        supabase.table("jobs").update({
            "status": "failed",
            "error_message": error_message,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "attempts": attempts,
        }).eq("id", job_id).execute()
        logger.error(f"Job {job_id} permanently failed after {attempts} attempts: {error_message}")
