-- =============================================================
-- XAIS Vault v2 — Schema PostgreSQL
-- Source de vérité unique. Pas de migrations incrémentales.
-- Supabase PostgreSQL 17 + pgvector
-- =============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================================
-- ORGANIZATIONS & AUTH
-- =============================================================

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    logo_url TEXT,
    plan TEXT NOT NULL DEFAULT 'starter' CHECK (plan IN ('starter', 'premium', 'team', 'enterprise', 'trial')),
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    trial_ends_at TIMESTAMPTZ,
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'analyst' CHECK (role IN ('admin', 'analyst', 'viewer')),
    invited_by UUID REFERENCES auth.users(id),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, user_id)
);

CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    avatar_url TEXT,
    default_organization_id UUID REFERENCES organizations(id),
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================
-- DEALS (anciennement "notebooks")
-- =============================================================

CREATE TABLE deals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES auth.users(id),
    name TEXT NOT NULL,
    emoji TEXT DEFAULT '📁',
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived', 'closed')),
    deal_type TEXT CHECK (deal_type IN ('equity', 'debt', 'ma', 'restructuring', 'other')),
    sector TEXT,
    target_company TEXT,
    settings JSONB NOT NULL DEFAULT '{}',
    scan_status TEXT NOT NULL DEFAULT 'pending' CHECK (scan_status IN ('pending', 'scanning', 'scanned', 'failed')),
    scan_summary JSONB,  -- résumé du scan automatique (métriques globales)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================
-- SOURCES (documents du deal)
-- =============================================================

CREATE TABLE sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    uploaded_by UUID NOT NULL REFERENCES auth.users(id),
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('pdf', 'docx', 'xlsx', 'pptx', 'txt', 'md', 'csv')),
    file_path TEXT,                    -- chemin dans Supabase Storage
    file_size_bytes INT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'ready', 'failed')),
    error_message TEXT,
    -- Contenu extrait
    extracted_text TEXT,               -- texte brut extrait
    page_count INT,
    word_count INT,
    -- Résumé IA
    summary TEXT,
    topics TEXT[],
    suggested_questions TEXT[],
    -- Métadonnées
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================
-- CHUNKS & EMBEDDINGS (RAG vectoriel)
-- =============================================================

CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    deal_id UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INT NOT NULL,          -- ordre dans le document
    token_count INT,
    page_number INT,                   -- page d'origine (pour les citations)
    section_title TEXT,                -- titre de section si détecté
    embedding VECTOR(1536),            -- Gemini Embedding 2
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index pour la recherche sémantique (cosine similarity)
CREATE INDEX idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_chunks_source ON chunks(source_id);
CREATE INDEX idx_chunks_deal ON chunks(deal_id);

-- RPC search_chunks supprimée (remplacée par search_chunks_hybrid dans migration 20260325000000)

-- =============================================================
-- KNOWLEDGE GRAPH (RAG v3 — entités + relations cross-document)
-- =============================================================

CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,               -- "Acme SAS", "EBITDA", "Clause 7.2"
    entity_type TEXT NOT NULL CHECK (entity_type IN (
        'company', 'person', 'metric', 'clause', 'date', 'amount'
    )),
    description TEXT,                 -- Résumé court de l'entité
    properties JSONB DEFAULT '{}',    -- Métadonnées libres (secteur, montant, etc.)
    embedding VECTOR(1536),           -- Pour fuzzy entity matching
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_entities_embedding ON entities
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_entities_deal ON entities(deal_id);
CREATE INDEX idx_entities_org ON entities(organization_id);
CREATE INDEX idx_entities_type ON entities(deal_id, entity_type);
CREATE INDEX idx_entities_name_lower ON entities(deal_id, lower(name));

CREATE TABLE entity_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    source_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,      -- "détient", "emploie", "référence", "contredit"
    description TEXT,                 -- "Acme SAS détient 60% de Beta Corp"
    confidence FLOAT DEFAULT 1.0,     -- Score de confiance LLM
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_entity_relations_deal ON entity_relations(deal_id);
CREATE INDEX idx_entity_relations_source ON entity_relations(source_entity_id);
CREATE INDEX idx_entity_relations_target ON entity_relations(target_entity_id);

CREATE TABLE chunk_entities (
    chunk_id UUID NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    mention_count INT DEFAULT 1,      -- Nombre de mentions dans le chunk
    PRIMARY KEY (chunk_id, entity_id)
);

CREATE INDEX idx_chunk_entities_entity ON chunk_entities(entity_id);

