-- Phase 3.A — Pivot généraliste : rename deals→workspaces, findings→insights
-- Migration du domaine deals vers le domaine générique workspaces.
--
-- Renames :
--   * tables : deals → workspaces, findings → insights
--   * colonnes FK : deal_id → workspace_id (11 tables enfants),
--     investigations.finding_id → insight_id, notes.linked_finding_id → linked_insight_id
--   * indexes : 14 indexes renommés
--   * constraints FK/CHECK/PK : ~25 contraintes renommées explicitement
--   * RLS policies : 2 policies renommées
--   * RPCs : super_admin_org_metrics, super_admin_platform_overview,
--     super_admin_user_activity recréées avec les nouveaux noms
--
-- ROLLBACK manuel (à exécuter en transaction inverse si besoin) :
--   begin;
--     -- inverser tous les ALTER ci-dessous
--     alter table public.workspaces rename to deals;
--     alter table public.insights rename to findings;
--     -- (etc, inverse complet)
--   commit;

begin;

-- ─── 1. Rename des tables principales ──────────────────────

alter table public.deals rename to workspaces;
alter table public.findings rename to insights;

-- ─── 2. Rename des colonnes FK deal_id → workspace_id ──────

alter table public.agent_traces      rename column deal_id to workspace_id;
alter table public.chat_sessions     rename column deal_id to workspace_id;
alter table public.chunks            rename column deal_id to workspace_id;
alter table public.deliverables      rename column deal_id to workspace_id;
alter table public.entities          rename column deal_id to workspace_id;
alter table public.entity_relations  rename column deal_id to workspace_id;
alter table public.insights          rename column deal_id to workspace_id;
alter table public.investigations    rename column deal_id to workspace_id;
alter table public.notes             rename column deal_id to workspace_id;
alter table public.sources           rename column deal_id to workspace_id;
alter table public.usage_logs        rename column deal_id to workspace_id;

-- ─── 3. Rename des colonnes FK finding_id → insight_id ─────

alter table public.investigations rename column finding_id        to insight_id;
alter table public.notes          rename column linked_finding_id to linked_insight_id;

-- ─── 4. Rename des indexes ─────────────────────────────────

alter index public.deals_pkey                   rename to workspaces_pkey;
alter index public.findings_pkey                rename to insights_pkey;
alter index public.idx_agent_traces_deal        rename to idx_agent_traces_workspace;
alter index public.idx_chat_sessions_deal       rename to idx_chat_sessions_workspace;
alter index public.idx_chunks_deal              rename to idx_chunks_workspace;
alter index public.idx_deals_org                rename to idx_workspaces_org;
alter index public.idx_deliverables_deal        rename to idx_deliverables_workspace;
alter index public.idx_entities_deal            rename to idx_entities_workspace;
alter index public.idx_entity_relations_deal    rename to idx_entity_relations_workspace;
alter index public.idx_findings_deal            rename to idx_insights_workspace;
alter index public.idx_findings_status          rename to idx_insights_status;
alter index public.idx_investigations_deal      rename to idx_investigations_workspace;
alter index public.idx_notes_deal               rename to idx_notes_workspace;
alter index public.idx_sources_deal             rename to idx_sources_workspace;

-- ─── 5. Rename des contraintes (Postgres ne renomme PAS auto) ──

-- workspaces (ex-deals)
alter table public.workspaces rename constraint deals_created_by_fkey       to workspaces_created_by_fkey;
alter table public.workspaces rename constraint deals_organization_id_fkey  to workspaces_organization_id_fkey;
alter table public.workspaces rename constraint deals_deal_type_check       to workspaces_deal_type_check;
alter table public.workspaces rename constraint deals_scan_status_check     to workspaces_scan_status_check;
alter table public.workspaces rename constraint deals_status_check          to workspaces_status_check;

-- insights (ex-findings)
alter table public.insights rename constraint findings_deal_id_fkey            to insights_workspace_id_fkey;
alter table public.insights rename constraint findings_organization_id_fkey   to insights_organization_id_fkey;
alter table public.insights rename constraint findings_reviewed_by_fkey       to insights_reviewed_by_fkey;
alter table public.insights rename constraint findings_source_id_fkey         to insights_source_id_fkey;
alter table public.insights rename constraint findings_confidence_score_check to insights_confidence_score_check;
alter table public.insights rename constraint findings_severity_check         to insights_severity_check;
alter table public.insights rename constraint findings_status_check           to insights_status_check;
alter table public.insights rename constraint findings_type_check             to insights_type_check;

-- Tables enfants
alter table public.agent_traces     rename constraint agent_traces_deal_id_fkey     to agent_traces_workspace_id_fkey;
alter table public.chat_sessions    rename constraint chat_sessions_deal_id_fkey    to chat_sessions_workspace_id_fkey;
alter table public.chunks           rename constraint chunks_deal_id_fkey           to chunks_workspace_id_fkey;
alter table public.deliverables     rename constraint deliverables_deal_id_fkey     to deliverables_workspace_id_fkey;
alter table public.entities         rename constraint entities_deal_id_fkey         to entities_workspace_id_fkey;
alter table public.entity_relations rename constraint entity_relations_deal_id_fkey to entity_relations_workspace_id_fkey;
alter table public.investigations   rename constraint investigations_deal_id_fkey   to investigations_workspace_id_fkey;
alter table public.investigations   rename constraint investigations_finding_id_fkey to investigations_insight_id_fkey;
alter table public.notes            rename constraint notes_deal_id_fkey            to notes_workspace_id_fkey;
alter table public.notes            rename constraint notes_linked_finding_id_fkey  to notes_linked_insight_id_fkey;
alter table public.sources          rename constraint sources_deal_id_fkey          to sources_workspace_id_fkey;
alter table public.usage_logs       rename constraint usage_logs_deal_id_fkey       to usage_logs_workspace_id_fkey;

