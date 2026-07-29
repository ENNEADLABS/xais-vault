"""
Profile router — GET and PATCH for the current user's profile.

Uses AuthOnly (no org context needed — profile is per-user, not per-org).
Auto-creates the profile on first GET if missing.
"""

from fastapi import APIRouter, HTTPException

from packages.db.client import require_one, safe_get_one

from ..dependencies import DB, AuthOnly
from ..models.common import ApiResponse
from ..models.profile import ProfileResponse, ProfileUpdate

router = APIRouter()


@router.get("/")
async def get_profile(auth: AuthOnly, db: DB):
    """Get current user profile. Auto-creates if missing."""
    result = db.table("profiles").select("*").eq("id", auth.user_id).execute()
    profile = safe_get_one(result)

    if not profile:
        result = db.table("profiles").insert({
            "id": auth.user_id,
        }).execute()
        profile = require_one(result, "Profile")

    profile["email"] = auth.email
    return ApiResponse(data=ProfileResponse(**profile))


@router.patch("/")
async def update_profile(body: ProfileUpdate, auth: AuthOnly, db: DB):
    """Update display_name and/or avatar_url."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = db.table("profiles").update(updates).eq("id", auth.user_id).execute()
    profile = require_one(result, "Profile")

    profile["email"] = auth.email
    return ApiResponse(data=ProfileResponse(**profile))
