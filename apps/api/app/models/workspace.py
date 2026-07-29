"""
Workspace Pydantic models.
A Workspace = a workspace for analyzing an investment opportunity.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ScanMode = Literal["quick", "standard", "deep"]


class ScanRequest(BaseModel):
    """Lancer un scan DD manuellement."""

    mode: ScanMode = "standard"


class WorkspaceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=200)
    emoji: str = Field(default="📁", max_length=32)
    description: str | None = None
    deal_type: str | None = Field(
        default=None, pattern=r"^(equity|debt|ma|restructuring|other)$"
    )
    sector: str | None = None
    target_company: str | None = None


class WorkspaceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    emoji: str | None = Field(default=None, max_length=32)
    description: str | None = None
    status: str | None = Field(default=None, pattern=r"^(active|archived|closed)$")
    deal_type: str | None = None
    sector: str | None = None
    target_company: str | None = None
    settings: dict | None = None


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    emoji: str
    description: str | None = None
    status: str
    deal_type: str | None = None
    sector: str | None = None
    target_company: str | None = None
    scan_status: str
    scan_summary: dict | None = None
    source_count: int | None = None
    insight_count: int | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class WorkspaceListItem(BaseModel):
    id: str
    name: str
    emoji: str
    status: str
    deal_type: str | None = None
    target_company: str | None = None
    scan_status: str
    source_count: int = 0
    insight_count: int = 0
    created_at: datetime
    updated_at: datetime
