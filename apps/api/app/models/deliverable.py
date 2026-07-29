"""
Deliverable Pydantic models — request/response schemas.
"""

from enum import Enum

from pydantic import BaseModel, Field


class DeliverableType(str, Enum):
    executive_summary = "executive_summary"
    investment_memo = "investment_memo"
    dd_report = "dd_report"


class DeliverableStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class DeliverableCreateRequest(BaseModel):
    """Body for POST /deliverables."""
    type: DeliverableType
    name: str = Field(min_length=1, max_length=255)
    options: dict | None = None


class DeliverableResponse(BaseModel):
    """Single deliverable in API responses."""
    id: str
    workspace_id: str
    organization_id: str
    generated_by: str
    type: str
    name: str
    status: str
    content_markdown: str | None = None
    file_path: str | None = None
    file_size_bytes: int | None = None
    options: dict = Field(default_factory=dict)
    current_step: str | None = None
    progress_percent: int = 0
    error_message: str | None = None
    created_at: str
    completed_at: str | None = None