-- =============================================================
-- CHAT
-- =============================================================

CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    citations JSONB,                   -- [{source_id, page, section, text}]
    input_tokens INT,
    output_tokens INT,
    cost_usd NUMERIC(10,6),
    model_used TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================
-- FINDINGS (résultats du scan + vérifications)
-- =============================================================

CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    -- Classification
    type TEXT NOT NULL CHECK (type IN ('red_flag', 'metric', 'observation', 'missing_info')),
    severity TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    confidence_score INT NOT NULL CHECK (confidence_score BETWEEN 0 AND 100),
    -- Contenu
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    -- Citation source
    source_id UUID REFERENCES sources(id) ON DELETE SET NULL,
    source_page INT,
    source_section TEXT,
    source_quote TEXT,
    -- Statut (human-in-the-loop)
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'investigating', 'rejected')),
    reviewed_by UUID REFERENCES auth.users(id),
    reviewed_at TIMESTAMPTZ,
    -- Vérification (Agent Vérificateur)
    verification JSONB,                -- {verdict, evidence[], cross_references[], agent_trace_id}
    -- Métadonnées
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================
-- INVESTIGATIONS (deep research)
-- =============================================================

CREATE TABLE investigations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    finding_id UUID REFERENCES findings(id) ON DELETE SET NULL,
    requested_by UUID NOT NULL REFERENCES auth.users(id),
    -- Question / scope
    question TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'documents' CHECK (scope IN ('documents', 'web', 'both')),
    -- Résultat
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    report TEXT,                        -- mini-rapport Markdown
    web_sources JSONB,                 -- [{url, title, snippet, accessed_at}]
    doc_references JSONB,              -- [{source_id, page, section, quote}]
    -- Coût
    input_tokens INT,
    output_tokens INT,
    cost_usd NUMERIC(10,6),
    model_used TEXT,
    -- Timing
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- =============================================================
-- DELIVERABLES (livrables générés)
-- =============================================================

CREATE TABLE deliverables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    generated_by UUID NOT NULL REFERENCES auth.users(id),
    -- Type
    type TEXT NOT NULL CHECK (type IN ('executive_summary', 'investment_memo', 'dd_report')),
    name TEXT NOT NULL,
    -- Contenu
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    content_markdown TEXT,             -- contenu intermédiaire (Markdown)
    file_path TEXT,                    -- chemin du DOCX dans Supabase Storage
    file_size_bytes INT,
    -- Options de génération
    options JSONB NOT NULL DEFAULT '{}',  -- {include_findings: bool, include_investigations: bool, tone: string}
    -- Progression
    current_step TEXT,
    progress_percent INT DEFAULT 0,
    -- Coût
    total_input_tokens INT,
    total_output_tokens INT,
    total_cost_usd NUMERIC(10,6),
    models_used JSONB,
    -- Timing
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- =============================================================
-- NOTES (annotations structurées)
-- =============================================================

CREATE TABLE notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    title TEXT,
    content TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    is_pinned BOOLEAN NOT NULL DEFAULT false,
    -- Liens
    linked_source_id UUID REFERENCES sources(id) ON DELETE SET NULL,
    linked_finding_id UUID REFERENCES findings(id) ON DELETE SET NULL,
    linked_message_id UUID REFERENCES chat_messages(id) ON DELETE SET NULL,
    -- Checklist
    checklist_items JSONB,             -- [{text, checked}]
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================
-- JOB QUEUE
-- =============================================================

CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    type TEXT NOT NULL,                -- index_source, scan_deal, verify_finding, investigate, generate_deliverable, dispatch_webhook
    payload JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    result JSONB,
    error_message TEXT,
    attempts INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 3,
    locked_until TIMESTAMPTZ,
    priority INT NOT NULL DEFAULT 0,   -- plus haut = plus prioritaire
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_jobs_pending ON jobs(status, priority DESC, created_at ASC) WHERE status = 'pending';
CREATE INDEX idx_jobs_locked ON jobs(locked_until) WHERE status = 'processing';

-- =============================================================
-- AGENT TRACES (audit trail des agents)
-- =============================================================

CREATE TABLE agent_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    deal_id UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    agent_type TEXT NOT NULL CHECK (agent_type IN ('scanner', 'verifier', 'researcher', 'writer')),
    -- Exécution
    input_summary TEXT,                -- résumé de l'input (pas le contenu complet)
    output_summary TEXT,               -- résumé de l'output
    steps JSONB,                       -- [{step, action, result, duration_ms}]
    -- Coût
    input_tokens INT,
    output_tokens INT,
    cost_usd NUMERIC(10,6),
    model_used TEXT,
    -- Timing
    duration_ms INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================
