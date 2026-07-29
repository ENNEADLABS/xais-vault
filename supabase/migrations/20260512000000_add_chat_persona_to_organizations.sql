-- Phase 2.B du pivot généraliste : persona chat par organisation
--
-- - Ajoute `chat_persona` (nullable, default null) sur `organizations`.
--   NULL = persona "general" par défaut (assistant d'analyse documentaire).
--   "dd"  = persona DD historique (analyste PE/VC/M&A).
-- - Migre toutes les organisations existantes vers chat_persona='dd' pour
--   préserver l'expérience des utilisateurs PE/VC actuels. Les nouvelles
--   organisations créées après cette migration auront chat_persona=NULL
--   et donc le persona généraliste par défaut.

alter table public.organizations
  add column if not exists chat_persona text default null;

comment on column public.organizations.chat_persona is
  'Persona système pour le chat RAG. NULL = ''general'' (assistant d''analyse documentaire). Valeurs supportées : ''general'', ''dd''. Voir apps/api/app/services/prompts/chat_personas.py.';

-- Backfill : préserver l'UX des orgs existantes (cadrage DD).
update public.organizations
  set chat_persona = 'dd'
  where chat_persona is null;
