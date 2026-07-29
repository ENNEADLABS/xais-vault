"""
Source Pydantic models.
A Source = a document uploaded to a workspace for analysis.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SourceResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    type: str  # pdf, docx, xlsx, pptx, txt, md, csv
    file_size_bytes: int | None = None
    status: str  # pending, processing, ready, failed
    error_message: str | None = None
    page_count: int | None = None
    word_count: int | None = None
    summary: str | None = None
    topics: list[str] | None = None
    suggested_questions: list[str] | None = None
    uploaded_by: str
    created_at: datetime


MAX_TEXT_SIZE = 1_000_000  # 1 MB de texte (~500 pages)


class SourceTextCreate(BaseModel):
    """For pasting text directly as a source."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=MAX_TEXT_SIZE)
