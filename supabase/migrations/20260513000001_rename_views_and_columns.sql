-- Phase 3.A bis — Rename de la vue deals_with_counts et alignement des alias
--
-- La migration précédente (20260513000000) a renommé les tables mais Postgres
-- a auto-redirigé les vues qui les référencent vers les nouveaux noms de tables.
-- Le nom de la vue lui-même et les alias de colonnes restent à `deals_with_counts`
-- et `finding_count`. On les aligne avec la convention workspaces/insights.

begin;

drop view if exists public.deals_with_counts;

create or replace view public.workspaces_with_counts as
select
    w.id,
    w.organization_id,
    w.created_by,
    w.name,
    w.emoji,
    w.description,
    w.status,
    w.deal_type,
    w.sector,
    w.target_company,
    w.settings,
    w.scan_status,
    w.scan_summary,
    w.created_at,
    w.updated_at,
    coalesce(s.cnt, 0::bigint) as source_count,
    coalesce(i.cnt, 0::bigint) as insight_count
from workspaces w
left join (
    select workspace_id, count(*) as cnt
    from sources
    group by workspace_id
) s on s.workspace_id = w.id
left join (
    select workspace_id, count(*) as cnt
    from insights
    group by workspace_id
) i on i.workspace_id = w.id;

commit;
