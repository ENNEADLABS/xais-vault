"""Router registration — centralise tous les include_router de l'API."""

from fastapi import FastAPI


def register_routers(app: FastAPI) -> None:
    """Enregistre tous les routers sous /api/v2."""
    from . import (
        chat,
        insights,
        organization_members,
        organizations,
        profile,
        sources,
        workspaces,
    )

    app.include_router(profile.router, prefix="/api/v2/profile", tags=["Profile"])
    app.include_router(
        organizations.router, prefix="/api/v2/organizations", tags=["Organizations"]
    )
    app.include_router(
        organization_members.router,
        prefix="/api/v2/organizations",
        tags=["Organization Members"],
    )
    app.include_router(workspaces.router, prefix="/api/v2/workspaces", tags=["Workspaces"])
    app.include_router(
        sources.router, prefix="/api/v2/workspaces/{workspace_id}/sources", tags=["Sources"]
    )
    app.include_router(
        chat.router, prefix="/api/v2/workspaces/{workspace_id}/chat", tags=["Chat"]
    )
    app.include_router(
        insights.router, prefix="/api/v2/workspaces/{workspace_id}/insights", tags=["Insights"]
    )

    from . import deliverables

    app.include_router(
        deliverables.router,
        prefix="/api/v2/workspaces/{workspace_id}/deliverables",
        tags=["Deliverables"],
    )

    from . import notes

    app.include_router(
        notes.router, prefix="/api/v2/workspaces/{workspace_id}/notes", tags=["Notes"]
    )

    from . import investigations

    app.include_router(
        investigations.router,
        prefix="/api/v2/workspaces/{workspace_id}/investigations",
        tags=["Investigations"],
    )

    from . import entities

    app.include_router(
        entities.router,
        prefix="/api/v2/workspaces/{workspace_id}/entities",
        tags=["Entities"],
    )

    from . import api_keys

    app.include_router(api_keys.router, prefix="/api/v2/api-keys", tags=["API Keys"])

    from . import webhooks

    app.include_router(webhooks.router, prefix="/api/v2/webhooks", tags=["Webhooks"])

    from . import billing

    app.include_router(billing.router, prefix="/api/v2/billing", tags=["Billing"])

    from . import admin

    app.include_router(admin.router, prefix="/api/v2/admin", tags=["Admin"])

    from . import super_admin

    app.include_router(
        super_admin.router, prefix="/api/v2/super-admin", tags=["Super Admin"]
    )
