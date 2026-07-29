"""
Chat Pydantic models — sessions and messages.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """User sends a chat message."""

    content: str = Field(..., min_length=1, max_length=50_000)
    session_id: str | None = None  # None = create new session
    source_ids: list[str] | None = None  # Filtrer le RAG sur ces sources (focus mode)


class ChatSessionResponse(BaseModel):
    """A chat session (conversation thread)."""

    id: str
    workspace_id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime


class ChatSessionRename(BaseModel):
    """Rename a chat session."""

    title: str = Field(..., min_length=1, max_length=200)


class ChatMessageResponse(BaseModel):
    """A single chat message (persisted)."""

    id: str
    session_id: str
    role: str  # user, assistant
    content: str
    citations: list[dict] | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    model_used: str | None = None
    created_at: datetime


class Citation(BaseModel):
    """A citation referencing a source document."""

    source_id: str
    source_name: str
    page_number: int | None = None
    section_title: str | None = None
    quote: str
