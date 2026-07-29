"""
Worker background loops — recovery and GC, extracted from main.py.

Each loop accepts a `should_stop` callable so callers can inject
the SHUTDOWN signal without creating a module-level circular dependency.
"""

import asyncio
import logging
from typing import Callable

from packages.db.cleanup import (
    cleanup_old_jobs,
    cleanup_old_traces,
    cleanup_old_webhook_deliveries,
)
from packages.db.job_queue import recover_stuck_jobs

logger = logging.getLogger("worker")

RECOVERY_INTERVAL = 60  # secondes
GC_INTERVAL = 3600  # secondes (1 heure)


async def recovery_loop(supabase, should_stop: Callable[[], bool]) -> None:
    """Periodic recovery of stuck jobs — runs every 60s."""
    while not should_stop():
        try:
            recovered = await recover_stuck_jobs(supabase)
            if recovered > 0:
                logger.info(f"Recovery sweep: {recovered} job(s) recovered")
        except Exception as e:
            logger.exception(f"Recovery sweep error: {e}")
        await asyncio.sleep(RECOVERY_INTERVAL)


async def supervised_recovery_loop(supabase, should_stop: Callable[[], bool]) -> None:
    """Run recovery_loop with automatic restart on crash."""
    while not should_stop():
        try:
            await recovery_loop(supabase, should_stop)
        except Exception:
            logger.exception("Recovery loop crashed, restarting in 10s...")
            await asyncio.sleep(10)


async def gc_loop(supabase, should_stop: Callable[[], bool]) -> None:
    """Nettoyage périodique des jobs/traces/webhooks terminés — toutes les heures."""
    while not should_stop():
        try:
            job_stats = await cleanup_old_jobs(supabase)
            traces = await cleanup_old_traces(supabase)
            webhooks = await cleanup_old_webhook_deliveries(supabase)
            total = (
                job_stats["completed_deleted"]
                + job_stats["failed_deleted"]
                + traces
                + webhooks
            )
            if total > 0:
                logger.info(
                    "GC sweep: jobs=%s, traces=%d, webhooks=%d",
                    job_stats,
                    traces,
                    webhooks,
                )
        except Exception as e:
            logger.exception(f"GC sweep error: {e}")
        await asyncio.sleep(GC_INTERVAL)


async def supervised_gc_loop(supabase, should_stop: Callable[[], bool]) -> None:
    """Run gc_loop with automatic restart on crash."""
    while not should_stop():
        try:
            await gc_loop(supabase, should_stop)
        except Exception:
            logger.exception("GC loop crashed, restarting in 10s...")
            await asyncio.sleep(10)
