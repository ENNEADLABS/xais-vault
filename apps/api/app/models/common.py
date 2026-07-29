"""
Common Pydantic models — shared across all routers.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class UsageInfo(BaseModel):
    """LLM usage tracking — included in every AI-powered response."""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    model_used: str = ""


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    data: T | None = None
    usage: UsageInfo | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated API response."""
    data: list[T]
    total: int
    page: int
    per_page: int
    pages: int


class ErrorResponse(BaseModel):
    """Error response format."""
    error: dict[str, Any] = Field(
        ...,
        examples=[{"code": 404, "message": "Not found"}],
    )


class JobAccepted(BaseModel):
    """Response when an async job is created."""
    job_id: str
    status: str = "accepted"
    message: str = "Job created and queued for processing"
