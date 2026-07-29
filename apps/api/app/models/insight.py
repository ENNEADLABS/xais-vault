"""
Insight Pydantic models — scan results, verification, human-in-the-loop.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class InsightType(str, Enum):
    red_flag = "red_flag"
    metric = "metric"
    observation = "observation"
    missing_info = "missing_info"


class InsightSeverity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class InsightStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    investigating = "investigating"
    rejected = "rejected"


class InsightAction(str, Enum):
    """Action an analyst can take on a insight."""
    confirm = "confirm"
    reject = "reject"
    investigate = "investigate"


class InsightResponse(BaseModel):
    """A single insight from the scanner or verifier."""
    id: str
    workspace_id: str
    type: str
    severity: str
    confidence_score: int
    title: str
    description: str
    source_id: str | None = None
    source_page: int | None = None
    source_section: str | None = None
    source_quote: str | None = None
    status: str
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    verification: dict | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class InsightActionRequest(BaseModel):
    """Request to confirm, reject, or investigate a insight."""
    action: InsightAction
