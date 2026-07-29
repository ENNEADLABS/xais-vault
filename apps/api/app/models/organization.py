"""
Organization & Member Pydantic models.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Valeurs supportées pour `organizations.chat_persona`. NULL est aussi accepté
# (= fallback persona "general"). Voir apps/api/app/services/prompts/chat_personas.py.
ChatPersona = Literal["general", "dd"]


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")


class OrganizationUpdate(BaseModel):
    name: str | None = None
    logo_url: str | None = None
    settings: dict | None = None
    chat_persona: ChatPersona | None = None


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    logo_url: str | None = None
    plan: str
    created_at: datetime
    member_count: int | None = None


class MemberInvite(BaseModel):
    email: str
    role: str = Field(default="analyst", pattern=r"^(admin|analyst|viewer)$")


class MemberResponse(BaseModel):
    id: str
    user_id: str
    role: str
    display_name: str | None = None
    email: str | None = None
    joined_at: datetime


class MemberRoleUpdate(BaseModel):
    role: str = Field(..., pattern=r"^(admin|analyst|viewer)$")
