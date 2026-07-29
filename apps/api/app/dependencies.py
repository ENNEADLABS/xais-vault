"""
FastAPI dependencies — injected into route handlers.

Usage in a router:
    @router.get("/")
    async def list_workspaces(auth: AuthContext = Depends(require_auth)):
        ...

    @router.post("/")
    async def create_workspace(auth: AuthContext = Depends(require_analyst)):
        ...
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request

from packages.core.config import load_config
from packages.db.client import get_supabase
from supabase import Client

from .services.auth import (
    AuthContext,
    authenticate,
    require_role,
    require_scope,
    resolve_organization,
)

# ─── Supabase client dependency ────────────────────────────


def get_db() -> Client:
    """Inject Supabase client into route handlers."""
    return get_supabase()


DB = Annotated[Client, Depends(get_db)]


# ─── Auth dependencies ─────────────────────────────────────


async def require_auth(request: Request, db: DB) -> AuthContext:
    """Authenticate the request. Returns AuthContext with user_id.

    Organization is resolved from:
    1. X-Organization-ID header (if provided)
    2. User's default_organization_id (from profile)
    """
    auth = await authenticate(request, db)

    # Resolve organization
    org_id = request.headers.get("X-Organization-ID")
    auth = await resolve_organization(auth, db, organization_id=org_id)

    if not auth.organization_id:
        raise HTTPException(
            status_code=400,
            detail="No organization context. Set X-Organization-ID header or configure a default organization.",
        )

    return auth


async def require_analyst(request: Request, db: DB) -> AuthContext:
    """Require at least analyst role (analyst or admin)."""
    auth = await require_auth(request, db)
    require_role(auth, ["admin", "analyst"])
    return auth


async def require_admin(request: Request, db: DB) -> AuthContext:
    """Require admin role."""
    auth = await require_auth(request, db)
    require_role(auth, ["admin"])
    return auth


async def require_viewer(request: Request, db: DB) -> AuthContext:
    """Require at least viewer role (any role)."""
    auth = await require_auth(request, db)
    require_role(auth, ["admin", "analyst", "viewer"])
    return auth


async def require_authenticated(request: Request, db: DB) -> AuthContext:
    """Authenticate the request WITHOUT requiring an organization context.

    Use for endpoints that work before the user has an org (create/list orgs).
    """
    return await authenticate(request, db)


async def require_super_admin(request: Request, db: DB) -> AuthContext:
    """Super-admin uniquement (ADMIN_USER_IDS). Pas de context org."""
    auth = await authenticate(request, db)
    config = load_config()
    if auth.user_id not in config.admin_user_ids:
        raise HTTPException(status_code=403, detail="Super-admin access required")
    return auth


# Type aliases for cleaner route signatures
Auth = Annotated[AuthContext, Depends(require_auth)]
AuthOnly = Annotated[AuthContext, Depends(require_authenticated)]
AnalystAuth = Annotated[AuthContext, Depends(require_analyst)]
AdminAuth = Annotated[AuthContext, Depends(require_admin)]
ViewerAuth = Annotated[AuthContext, Depends(require_viewer)]
SuperAdmin = Annotated[AuthContext, Depends(require_super_admin)]


# ─── Scope enforcement (API keys) ──────────────────────────


def require_scope_dep(scope: str):
    """Factory: returns a FastAPI dependency that enforces `scope` for API key auth.

    Depends on `require_auth` to resolve the AuthContext. JWT users bypass
    the check (require_scope returns early for them). API keys must carry
    the scope listed (or `*`) in their stored scopes.

    Usage in a route:
        @router.post("/", dependencies=[Depends(require_scope_dep("workspaces:write"))])

    Test note: tests that override the role-level auth dep (require_analyst
    / require_admin / require_viewer) must also override `require_auth` so
    the scope dep resolves against the stubbed AuthContext instead of hitting
    the real authenticate() flow.
    """

    async def _check(auth: AuthContext = Depends(require_auth)) -> None:
        require_scope(auth, scope)

    return _check
