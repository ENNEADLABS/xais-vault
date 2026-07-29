"""Schemas Pydantic pour les endpoints /api/v2/admin."""

from pydantic import BaseModel

# ─── Usage ────────────────────────────────────────────────────────────────────


class UsageByMonth(BaseModel):
    month: str  # "2026-03"
    operation: str  # chat, scan, verify, investigate, deliverable
    count: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


class UsageTotals(BaseModel):
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    total_operations: int


class UsageStatsResponse(BaseModel):
    months: list[UsageByMonth]
    totals: UsageTotals


# ─── Overview ─────────────────────────────────────────────────────────────────


class OrgOverviewResponse(BaseModel):
    name: str
    plan: str
    member_count: int
    workspace_count: int
    source_count: int
    insight_count: int
    trial_ends_at: str | None


# ─── API Keys usage ───────────────────────────────────────────────────────────


class ApiKeyUsageItem(BaseModel):
    id: str
    name: str
    key_prefix: str
    is_active: bool
    rpm_limit: int
    rpd_limit: int
    last_used_at: str | None
    created_at: str


class ApiKeysUsageResponse(BaseModel):
    keys: list[ApiKeyUsageItem]


# ─── Activity log ─────────────────────────────────────────────────────────────


class ActivityItem(BaseModel):
    id: str
    type: str
    status: str
    created_at: str
    completed_at: str | None
    workspace_name: str | None = None
    source_name: str | None = None


class ActivityLogResponse(BaseModel):
    items: list[ActivityItem]
