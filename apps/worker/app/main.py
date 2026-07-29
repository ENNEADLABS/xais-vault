"""
XAIS Vault Worker — Job processing loop.

Polls the `jobs` table every 2 seconds and executes pending jobs.
Runs as a separate Render background worker service.

Handles: index_source, scan_workspace, verify_insight, investigate,
         generate_deliverable, dispatch_webhook.
"""

from dotenv import load_dotenv

load_dotenv()

import asyncio
import logging
import os
import signal
import sys

from supabase import create_client

# Add project root (for packages/) and worker root (for app/) to path
_project_root = os.path.join(os.path.dirname(__file__), "..", "..", "..")
_worker_root = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.abspath(_project_root))
sys.path.insert(0, os.path.abspath(_worker_root))

from app.worker_loops import supervised_gc_loop, supervised_recovery_loop

from packages.core.config import load_config
from packages.db.job_queue import (
    claim_next_job,
    complete_job,
    fail_job,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("worker")

POLL_INTERVAL = 2  # secondes
SHUTDOWN = False


def handle_signal(signum, frame):
    """Graceful shutdown on SIGTERM/SIGINT."""
    global SHUTDOWN
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    SHUTDOWN = True


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


async def process_job(supabase, job: dict) -> dict:
    """Route a job to the appropriate handler.

    Each handler receives the job payload and returns a result dict.
    """
    job_type = job["type"]
    payload = job.get("payload", {})

    logger.info(f"Processing job {job['id']} type={job_type}")

    match job_type:
        case "index_source":
            from app.services.indexing import index_source

            return await index_source(supabase, payload)

        case "scan_workspace":
            from app.agents.scanner import run_scan

            return await run_scan(supabase, payload)

        case "verify_insight":
            from app.agents.verifier import run_verification

            return await run_verification(supabase, payload)

        case "investigate":
            from app.agents.researcher import run_investigation

            return await run_investigation(supabase, payload)

        case "generate_deliverable":
            from app.agents.writer import run_generation

            return await run_generation(supabase, payload)

        case "dispatch_webhook":
            from app.services.webhook_dispatcher import deliver_webhook

            return await deliver_webhook(supabase, **payload)

        case _:
            raise ValueError(f"Unknown job type: {job_type}")


async def run_loop():
    """Main polling loop — runs until SHUTDOWN signal."""
    config = load_config()
    supabase = create_client(config.supabase_url, config.supabase_service_role_key)
    logger.info("Worker started — polling for jobs...")

    # Stocker les références pour éviter la collecte par le GC
    _stop = lambda: SHUTDOWN  # noqa: E731
    _recovery_task = asyncio.create_task(supervised_recovery_loop(supabase, _stop))
    _gc_task = asyncio.create_task(supervised_gc_loop(supabase, _stop))

    while not SHUTDOWN:
        try:
            job = await claim_next_job(supabase)

            if job:
                try:
                    result = await process_job(supabase, job)
                    await complete_job(supabase, job["id"], result=result)
                except Exception as e:
                    logger.exception(f"Job {job['id']} failed: {e}")
                    await fail_job(
                        supabase,
                        job["id"],
                        error_message=str(e),
                        attempts=job.get("attempts", 1),
                        max_attempts=job.get("max_attempts", 3),
                    )
            else:
                await asyncio.sleep(POLL_INTERVAL)

        except Exception as e:
            logger.exception(f"Worker loop error: {e}")
            await asyncio.sleep(POLL_INTERVAL * 5)

    logger.info("Worker shut down cleanly.")


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(run_loop())
