"""Schemas Pydantic pour les endpoints /api/v2/super-admin."""

from pydantic import BaseModel

# ─── Overview ─────────────────────────────────────────────────────────────────


class PlatformOverview(BaseModel):
    total_organizations: int
    total_workspaces: int
    total_sources: int
    total_insights: int
    total_deliverables: int
    total_chat_messages: int
    active_orgs_7d: int
    failed_jobs_24h: int
    job_success_rate_7d: float


# ─── Organisations ────────────────────────────────────────────────────────────


class OrgMetrics(BaseModel):
    org_id: str
    org_name: str
    plan: str
    member_count: int
    workspace_count: int
    source_count: int
    insight_count: int
    deliverable_count: int
    chat_message_count: int
    last_activity_at: str | None
    created_at: str


# ─── Activité users ──────────────────────────────────────────────────────────


class UserActivity(BaseModel):
    user_id: str
    email: str | None
    display_name: str | None
    org_name: str
    workspaces_created: int
    sources_uploaded: int
    chat_messages_sent: int
    deliverables_generated: int
    last_active_at: str | None


# ─── Feed d'activité ─────────────────────────────────────────────────────────


class SuperAdminActivityItem(BaseModel):
    id: str
    type: str
    status: str
    org_name: str
    workspace_name: str | None
    created_at: str
    completed_at: str | None
    error_message: str | None


# ─── Summarization monitoring ────────────────────────────────────────────────


class SummarizationStats(BaseModel):
    total_count: int
    count_24h: int
    total_cost_usd: float
    cost_24h_usd: float
    avg_cost_usd: float
    avg_input_tokens: int
    avg_output_tokens: int


# ─── Erreurs ─────────────────────────────────────────────────────────────────


class ErrorItem(BaseModel):
    id: str
    type: str
    org_name: str
    workspace_name: str | None
    error_message: str | None
    attempts: int
    created_at: str
    failed_at: str | None


# ─── Knowledge Graph monitoring ────────────────────────────────────────��────


class GraphStats(BaseModel):
    total_entities: int
    total_relations: int
    total_chunk_links: int
    entities_by_type: dict[str, int]
    workspaces_with_graph: int
    extraction_cost_total_usd: float
    extraction_cost_24h_usd: float
    avg_entities_per_workspace: float
