-- Super-admin RPCs — métriques cross-org pour le dashboard opérationnel.
-- Ces fonctions sont appelées via service_role uniquement (pas de RLS).

-- RPC 0 : Vue d'ensemble plateforme (remplace ~10 queries séquentielles)
CREATE OR REPLACE FUNCTION super_admin_platform_overview()
RETURNS JSON
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
    SELECT json_build_object(
        'total_organizations', (SELECT COUNT(*) FROM organizations),
        'total_deals',         (SELECT COUNT(*) FROM deals),
        'total_sources',       (SELECT COUNT(*) FROM sources),
        'total_findings',      (SELECT COUNT(*) FROM findings),
        'total_deliverables',  (SELECT COUNT(*) FROM deliverables),
        'total_chat_messages', (SELECT COUNT(*) FROM chat_messages WHERE role = 'user'),
        'active_orgs_7d',      (
            SELECT COUNT(DISTINCT organization_id)
            FROM jobs
            WHERE created_at >= NOW() - INTERVAL '7 days'
        ),
        'failed_jobs_24h',     (
            SELECT COUNT(*)
            FROM jobs
            WHERE status = 'failed' AND created_at >= NOW() - INTERVAL '24 hours'
        ),
        'job_success_rate_7d', (
            SELECT COALESCE(
                ROUND(
                    COUNT(*) FILTER (WHERE status = 'completed') * 100.0
                    / NULLIF(COUNT(*) FILTER (WHERE status IN ('completed', 'failed')), 0),
                    1
                ),
                100.0
            )
            FROM jobs
            WHERE created_at >= NOW() - INTERVAL '7 days'
        )
    );
$$;


-- RPC 1 : Métriques par organisation
CREATE OR REPLACE FUNCTION super_admin_org_metrics()
RETURNS TABLE (
    org_id UUID,
    org_name TEXT,
    plan TEXT,
    member_count BIGINT,
    deal_count BIGINT,
    source_count BIGINT,
    finding_count BIGINT,
    deliverable_count BIGINT,
    chat_message_count BIGINT,
    last_activity_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
    SELECT
        o.id AS org_id,
        o.name AS org_name,
        o.plan,
        COALESCE(m.cnt, 0) AS member_count,
        COALESCE(d.cnt, 0) AS deal_count,
        COALESCE(s.cnt, 0) AS source_count,
        COALESCE(f.cnt, 0) AS finding_count,
        COALESCE(dl.cnt, 0) AS deliverable_count,
        COALESCE(cm.cnt, 0) AS chat_message_count,
        j.last_activity_at,
        o.created_at
    FROM organizations o
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS cnt FROM organization_members WHERE organization_id = o.id
    ) m ON TRUE
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS cnt FROM deals WHERE organization_id = o.id
    ) d ON TRUE
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS cnt FROM sources WHERE organization_id = o.id
    ) s ON TRUE
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS cnt FROM findings WHERE organization_id = o.id
    ) f ON TRUE
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS cnt FROM deliverables WHERE organization_id = o.id
    ) dl ON TRUE
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS cnt
        FROM chat_messages cm2
        JOIN chat_sessions cs ON cs.id = cm2.session_id
        JOIN deals d2 ON d2.id = cs.deal_id
        WHERE d2.organization_id = o.id AND cm2.role = 'user'
    ) cm ON TRUE
    LEFT JOIN LATERAL (
        SELECT MAX(created_at) AS last_activity_at
        FROM jobs WHERE organization_id = o.id
    ) j ON TRUE
    ORDER BY j.last_activity_at DESC NULLS LAST, o.created_at DESC;
$$;


-- RPC 2 : Activité par utilisateur (email depuis auth.users, pas profiles)
CREATE OR REPLACE FUNCTION super_admin_user_activity(
    target_org_id UUID DEFAULT NULL,
    row_limit INT DEFAULT 100
)
RETURNS TABLE (
    user_id UUID,
    email TEXT,
    display_name TEXT,
    org_name TEXT,
    deals_created BIGINT,
    sources_uploaded BIGINT,
    chat_messages_sent BIGINT,
    deliverables_generated BIGINT,
    last_active_at TIMESTAMPTZ
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
    SELECT
        p.id AS user_id,
        au.email::TEXT,
        p.display_name,
        o.name AS org_name,
        COALESCE(dc.cnt, 0) AS deals_created,
        COALESCE(su.cnt, 0) AS sources_uploaded,
        COALESCE(cm.cnt, 0) AS chat_messages_sent,
        COALESCE(dg.cnt, 0) AS deliverables_generated,
        GREATEST(dc.last_at, su.last_at, cm.last_at, dg.last_at) AS last_active_at
    FROM organization_members om
    JOIN profiles p ON p.id = om.user_id
    JOIN auth.users au ON au.id = om.user_id
    JOIN organizations o ON o.id = om.organization_id
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS cnt, MAX(created_at) AS last_at
        FROM deals WHERE created_by = om.user_id AND organization_id = om.organization_id
    ) dc ON TRUE
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS cnt, MAX(created_at) AS last_at
        FROM sources WHERE uploaded_by = om.user_id AND organization_id = om.organization_id
    ) su ON TRUE
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS cnt, MAX(cm2.created_at) AS last_at
        FROM chat_messages cm2
        JOIN chat_sessions cs ON cs.id = cm2.session_id
        WHERE cs.user_id = om.user_id AND cm2.role = 'user'
    ) cm ON TRUE
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS cnt, MAX(created_at) AS last_at
        FROM deliverables WHERE generated_by = om.user_id AND organization_id = om.organization_id
    ) dg ON TRUE
    WHERE (target_org_id IS NULL OR om.organization_id = target_org_id)
    ORDER BY last_active_at DESC NULLS LAST
    LIMIT row_limit;
$$;