-- ─── 6. Rename des RLS policies ────────────────────────────

alter policy "Users can view deals in their organizations" on public.workspaces
  rename to "Users can view workspaces in their organizations";

alter policy "Users can access findings in their organizations" on public.insights
  rename to "Users can access insights in their organizations";

-- ─── 7. Recréation des RPCs super_admin ────────────────────
-- Les RPCs référencent les tables/colonnes par leur nom littéral, Postgres ne
-- résout pas la référence automatiquement après rename. On DROP + CREATE.
-- Noms de colonnes retournées également alignés (deal_count → workspace_count,
-- finding_count → insight_count, deals_created → workspaces_created).
-- Le code Python qui consomme ces RPCs (apps/api/app/services/super_admin_stats.py)
-- sera adapté en Phase 3.B.

drop function if exists public.super_admin_org_metrics();
create or replace function public.super_admin_org_metrics()
returns table (
    org_id uuid,
    org_name text,
    plan text,
    member_count bigint,
    workspace_count bigint,
    source_count bigint,
    insight_count bigint,
    deliverable_count bigint,
    chat_message_count bigint,
    last_activity_at timestamp with time zone,
    created_at timestamp with time zone
)
language sql
stable security definer
set search_path to 'public'
as $function$
    SELECT
        o.id AS org_id,
        o.name AS org_name,
        o.plan,
        COALESCE(m.cnt, 0)  AS member_count,
        COALESCE(w.cnt, 0)  AS workspace_count,
        COALESCE(s.cnt, 0)  AS source_count,
        COALESCE(i.cnt, 0)  AS insight_count,
        COALESCE(dl.cnt, 0) AS deliverable_count,
        COALESCE(cm.cnt, 0) AS chat_message_count,
        j.last_activity_at,
        o.created_at
    FROM organizations o
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS cnt FROM organization_members WHERE organization_id = o.id
    ) m ON TRUE
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS cnt FROM workspaces WHERE organization_id = o.id
    ) w ON TRUE
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS cnt FROM sources WHERE organization_id = o.id
    ) s ON TRUE
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS cnt FROM insights WHERE organization_id = o.id
    ) i ON TRUE
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS cnt FROM deliverables WHERE organization_id = o.id
    ) dl ON TRUE
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS cnt
        FROM chat_messages cm2
        JOIN chat_sessions cs ON cs.id = cm2.session_id
        JOIN workspaces w2 ON w2.id = cs.workspace_id
        WHERE w2.organization_id = o.id AND cm2.role = 'user'
    ) cm ON TRUE
    LEFT JOIN LATERAL (
        SELECT MAX(created_at) AS last_activity_at
        FROM jobs WHERE organization_id = o.id
    ) j ON TRUE
    ORDER BY j.last_activity_at DESC NULLS LAST, o.created_at DESC;
$function$;

drop function if exists public.super_admin_platform_overview();
create or replace function public.super_admin_platform_overview()
returns json
language sql
stable security definer
set search_path to 'public'
as $function$
    SELECT json_build_object(
        'total_organizations', (SELECT COUNT(*) FROM organizations),
        'total_workspaces',    (SELECT COUNT(*) FROM workspaces),
        'total_sources',       (SELECT COUNT(*) FROM sources),
        'total_insights',      (SELECT COUNT(*) FROM insights),
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
$function$;

drop function if exists public.super_admin_user_activity(uuid, integer);
create or replace function public.super_admin_user_activity(
    target_org_id uuid DEFAULT NULL::uuid,
    row_limit integer DEFAULT 100
)
returns table (
    user_id uuid,
    email text,
    display_name text,
    org_name text,
    workspaces_created bigint,
    sources_uploaded bigint,
    chat_messages_sent bigint,
    deliverables_generated bigint,
    last_active_at timestamp with time zone
)
language sql
stable security definer
set search_path to 'public'
as $function$
    SELECT
        p.id AS user_id,
        au.email::TEXT,
        p.display_name,
        o.name AS org_name,
        COALESCE(wc.cnt, 0) AS workspaces_created,
        COALESCE(su.cnt, 0) AS sources_uploaded,
        COALESCE(cm.cnt, 0) AS chat_messages_sent,
        COALESCE(dg.cnt, 0) AS deliverables_generated,
        GREATEST(wc.last_at, su.last_at, cm.last_at, dg.last_at) AS last_active_at
    FROM organization_members om
    JOIN profiles p ON p.id = om.user_id
    JOIN auth.users au ON au.id = om.user_id
    JOIN organizations o ON o.id = om.organization_id
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS cnt, MAX(created_at) AS last_at
        FROM workspaces WHERE created_by = om.user_id AND organization_id = om.organization_id
    ) wc ON TRUE
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
$function$;

commit;
