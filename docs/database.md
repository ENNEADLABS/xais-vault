# Schema Base de Donnees — XAIS Vault v2

Source de verite : `supabase/schema.sql` + migrations incrementales dans `supabase/migrations/` (appliquees via `supabase db push --linked`).

## Tables

### Organisations & Auth

**`organizations`**
- `id` UUID PK, `name`, `slug` (unique)
- `plan` : starter / premium / team / enterprise / trial (depuis migration `20260512100000_add_premium_to_plan_check.sql`)
- `chat_persona` : `NULL` (= persona `general` par défaut) / `'general'` / `'dd'` (depuis migration `20260512000000_add_chat_persona_to_organizations.sql`, Phase 2.B du pivot ; backfill `dd` pour les orgs préexistantes au 2026-05-12 pour préserver leur UX)
- `stripe_customer_id`, `stripe_subscription_id`
- `max_workspaces`, `max_sources_per_deal`, `max_members`

**`organization_members`**
- `id` UUID PK, `organization_id` FK, `user_id` FK
- `role` : admin / analyst / viewer
- `invited_by`, `invited_at`, `joined_at`

**`profiles`**
- `id` UUID PK (= auth.users.id), `email`
- `display_name`, `avatar_url`
- `default_organization_id` FK

### Workspaces & Sources

**`workspaces`**
- `id` UUID PK, `organization_id` FK, `created_by` FK
- `name`, `emoji`, `description`
- `deal_type` : equity / debt / ma / restructuring / other
- `sector`, `target_company`
- `status` : active / archived / closed
- `scan_status` : pending / scanning / completed / failed
- `source_count`, `insight_count` (compteurs denormalises)

**`sources`**
- `id` UUID PK, `workspace_id` FK, `organization_id` FK
- `name`, `file_type` (pdf/docx/xlsx/pptx/txt/md/csv)
- `file_size`, `storage_path`
- `status` : pending / processing / ready / failed
- `extracted_text`, `page_count`, `error_message`

**`chunks`**
- `id` UUID PK, `source_id` FK, `organization_id` FK
- `content` TEXT, `embedding` vector(1536)
- `chunk_index`, `page_number`, `section_title`
- Index HNSW sur `embedding` pour la recherche vectorielle

### Chat & RAG

**`chat_sessions`**
- `id` UUID PK, `workspace_id` FK, `user_id` FK, `organization_id` FK
- `title`, `message_count`
- `history_summary` TEXT, `history_summary_until` UUID (depuis migration `20260327000000_chat_history_summary.sql` — résumé automatique des conversations longues pour contenir le budget tokens)

**`chat_messages`**
- `id` UUID PK, `session_id` FK, `organization_id` FK
- `role` : user / assistant
- `content` TEXT, `citations` JSONB
- `input_tokens`, `output_tokens`, `cost_usd`, `model_used`

### Knowledge Graph

Tables introduites par la migration `20260405000000_knowledge_graph.sql` (RAG v3). Utilisées par `chat_graph.py` (graph search), `entity_extraction.py` (extraction LLM lors de l'indexation) et le composant `graph-tab.tsx` (visualisation Force Graph 2D).

**`entities`**
- `id` UUID PK, `workspace_id` FK, `organization_id` FK
- `name` (ex : "Acme SAS", "EBITDA", "Clause 7.2")
- `entity_type` : `company` / `person` / `metric` / `clause` / `date` / `amount`
- `description`, `properties` JSONB
- `embedding` vector(1536) (pour fuzzy entity matching)

**`entity_relations`**
- `id` UUID PK, `workspace_id` FK, `organization_id` FK
- `source_entity_id` FK, `target_entity_id` FK
- `relation_type` (ex : "détient", "emploie", "référence", "contredit")
- `description`, `confidence` FLOAT

**`chunk_entities`**
- Table de jonction `chunk_id` ↔ `entity_id` (un chunk peut mentionner plusieurs entités, une entité apparaît dans plusieurs chunks)
- Utilisée par le graph search pour traverser depuis un chunk vers les entités liées

### Insights & Investigations

**`insights`**
- `id` UUID PK, `workspace_id` FK, `organization_id` FK
- `type` : red_flag / metric / observation / missing_info
- `severity` : critical / high / medium / low
- `confidence_score` INT (0-100)
- `title`, `description`
- `source_id` FK, `source_page`, `source_section`, `source_quote`
- `status` : pending / confirmed / rejected / investigating
- `reviewed_by` FK, `reviewed_at`
- `verification` JSONB

**`investigations`**
- `id` UUID PK, `insight_id` FK, `workspace_id` FK, `organization_id` FK
- `status` : pending / processing / completed / failed
- `question`, `report` (Markdown)
- `doc_references` JSONB, `web_sources` JSONB
- `input_tokens`, `output_tokens`, `cost_usd`

### Livrables

**`deliverables`**
- `id` UUID PK, `workspace_id` FK, `organization_id` FK
- `type` : executive_summary / investment_memo / dd_report
- `status` : pending / processing / completed / failed
- `options` JSONB (include_insights, tone, etc.)
- `storage_path`, `file_size`

### Notes

**`notes`**
- `id` UUID PK, `workspace_id` FK, `user_id` FK, `organization_id` FK
- `content` TEXT, `is_pinned` BOOLEAN
- `tags` TEXT[], `linked_source_id`, `linked_insight_id`, `linked_message_id`

### Jobs & Traces

**`jobs`**
- `id` UUID PK, `organization_id` FK
- `type` : index_source / scan_workspace / verify_insight / investigate / generate_deliverable / dispatch_webhook
- `payload` JSONB, `status`, `result` JSONB, `error_message`
- `attempts`, `max_attempts` (defaut 3), `locked_until`
- `priority` (defaut 0, plus haut = plus prioritaire)

**`agent_traces`**
- `id` UUID PK, `job_id` FK, `organization_id` FK
- `agent_type`, `input` JSONB, `output` JSONB
- `input_tokens`, `output_tokens`, `cost_usd`, `model_used`
- `duration_ms`, `steps` JSONB

### API & Webhooks

**`api_keys`**
- `id` UUID PK, `organization_id` FK, `created_by` FK
- `name`, `key_prefix` (ex: `xv_live_abc`), `key_hash` (SHA-256)
- `permissions` JSONB, `rate_limit_rpm`, `rate_limit_rpd`
- `last_used_at`, `expires_at`, `is_active`

**`webhooks`**
- `id` UUID PK, `organization_id` FK, `created_by` FK
- `url`, `secret` (plaintext, pour signer les payloads)
- `events` TEXT[] (ex: `["insight.created", "deliverable.completed"]`)
- `is_active`, `failure_count`

**`webhook_deliveries`**
- `id` UUID PK, `webhook_id` FK, `organization_id` FK
- `event`, `payload` JSONB
- `status` : pending / success / failed
- `http_status`, `response_body`, `error_message`
- `attempt`, `next_retry_at`

### Usage

**`usage_logs`**
- `id` UUID PK, `organization_id` FK, `user_id` FK
- `operation`, `model_used`
- `input_tokens`, `output_tokens`, `cost_usd`

## RLS

Toutes les tables (sauf `jobs`) ont des policies RLS :
- SELECT/INSERT/UPDATE/DELETE filtrent par `organization_id`
- Verification via `auth.uid()` + lookup dans `organization_members`
- `jobs` accessible uniquement via service role (backend)
