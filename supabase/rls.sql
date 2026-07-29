-- =============================================================
-- XAIS Vault v2 — Row Level Security Policies
-- Applied after schema.sql
-- =============================================================

-- Enable RLS on all tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE deals ENABLE ROW LEVEL SECURITY;
ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE investigations ENABLE ROW LEVEL SECURITY;
ALTER TABLE deliverables ENABLE ROW LEVEL SECURITY;
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhooks ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_traces ENABLE ROW LEVEL SECURITY;
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_relations ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunk_entities ENABLE ROW LEVEL SECURITY;
-- jobs: NO RLS — backend-only via service role

-- ─── Helper function ──────────────────────────────────────

CREATE OR REPLACE FUNCTION user_org_ids()
RETURNS SETOF UUID
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT organization_id
    FROM organization_members
    WHERE user_id = auth.uid();
$$;

-- ─── Organizations ────────────────────────────────────────

CREATE POLICY "Users can view their organizations"
    ON organizations FOR SELECT
    USING (id IN (SELECT user_org_ids()));

CREATE POLICY "Admins can update their organizations"
    ON organizations FOR UPDATE
    USING (id IN (
        SELECT organization_id FROM organization_members
        WHERE user_id = auth.uid() AND role = 'admin'
    ));

-- ─── Organization Members ─────────────────────────────────

CREATE POLICY "Users can view members of their organizations"
    ON organization_members FOR SELECT
    USING (organization_id IN (SELECT user_org_ids()));

CREATE POLICY "Admins can manage members"
    ON organization_members FOR ALL
    USING (organization_id IN (
        SELECT organization_id FROM organization_members
        WHERE user_id = auth.uid() AND role = 'admin'
    ));

-- ─── Profiles ─────────────────────────────────────────────

CREATE POLICY "Users can view and update their own profile"
    ON profiles FOR ALL
    USING (id = auth.uid());

-- ─── Deals ────────────────────────────────────────────────

-- Lecture : tous les membres de l'org
CREATE POLICY "Users can view deals in their organizations"
    ON deals FOR SELECT
    USING (organization_id IN (SELECT user_org_ids()));

-- Écriture : admins et editors seulement (défense contre un viewer via anon key)
CREATE POLICY "Editors can manage deals in their organizations"
    ON deals FOR INSERT
    WITH CHECK (organization_id IN (
        SELECT organization_id FROM organization_members
        WHERE user_id = auth.uid() AND role IN ('admin', 'editor')
    ));

CREATE POLICY "Editors can update deals in their organizations"
    ON deals FOR UPDATE
    USING (organization_id IN (
        SELECT organization_id FROM organization_members
        WHERE user_id = auth.uid() AND role IN ('admin', 'editor')
    ));

CREATE POLICY "Admins can delete deals in their organizations"
    ON deals FOR DELETE
    USING (organization_id IN (
        SELECT organization_id FROM organization_members
        WHERE user_id = auth.uid() AND role = 'admin'
    ));

-- ─── Sources ──────────────────────────────────────────────

-- Lecture : tous les membres de l'org
CREATE POLICY "Users can view sources in their organizations"
    ON sources FOR SELECT
    USING (organization_id IN (SELECT user_org_ids()));

-- Écriture : admins et editors seulement
CREATE POLICY "Editors can manage sources in their organizations"
    ON sources FOR INSERT
    WITH CHECK (organization_id IN (
        SELECT organization_id FROM organization_members
        WHERE user_id = auth.uid() AND role IN ('admin', 'editor')
    ));

CREATE POLICY "Editors can update sources in their organizations"
    ON sources FOR UPDATE
    USING (organization_id IN (
        SELECT organization_id FROM organization_members
        WHERE user_id = auth.uid() AND role IN ('admin', 'editor')
    ));

CREATE POLICY "Admins can delete sources in their organizations"
    ON sources FOR DELETE
    USING (organization_id IN (
        SELECT organization_id FROM organization_members
        WHERE user_id = auth.uid() AND role = 'admin'
    ));

-- ─── Chunks ───────────────────────────────────────────────