-- API KEYS & WEBHOOKS
-- =============================================================

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES auth.users(id),
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,      -- SHA256 du secret
    key_prefix TEXT NOT NULL,           -- premiers 8 chars pour identification
    scopes TEXT[] NOT NULL DEFAULT '{*}',
    rpm_limit INT DEFAULT 60,
    rpd_limit INT DEFAULT 1000,
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES auth.users(id),
    url TEXT NOT NULL,
    events TEXT[] NOT NULL,
    secret TEXT NOT NULL,               -- whsec_... pour HMAC-SHA256
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_id UUID NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'delivered', 'failed')),
    attempt INT NOT NULL DEFAULT 0,
    http_status INT,
    response_body TEXT,
    next_retry_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered_at TIMESTAMPTZ
);

-- =============================================================
-- USAGE TRACKING
-- =============================================================

CREATE TABLE usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id),
    deal_id UUID REFERENCES deals(id) ON DELETE SET NULL,
    operation TEXT NOT NULL,            -- chat, scan, verify, investigate, deliverable
    input_tokens INT,
    output_tokens INT,
    cost_usd NUMERIC(10,6),
    model_used TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_usage_org_month ON usage_logs(organization_id, created_at);

-- =============================================================
-- INDEXES
-- =============================================================

CREATE INDEX idx_deals_org ON deals(organization_id);
CREATE INDEX idx_sources_deal ON sources(deal_id);
CREATE INDEX idx_sources_org ON sources(organization_id);
CREATE INDEX idx_findings_deal ON findings(deal_id);
CREATE INDEX idx_findings_status ON findings(deal_id, status);
CREATE INDEX idx_investigations_deal ON investigations(deal_id);
CREATE INDEX idx_deliverables_deal ON deliverables(deal_id);
CREATE INDEX idx_notes_deal ON notes(deal_id);
CREATE INDEX idx_chat_sessions_deal ON chat_sessions(deal_id);
CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX idx_agent_traces_deal ON agent_traces(deal_id);
CREATE INDEX idx_org_members_user ON organization_members(user_id);
CREATE INDEX idx_org_members_org ON organization_members(organization_id);
CREATE INDEX idx_webhook_deliveries_webhook ON webhook_deliveries(webhook_id);

-- =============================================================
-- REALTIME
-- Toutes les tables écoutées par le frontend doivent :
--   1. Avoir REPLICA IDENTITY FULL pour que le filtre (ex: deal_id=eq.X)
--      fonctionne sur les UPDATEs faits via service role (qui bypass RLS).
--      Sans FULL, PostgreSQL n'inclut pas les OLD values dans le WAL,
--      et Supabase Realtime ne peut pas évaluer le filtre.
--   2. Être ajoutées à la publication supabase_realtime.
-- =============================================================

ALTER TABLE sources REPLICA IDENTITY FULL;
ALTER TABLE deals REPLICA IDENTITY FULL;
ALTER TABLE findings REPLICA IDENTITY FULL;
ALTER TABLE investigations REPLICA IDENTITY FULL;
ALTER TABLE deliverables REPLICA IDENTITY FULL;

ALTER PUBLICATION supabase_realtime ADD TABLE sources;
ALTER PUBLICATION supabase_realtime ADD TABLE deals;
ALTER PUBLICATION supabase_realtime ADD TABLE findings;
ALTER PUBLICATION supabase_realtime ADD TABLE investigations;
ALTER PUBLICATION supabase_realtime ADD TABLE deliverables;
CREATE INDEX idx_webhook_deliveries_pending ON webhook_deliveries(status, next_retry_at) WHERE status = 'pending';

-- =============================================================
-- VIEWS
-- =============================================================

-- Vue dénormalisée pour list_deals — élimine le N+1 (41 queries → 1).
-- source_count et finding_count sont calculés en une seule query SQL.
CREATE OR REPLACE VIEW deals_with_counts AS
SELECT
    d.*,
    COALESCE(s.cnt, 0) AS source_count,
    COALESCE(f.cnt, 0) AS finding_count
FROM deals d
LEFT JOIN (
    SELECT deal_id, COUNT(*) AS cnt FROM sources GROUP BY deal_id
) s ON s.deal_id = d.id
LEFT JOIN (
    SELECT deal_id, COUNT(*) AS cnt FROM findings GROUP BY deal_id
) f ON f.deal_id = d.id;
