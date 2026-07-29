"""
Organization resolution — extracted from auth.py.
"""

import sentry_sdk
from fastapi import HTTPException

from .auth_jwt import AuthContext


async def resolve_organization(
    auth: AuthContext,
    supabase_client,
    organization_id: str | None = None,
) -> AuthContext:
    """Resolve the user's organization and role.

    If organization_id is provided (from request), verify membership.
    Otherwise, use the user's default organization.
    """
    if auth.organization_id and auth.role:
        # Already resolved (API key path)
        return auth

    if organization_id:
        # Verify membership
        with sentry_sdk.start_span(op="auth.resolve_org", name="Verify org membership"):
            result = (
                supabase_client.table("organization_members")
                .select("role")
                .eq("user_id", auth.user_id)
                .eq("organization_id", organization_id)
                .execute()
            )

        if not result.data:
            raise HTTPException(
                status_code=403, detail="Not a member of this organization"
            )

        auth.organization_id = organization_id
        auth.role = result.data[0]["role"]
    else:
        # Use default organization from profile
        with sentry_sdk.start_span(
            op="auth.resolve_default_org", name="Fetch default org"
        ):
            result = (
                supabase_client.table("profiles")
                .select("default_organization_id")
                .eq("id", auth.user_id)
                .execute()
            )

        if result.data and result.data[0].get("default_organization_id"):
            default_org_id = result.data[0]["default_organization_id"]
            # Verify membership
            member_result = (
                supabase_client.table("organization_members")
                .select("role")
                .eq("user_id", auth.user_id)
                .eq("organization_id", default_org_id)
                .execute()
            )

            if member_result.data:
                auth.organization_id = default_org_id
                auth.role = member_result.data[0]["role"]

    return auth
