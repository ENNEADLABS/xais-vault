export interface Workspace {
  id: string;
  name: string;
  emoji: string;
  description: string | null;
  deal_type: string;
  sector: string | null;
  target_company: string | null;
  status: "active" | "archived" | "closed";
  scan_status: "pending" | "scanning" | "scanned" | "failed";
  organization_id: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  source_count: number;
  insight_count: number;
}

export interface Source {
  id: string;
  workspace_id: string;
  organization_id: string;
  name: string;
  type: "pdf" | "docx" | "xlsx" | "pptx" | "txt" | "md" | "csv";
  file_size_bytes: number | null;
  status: "pending" | "processing" | "ready" | "failed";
  error_message: string | null;
  page_count: number | null;
  word_count: number | null;
  summary: string | null;
  topics: string[] | null;
  suggested_questions: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface ChatSession {
  id: string;
  workspace_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  source_id: string;
  source_name: string;
  page_number: number | null;
  section_title: string | null;
  quote: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[] | null;
  created_at: string;
}

export interface Insight {
  id: string;
  workspace_id: string;
  organization_id: string;
  type: "red_flag" | "metric" | "observation" | "missing_info";
  severity: "critical" | "high" | "medium" | "low";
  confidence_score: number;
  title: string;
  description: string;
  source_id: string | null;
  source_name: string | null;
  source_page: number | null;
  source_section: string | null;
  source_quote: string | null;
  status: "pending" | "confirmed" | "investigating" | "rejected";
  reviewed_by: string | null;
  reviewed_at: string | null;
  verification: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface Investigation {
  id: string;
  workspace_id: string;
  organization_id: string;
  insight_id: string | null;
  requested_by: string;
  question: string;
  scope: "documents" | "web" | "both";
  status: "pending" | "processing" | "completed" | "failed";
  report: string | null;
  web_sources: Array<{
    url: string;
    title: string;
    snippet: string;
    accessed_at: string;
  }> | null;
  doc_references: Array<{
    source_id: string;
    page: number;
    section: string;
    quote: string;
  }> | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface Deliverable {
  id: string;
  workspace_id: string;
  organization_id: string;
  generated_by: string;
  type: "executive_summary" | "investment_memo" | "dd_report";
  name: string;
  status: "pending" | "processing" | "completed" | "failed";
  content_markdown: string | null;
  file_path: string | null;
  file_size_bytes: number | null;
  options: Record<string, unknown>;
  current_step: string | null;
  progress_percent: number;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export type ChatPersona = "general" | "dd";

export interface Organization {
  id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  plan: "starter" | "premium" | "team" | "enterprise" | "trial";
  created_at: string;
  member_count: number | null;
  chat_persona: ChatPersona | null;
}

export interface OrganizationMember {
  id: string;
  user_id: string;
  role: "admin" | "analyst" | "viewer";
  display_name: string | null;
  email: string | null;
  joined_at: string;
}

export interface UserProfile {
  id: string;
  email: string | null;
  display_name: string | null;
  avatar_url: string | null;
  default_organization_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChecklistItem {
  text: string;
  checked: boolean;
}

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  rpm_limit: number;
  rpd_limit: number;
  is_active: boolean;
  last_used_at: string | null;
  expires_at: string | null;
  created_by: string;
  created_at: string;
}

export interface ApiKeyCreated extends ApiKey {
  key: string; // xv_live_{32_hex} — affiché UNE SEULE FOIS
}

export interface ApiKeyWithUsage extends ApiKey {
  usage_today: number;
  usage_this_month: number;
}

// ─── Webhooks ────────────────────────────────────────────

export const WEBHOOK_EVENTS = [
  "source.ready",
  "source.failed",
  "scan.completed",
  "insight.created",
  "investigation.completed",
  "deliverable.ready",
  "webhook.test",
] as const;

export type WebhookEvent = (typeof WEBHOOK_EVENTS)[number];

export interface Webhook {
  id: string;
  url: string;
  events: string[];
  is_active: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface WebhookCreated extends Webhook {
  secret: string; // whsec_{32_hex} — affiché UNE SEULE FOIS
}

export interface WebhookDelivery {
  id: string;
  webhook_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  status: "pending" | "delivered" | "failed";
  attempt: number;
  http_status: number | null;
  response_body: string | null;
  next_retry_at: string | null;
  created_at: string;
  delivered_at: string | null;
}

// ─── Billing ─────────────────────────────────────────────

export interface BillingLimits {
  max_workspaces: number | null;
  max_analyses_per_month: number | null;
}

export interface BillingUsage {
  workspaces_count: number;
  analyses_this_month: number;
}

export interface BillingStatus {
  plan: "starter" | "premium" | "team" | "enterprise" | "trial";
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  trial_ends_at: string | null;
  limits: BillingLimits;
  current_usage: BillingUsage;
}

// ─── Admin Dashboard ─────────────────────────────────────

export interface UsageByMonth {
  month: string;
  operation: string;
  count: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

export interface UsageTotals {
  total_cost_usd: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_operations: number;
}

export interface UsageStatsResponse {
  months: UsageByMonth[];
  totals: UsageTotals;
}

export interface OrgOverviewResponse {
  name: string;
  plan: string;
  member_count: number;
  workspace_count: number;
  source_count: number;
  insight_count: number;
  trial_ends_at: string | null;
}

export interface ActivityItem {
  id: string;
  type: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  workspace_name: string | null;
  source_name: string | null;
}

export interface ActivityLogResponse {
  items: ActivityItem[];
}

export interface ApiKeyUsageItem {
  id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  rpm_limit: number;
  rpd_limit: number;
  last_used_at: string | null;
  created_at: string;
}

export interface ApiKeysUsageResponse {
  keys: ApiKeyUsageItem[];
}

// ─── Super Admin Dashboard ──────────────────────────────

export interface PlatformOverview {
  total_organizations: number;
  total_workspaces: number;
  total_sources: number;
  total_insights: number;
  total_deliverables: number;
  total_chat_messages: number;
  active_orgs_7d: number;
  failed_jobs_24h: number;
  job_success_rate_7d: number;
}

export interface OrgMetrics {
  org_id: string;
  org_name: string;
  plan: string;
  member_count: number;
  workspace_count: number;
  source_count: number;
  insight_count: number;
  deliverable_count: number;
  chat_message_count: number;
  last_activity_at: string | null;
  created_at: string;
}

export interface SuperAdminUserActivity {
  user_id: string;
  email: string | null;
  display_name: string | null;
  org_name: string;
  workspaces_created: number;
  sources_uploaded: number;
  chat_messages_sent: number;
  deliverables_generated: number;
  last_active_at: string | null;
}

export interface SuperAdminActivityItem {
  id: string;
  type: string;
  status: string;
  org_name: string;
  workspace_name: string | null;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface SummarizationStats {
  total_count: number;
  count_24h: number;
  total_cost_usd: number;
  cost_24h_usd: number;
  avg_cost_usd: number;
  avg_input_tokens: number;
  avg_output_tokens: number;
}

export interface SuperAdminErrorItem {
  id: string;
  type: string;
  org_name: string;
  workspace_name: string | null;
  error_message: string | null;
  attempts: number;
  created_at: string;
  failed_at: string | null;
}

export interface Note {
  id: string;
  workspace_id: string;
  user_id: string;
  title: string | null;
  content: string;
  tags: string[];
  is_pinned: boolean;
  checklist_items: ChecklistItem[] | null;
  linked_source_id: string | null;
  linked_insight_id: string | null;
  linked_message_id: string | null;
  created_at: string;
  updated_at: string;
}