CREATE POLICY "Users can access chunks in their organizations"
    ON chunks FOR SELECT
    USING (organization_id IN (SELECT user_org_ids()));

-- ─── Chat Sessions ────────────────────────────────────────

CREATE POLICY "Users can access chat sessions in their organizations"
    ON chat_sessions FOR ALL
    USING (organization_id IN (SELECT user_org_ids()));

-- ─── Chat Messages ────────────────────────────────────────

CREATE POLICY "Users can access chat messages in their organizations"
    ON chat_messages FOR ALL
    USING (organization_id IN (SELECT user_org_ids()));

-- ─── Findings ─────────────────────────────────────────────

CREATE POLICY "Users can access findings in their organizations"
    ON findings FOR ALL
    USING (organization_id IN (SELECT user_org_ids()));

-- ─── Investigations ───────────────────────────────────────

CREATE POLICY "Users can access investigations in their organizations"
    ON investigations FOR ALL
    USING (organization_id IN (SELECT user_org_ids()));

-- ─── Deliverables ─────────────────────────────────────────

CREATE POLICY "Users can access deliverables in their organizations"
    ON deliverables FOR ALL
    USING (organization_id IN (SELECT user_org_ids()));

-- ─── Notes ────────────────────────────────────────────────

CREATE POLICY "Users can access notes in their organizations"
    ON notes FOR ALL
    USING (organization_id IN (SELECT user_org_ids()));

-- ─── API Keys ─────────────────────────────────────────────

CREATE POLICY "Users can manage API keys in their organizations"
    ON api_keys FOR ALL
    USING (organization_id IN (SELECT user_org_ids()));

-- ─── Webhooks ─────────────────────────────────────────────

CREATE POLICY "Users can manage webhooks in their organizations"
    ON webhooks FOR ALL
    USING (organization_id IN (SELECT user_org_ids()));

CREATE POLICY "Users can view webhook deliveries in their organizations"
    ON webhook_deliveries FOR SELECT
    USING (webhook_id IN (
        SELECT id FROM webhooks
        WHERE organization_id IN (SELECT user_org_ids())
    ));

-- ─── Usage Logs ───────────────────────────────────────────

CREATE POLICY "Users can view usage logs in their organizations"
    ON usage_logs FOR SELECT
    USING (organization_id IN (SELECT user_org_ids()));

-- ─── Agent Traces ─────────────────────────────────────────

CREATE POLICY "Users can view agent traces in their organizations"
    ON agent_traces FOR SELECT
    USING (organization_id IN (SELECT user_org_ids()));


-- ─── Entities (Knowledge Graph) ──────────────────────────────

CREATE POLICY "Users can view entities in their organizations"
    ON entities FOR SELECT
    USING (organization_id IN (SELECT user_org_ids()));

-- ─── Entity Relations ────────────────────────────────────────

CREATE POLICY "Users can view entity relations in their organizations"
    ON entity_relations FOR SELECT
    USING (organization_id IN (SELECT user_org_ids()));

-- ─── Chunk Entities ──────────────────────────────────────────

CREATE POLICY "Users can view chunk entities via org membership"
    ON chunk_entities FOR SELECT
    USING (entity_id IN (
        SELECT id FROM entities
        WHERE organization_id IN (SELECT user_org_ids())
    ));


-- =============================================================
-- RPC Functions
-- =============================================================

-- ─── Job Queue: Atomic claim with SKIP LOCKED ─────────────

CREATE OR REPLACE FUNCTION claim_next_job(lock_until_ts TIMESTAMPTZ)
RETURNS SETOF jobs
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    claimed_id UUID;
BEGIN
    SELECT id INTO claimed_id
    FROM jobs
    WHERE status = 'pending'
      AND (locked_until IS NULL OR locked_until < now())
    ORDER BY priority DESC, created_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED;

    IF claimed_id IS NOT NULL THEN
        UPDATE jobs
        SET status = 'processing',
            locked_until = lock_until_ts,
            started_at = now(),
            attempts = attempts + 1
        WHERE id = claimed_id;

        RETURN QUERY SELECT * FROM jobs WHERE id = claimed_id;
    END IF;
END;
$$;
