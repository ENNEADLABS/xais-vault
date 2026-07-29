"""
Organizations router — CRUD only.
Member management is in organization_members.py.
Multi-tenant: each user belongs to 1+ organizations.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from packages.db.client import require_one, safe_get_list, safe_get_one

from ..dependencies import DB, AdminAuth, Auth, AuthOnly
from ..models.common import ApiResponse
from ..models.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)

router = APIRouter()


@router.post("/", status_code=201)
async def create_organization(body: OrganizationCreate, auth: AuthOnly, db: DB):
    """Create a new organization. The creator becomes admin."""
    existing = db.table("organizations").select("id").eq("slug", body.slug).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Organization slug already taken")

    trial_ends_at = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()

    result = (
        db.table("organizations")
        .insert(
            {
                "name": body.name,
                "slug": body.slug,
                "plan": "trial",
                "trial_ends_at": trial_ends_at,
            }
        )
        .execute()
    )
    org = require_one(result, "Organization")

    db.table("organization_members").insert(
        {
            "organization_id": org["id"],
            "user_id": auth.user_id,
            "role": "admin",
        }
    ).execute()

    # Set as default org if user has none
    profile = safe_get_one(
        db.table("profiles")
        .select("default_organization_id")
        .eq("id", auth.user_id)
        .execute()
    )
    if not profile or not profile.get("default_organization_id"):
        db.table("profiles").upsert(
            {
                "id": auth.user_id,
                "default_organization_id": org["id"],
            }
        ).execute()

    return ApiResponse(data=OrganizationResponse(**org, member_count=1))


@router.get("/")
async def list_organizations(auth: AuthOnly, db: DB):
    """List organizations the user belongs to. Default org first."""
    memberships = safe_get_list(
        db.table("organization_members")
        .select("organization_id, role")
        .eq("user_id", auth.user_id)
        .execute()
    )

    if not memberships:
        return ApiResponse(data=[])

    org_ids = [m["organization_id"] for m in memberships]
    orgs = safe_get_list(
        db.table("organizations")
        .select("*")
        .in_("id", org_ids)
        .order("created_at")
        .execute()
    )

    profile = safe_get_one(
        db.table("profiles")
        .select("default_organization_id")
        .eq("id", auth.user_id)
        .execute()
    )
    default_org_id = profile.get("default_organization_id") if profile else None
    if default_org_id:
        orgs.sort(key=lambda o: o["id"] != default_org_id)

    return ApiResponse(data=orgs)


@router.get("/{org_id}")
async def get_organization(org_id: str, auth: Auth, db: DB):
    """Get organization details."""
    if auth.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    org = require_one(
        db.table("organizations").select("*").eq("id", org_id).execute(),
        "Organization",
    )
    members = safe_get_list(
        db.table("organization_members")
        .select("id")
        .eq("organization_id", org_id)
        .execute()
    )
    return ApiResponse(data={**org, "member_count": len(members)})


@router.patch("/{org_id}")
async def update_organization(
    org_id: str, body: OrganizationUpdate, auth: AdminAuth, db: DB
):
    """Update organization. Admin only."""
    if auth.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = db.table("organizations").update(updates).eq("id", org_id).execute()
    org = require_one(result, "Organization")
    return ApiResponse(data=org)


@router.delete("/{org_id}", status_code=204)
async def delete_organization(org_id: str, auth: AdminAuth, db: DB):
    """Delete the organization and all its data. Admin only."""
    if auth.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    require_one(
        db.table("organizations").select("id").eq("id", org_id).execute(),
        "Organization",
    )

    # Clear default_organization_id for affected users before CASCADE delete
    db.table("profiles").update(
        {
            "default_organization_id": None,
        }
    ).eq("default_organization_id", org_id).execute()

    db.table("organizations").delete().eq("id", org_id).execute()
