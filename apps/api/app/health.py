"""
Health check endpoints — extracted from main.py.
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .config import load_config

logger = logging.getLogger(__name__)
config = load_config()

health_router = APIRouter()


@health_router.get("/health")
async def health_check():
    """Health check endpoint with dependency status."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "environment": config.environment,
    }


@health_router.get("/health/detailed")
async def health_check_detailed(request: Request):
    """Detailed health check — latence Supabase.

    Protégé par HEALTH_SECRET si défini en prod (header X-Health-Secret).
    """
    import time as _time

    from packages.db.client import get_supabase

    # Protection par token secret en production
    if config.health_secret and not config.debug:
        provided = request.headers.get("X-Health-Secret", "")
        if provided != config.health_secret:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    details: dict = {
        "status": "healthy",
        "version": "2.0.0",
        "environment": config.environment,
    }

    # Ping Supabase
    try:
        t0 = _time.monotonic()
        db = get_supabase()
        db.table("organizations").select("id").limit(1).execute()
        details["supabase_latency_ms"] = round((_time.monotonic() - t0) * 1000)
    except Exception as e:
        details["supabase_latency_ms"] = None
        details["supabase_error"] = "connection_failed"  # Pas de détail en prod
        details["status"] = "degraded"
        logger.warning("Supabase health check failed: %s", e)

    # Taille du cache JWT — sans PID (fingerprinting risk)
    from .services.auth import _jwt_cache

    details["jwt_cache_size"] = len(_jwt_cache)

    return details
