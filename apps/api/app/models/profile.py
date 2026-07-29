"""
Profile Pydantic models.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ProfileResponse(BaseModel):
    id: str
    display_name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    default_organization_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=100)
    avatar_url: str | None = None
