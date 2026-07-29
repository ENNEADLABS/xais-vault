-- =============================================================
-- Knowledge Graph — entités, relations, liens chunk↔entité
-- RAG v3 : ajoute un knowledge graph pour le retrieval cross-document
-- =============================================================

-- ─── Entités extraites des documents ─────────────────────────
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN (
        'company', 'person', 'metric', 'clause', 'date', 'amount'
    )),
    description TEXT,
    properties JSONB DEFAULT '{}',
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index pour la recherche sémantique sur les entités
CREATE INDEX idx_entities_embedding ON entities
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_entities_deal ON entities(deal_id);
CREATE INDEX idx_entities_org ON entities(organization_id);
CREATE INDEX idx_entities_type ON entities(deal_id, entity_type);
-- Index pour la déduplication par nom normalisé
CREATE INDEX idx_entities_name_lower ON entities(deal_id, lower(name));

-- ─── Relations entre entités ─────────────────────────────────
CREATE TABLE entity_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    source_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    description TEXT,
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_entity_relations_deal ON entity_relations(deal_id);
CREATE INDEX idx_entity_relations_source ON entity_relations(source_entity_id);
CREATE INDEX idx_entity_relations_target ON entity_relations(target_entity_id);

-- ─── Lien chunk ↔ entité (N:N) ──────────────────────────────
CREATE TABLE chunk_entities (
    chunk_id UUID NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    mention_count INT DEFAULT 1,
    PRIMARY KEY (chunk_id, entity_id)
);

CREATE INDEX idx_chunk_entities_entity ON chunk_entities(entity_id);

-- ─── RLS ─────────────────────────────────────────────────────
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_relations ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunk_entities ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view entities in their organizations"
    ON entities FOR SELECT
    USING (organization_id IN (SELECT user_org_ids()));

CREATE POLICY "Users can view entity relations in their organizations"
    ON entity_relations FOR SELECT
    USING (organization_id IN (SELECT user_org_ids()));

CREATE POLICY "Users can view chunk entities via org membership"
    ON chunk_entities FOR SELECT
    USING (entity_id IN (
        SELECT id FROM entities
        WHERE organization_id IN (SELECT user_org_ids())
    ));
