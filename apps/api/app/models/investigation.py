"""
Investigation Pydantic models — deep research results.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class InvestigationStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class InvestigationScope(str, Enum):
    documents = "documents"
    web = "web"
    both = "both"


class InvestigationCreate(BaseModel):
    """Créer une investigation depuis le Studio."""

    question: str = Field(..., min_length=1, max_length=500)
    insight_id: str | None = None
    scope: InvestigationScope = InvestigationScope.both


class InvestigationResponse(BaseModel):
    """Single investigation in API responses."""

    id: str
    workspace_id: str
    organization_id: str
    insight_id: str | None = None
    requested_by: str
    question: str
    scope: str
    status: str
    report: str | None = None
    web_sources: list[dict] | None = None
    doc_references: list[dict] | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    model_used: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
