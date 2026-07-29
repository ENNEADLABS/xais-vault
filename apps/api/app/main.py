"""
XAIS Vault API — Entry point.

Middleware stack: GZip → CORS → Request ID → Error Handler
18 routers under /api/v2
"""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from .config import load_config
from .middleware.rate_limit import RateLimitMiddleware

logger = logging.getLogger(__name__)

config = load_config()

# ─── Sentry ────────────────────────────────────────────────

if config.sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.httpx import HttpxIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    def _traces_sampler(sampling_context: dict) -> float:
        """Exclut /health du tracing, 30% sampling en prod, 100% en dev."""
        name = sampling_context.get("transaction_context", {}).get("name", "")
        if name.endswith("/health"):
            return 0
        return 1.0 if config.debug else 0.3

    sentry_sdk.init(
        dsn=config.sentry_dsn,
        environment=config.environment,
        traces_sampler=_traces_sampler,
        profiles_sample_rate=0.1,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
            HttpxIntegration(),
            LoggingIntegration(level=logging.WARNING),
        ],
    )


# ─── Lifespan ──────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"Starting XAIS Vault API ({config.environment})")
    # Préchauffer le client Supabase pour éviter le cold start au premier appel
    from packages.db.client import get_supabase
    from packages.db.redis_client import get_cache

    get_supabase()
    get_cache()  # Log le backend utilisé (Redis ou in-memory)
    yield
    logger.info("Shutting down XAIS Vault API")


# ─── App ───────────────────────────────────────────────────

app = FastAPI(
    title="XAIS Vault API",
    description="AI-powered due diligence platform for PE/VC/M&A",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if config.debug else None,
    redoc_url="/redoc" if config.debug else None,
)


# ─── Middleware ─────────────────────────────────────────────

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Rate limiting — 60 req/min par user (in-memory, single-instance)
app.add_middleware(RateLimitMiddleware)

# CORS — wildcard en dev, origin stricte en prod
if config.environment == "production" and not config.frontend_url:
    raise RuntimeError("FRONTEND_URL is required in production for CORS")

cors_origins = ["*"] if config.debug else [config.frontend_url]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Organization-ID",
        "X-Request-ID",
    ],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers à chaque réponse."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"  # Désactiver le filtre XSS legacy
    if not config.debug:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Add a unique request ID to every request for tracing."""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ─── Error Handler ──────────────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all error handler. Returns consistent error format."""
    if hasattr(exc, "status_code") and exc.status_code is not None:
        status_code = exc.status_code
        message = exc.detail if hasattr(exc, "detail") else str(exc)
    else:
        status_code = 500
        message = "Internal server error"

    if status_code >= 500:
        logger.exception(
            "%s %s %s → %s",
            request.method,
            request.url.path,
            status_code,
            message,
        )

    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": status_code, "message": message}},
    )


# ─── Health + Routers ──────────────────────────────────────

from .health import health_router
from .routers import register_routers

app.include_router(health_router)
register_routers(app)
