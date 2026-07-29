"""
Shared configuration — environment variables with validation.

Loaded once at startup. Cached as singleton.
Used by API server, Worker, and LLM factory.
"""

from dotenv import load_dotenv

load_dotenv()

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Config:
    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # LLM
    anthropic_api_key: str
    google_api_key: str

    # Tavily (web search for Agent Researcher)
    tavily_api_key: str

    # App
    frontend_url: str
    environment: str  # development, staging, production
    debug: bool

    # Admin
    admin_user_ids: list[str]

    # Optional
    supabase_jwt_secret: str | None = None
    sentry_dsn: str | None = None
    health_secret: str | None = None  # Protège /health/detailed en prod

    # Stripe (billing) — optionnel, désactivé si absent
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_starter: str | None = None
    stripe_price_premium: str | None = None
    stripe_price_team: str | None = None

    # Redis (cache + rate limiting) — optionnel, in-memory si absent
    redis_url: str | None = None


@lru_cache(maxsize=1)
def load_config() -> Config:
    """Load and validate configuration from environment variables.

    Cached — safe to call from multiple modules.
    """

    def require(key: str) -> str:
        value = os.environ.get(key)
        if not value:
            raise RuntimeError(f"Missing required environment variable: {key}")
        return value

    def optional(key: str, default: str = "") -> str:
        return os.environ.get(key, default)

    environment = optional("ENVIRONMENT", "development")

    return Config(
        supabase_url=require("SUPABASE_URL"),
        supabase_anon_key=require("SUPABASE_ANON_KEY"),
        supabase_service_role_key=require("SUPABASE_SERVICE_ROLE_KEY"),
        supabase_jwt_secret=optional("SUPABASE_JWT_SECRET") or None,
        anthropic_api_key=require("ANTHROPIC_API_KEY"),
        google_api_key=require("GOOGLE_API_KEY"),
        tavily_api_key=require("TAVILY_API_KEY"),
        frontend_url=optional("FRONTEND_URL", "http://localhost:3000"),
        environment=environment,
        debug=environment == "development",
        admin_user_ids=[
            uid.strip()
            for uid in optional("ADMIN_USER_IDS", "").split(",")
            if uid.strip()
        ],
        sentry_dsn=optional("SENTRY_DSN") or None,
        health_secret=optional("HEALTH_SECRET") or None,
        stripe_secret_key=optional("STRIPE_SECRET_KEY") or None,
        stripe_webhook_secret=optional("STRIPE_WEBHOOK_SECRET") or None,
        stripe_price_starter=optional("STRIPE_PRICE_STARTER") or None,
        stripe_price_premium=optional("STRIPE_PRICE_PREMIUM") or None,
        stripe_price_team=optional("STRIPE_PRICE_TEAM") or None,
        redis_url=optional("REDIS_URL") or None,
    )
