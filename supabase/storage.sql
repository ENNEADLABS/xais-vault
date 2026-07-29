-- =============================================================
-- XAIS Vault v2 — Supabase Storage Configuration
-- =============================================================

-- Sources bucket (deal documents)
INSERT INTO storage.buckets (id, name, public)
VALUES ('sources', 'sources', false);

-- Deliverables bucket (generated DOCX files)
INSERT INTO storage.buckets (id, name, public)
VALUES ('deliverables', 'deliverables', false);

-- Storage policies — lecture filtrée par org_id, écriture via service role uniquement.
-- Le path des objets est structuré : {organization_id}/{deal_id}/{source_id}/{filename}
-- Le service role bypasse RLS — ces policies protègent l'accès direct via anon key + JWT.

-- Sources : les users ne peuvent lire que les fichiers de leurs orgs
-- (le 1er composant du path = organization_id)
CREATE POLICY "Users can read their org sources"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'sources'
        AND (storage.foldername(name))[1]::uuid IN (SELECT user_org_ids())
    );

-- Deliverables : même principe
CREATE POLICY "Users can read their org deliverables"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'deliverables'
        AND (storage.foldername(name))[1]::uuid IN (SELECT user_org_ids())
    );

-- Note : INSERT/UPDATE/DELETE sont réservés au service role (backend).
-- Pas de politique explicite = accès refusé via anon key.
