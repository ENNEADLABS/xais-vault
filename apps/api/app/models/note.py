"""
Note Pydantic models — structured annotations on workspaces.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ChecklistItem(BaseModel):
    """Single checklist item inside a note."""

    text: str
    checked: bool = False


class NoteCreate(BaseModel):
    """Request body for creating a note."""

    title: str | None = None
    content: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
    is_pinned: bool = False
    checklist_items: list[ChecklistItem] | None = None
    linked_source_id: str | None = None
    linked_insight_id: str | None = None
    linked_message_id: str | None = None


class NoteUpdate(BaseModel):
    """Request body for partial update. All fields optional."""

    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    is_pinned: bool | None = None
    checklist_items: list[ChecklistItem] | None = None
    linked_source_id: str | None = None
    linked_insight_id: str | None = None
    linked_message_id: str | None = None


class NoteResponse(BaseModel):
    """A single note."""

    id: str
    workspace_id: str
    user_id: str
    title: str | None = None
    content: str
    tags: list[str] = Field(default_factory=list)
    is_pinned: bool = False
    checklist_items: list[ChecklistItem] | None = None
    linked_source_id: str | None = None
    linked_insight_id: str | None = None
    linked_message_id: str | None = None
    created_at: datetime
    updated_at: datetime
