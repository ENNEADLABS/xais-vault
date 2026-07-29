"""
Organization members router — list, invite, update role, remove, leave.
Mounted under /api/v2/organizations by main.py.
"""

import logging

from fastapi import APIRouter, HTTPException

from packages.db.client import require_one, safe_get_list, safe_get_one

from ..dependencies import DB, AdminAuth, Auth, AuthOnly
from ..models.common import ApiResponse
from ..models.organization import MemberInvite, MemberResponse, MemberRoleUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{org_id}/members")
async def list_members(org_id: str, auth: Auth, db: DB):
    """List organization members."""
    if auth.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    members = safe_get_list(
        db.table("organization_members")
        .select("id, user_id, role, joined_at")
        .eq("organization_id", org_id)
        .order("joined_at")
        .execute()
    )

    user_ids = [m["user_id"] for m in members]
    if user_ids:
        profiles = safe_get_list(
            db.table("profiles")
            .select("id, display_name")
            .in_("id", user_ids)
            .execute()
        )
        profile_map = {p["id"]: p for p in profiles}
        for m in members:
            profile = profile_map.get(m["user_id"], {})
            m["display_name"] = profile.get("display_name")

    return ApiResponse(data=members)


@router.post("/{org_id}/members/invite", status_code=201)
async def invite_member(org_id: str, body: MemberInvite, auth: AdminAuth, db: DB):
    """Invite a member by email. Creates user if not exists. Admin only."""
    if auth.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    require_one(
        db.table("organizations").select("id").eq("id", org_id).execute(),
        "Organization",
    )

    # Invite via Supabase Auth Admin — creates user if not exists
    try:
        response = db.auth.admin.invite_user_by_email(body.email)
        invited_user_id = response.user.id
    except Exception as e:
        error_msg = str(e).lower()
        # Supabase Auth Admin returns freeform error messages — no structured error codes.
        # This string check covers known variants ("already registered", "already been registered").
        if "already" in error_msg and "registered" in error_msg:
            # User exists — find their ID
            users_response = db.auth.admin.list_users()
            user = next((u for u in users_response if u.email == body.email), None)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            invited_user_id = user.id
        else:
            logger.exception("Supabase invite failed for %s", body.email)
            raise HTTPException(status_code=400, detail="Invitation failed")

    # Check not already a member
    existing = safe_get_one(
        db.table("organization_members")
        .select("id")
        .eq("organization_id", org_id)
        .eq("user_id", invited_user_id)
        .execute()
    )
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member")

    result = (
        db.table("organization_members")
        .insert(
            {
                "organization_id": org_id,
                "user_id": invited_user_id,
                "role": body.role,
                "invited_by": auth.user_id,
            }
        )
        .execute()
    )

    member = require_one(result, "Member")
    return ApiResponse(data=MemberResponse(**member))


@router.patch("/{org_id}/members/{member_id}")
async def update_member_role(
    org_id: str, member_id: str, body: MemberRoleUpdate, auth: AdminAuth, db: DB
):
    """Update a member's role. Admin only."""
    if auth.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    result = (
        db.table("organization_members")
        .update(
            {
                "role": body.role,
            }
        )
        .eq("id", member_id)
        .eq("organization_id", org_id)
        .execute()
    )

    member = require_one(result, "Member")
    return ApiResponse(data=member)


@router.delete("/{org_id}/members/{member_id}", status_code=204)
async def remove_member(org_id: str, member_id: str, auth: AdminAuth, db: DB):
    """Remove a member from the organization. Admin only."""
    if auth.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    member = require_one(
        db.table("organization_members")
        .select("user_id, role")
        .eq("id", member_id)
        .eq("organization_id", org_id)
        .execute(),
        "Member",
    )
    if member["role"] == "admin":
        admins = safe_get_list(
            db.table("organization_members")
            .select("id")
            .eq("organization_id", org_id)
            .eq("role", "admin")
            .execute()
        )
        if len(admins) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last admin")

    db.table("organization_members").delete().eq("id", member_id).eq(
        "organization_id", org_id
    ).execute()


@router.post("/{org_id}/members/leave", status_code=204)
async def leave_organization(org_id: str, auth: AuthOnly, db: DB):
    """Leave the organization. Cannot leave if last admin."""
    membership = safe_get_one(
        db.table("organization_members")
        .select("id, role")
        .eq("organization_id", org_id)
        .eq("user_id", auth.user_id)
        .execute()
    )
    if not membership:
        raise HTTPException(
            status_code=404, detail="You are not a member of this organization"
        )

    if membership["role"] == "admin":
        admins = safe_get_list(
            db.table("organization_members")
            .select("id")
            .eq("organization_id", org_id)
            .eq("role", "admin")
            .execute()
        )
        if len(admins) <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot leave as the last admin. Transfer admin role first.",
            )

    db.table("organization_members").delete().eq("id", membership["id"]).execute()

    # Clear default org if this was it
    profile = safe_get_one(
        db.table("profiles")
        .select("default_organization_id")
        .eq("id", auth.user_id)
        .execute()
    )
    if profile and profile.get("default_organization_id") == org_id:
        db.table("profiles").update({"default_organization_id": None}).eq(
            "id", auth.user_id
        ).execute()
