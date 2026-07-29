# Roadmap — Pivot généraliste XAIS Vault

> **Vision pivot** : repositionner XAIS Vault d'un outil de Due Diligence PE/VC exclusif vers une plateforme d'intelligence documentaire généraliste, en conservant le workflow DD comme cas d'usage premium.
>
> **Document de plan d'exécution.** La vision produit consolidée se trouve dans [PRD.md](../PRD.md). Ce fichier liste les phases d'évolution, leur statut, et les chantiers techniques associés.

---

## Contexte

L'ossature technique du produit (upload → extraction → chunking → embeddings → RAG hybride → chat + knowledge graph + agents IA) est **domain-agnostic depuis le départ**. Le positionnement initial (PRD v1.0, mars 2026) a sur-spécialisé le produit côté UX/wording vers PE/VC alors que :

- Les personas généralistes (chercheurs, juristes, consultants, journalistes, PM, étudiants) ont les mêmes besoins fondamentaux
- Le marché PE/VC est étroit ; la plateforme technique sert un marché 10-100× plus large
- Les 4 agents IA (Scanner, Vérificateur, Chercheur, Rédacteur) sont applicables au-delà du DD

**Décision pivot** : verbalisée fin de session 040 (mars 2026), implémentée à partir de la session 047 (avril 2026).

---

## Phase 1 — Wording user-facing + UX (LIVRÉ 2026-04-20)

**Commit final** : `812ad63` — merge fast-forward dans main

| Sous-phase | Contenu | Statut |
|---|---|---|
| **1.A** | Rename wording DD → analyse / synthèse / rapport (i18n FR+EN) | ✅ `b0eb1c8` |
| **1.B** | Knowledge graph visuel (react-force-graph-2d) — nouvel onglet Studio | ✅ `812ad63` |
| **1.C** | Questions pré-calculées exposées dans Studio Overview | ✅ `ea308b2` |

**Principes respectés** :
- Clés i18n conservées (`typeDdReport` reste `typeDdReport` ; seules les valeurs changent)
- Clés DB conservées (`findings`, `deals`, `dd_report` côté backend)
- Section `landing._todo` marquée pour Phase 2
- Aucun changement de schema, aucune migration

**Validation** : 1386 tests verts (980 backend + 406 frontend), lint/tsc/eslint clean, build prod OK.

**Spec complète** : [specs/done/01-pivot-generaliste-phase1.md](../specs/done/01-pivot-generaliste-phase1.md)

---

## Phase 2 — Landing + Persona + Renommage `findings` → `insights` UI (LIVRÉ 2026-05-12)

**Commits** : `78cdf29` + `755fbb1` + `a97c0b5` + `8b7dd91` + finitions (`db34789`, `a85a0ee`, `34eb5b6`, `83dce9b`, `3a5245a`)
**Spec exécutée** : [specs/done/01-pivot-generaliste-phase2.md](../specs/done/01-pivot-generaliste-phase2.md)

| Sous-phase | Contenu | Statut |
|---|---|---|
| **2.A** | Landing marketing pivotée (hero, metrics, features, howItWorks, CTA, pricing) | ✅ `78cdf29` |
| **2.B** | Persona chat généraliste par défaut + extraction prompt + migration DB | ✅ `a97c0b5` + `8b7dd91` (sélecteur UI Settings) |
| **2.C** | Rename UI `findings` → `insights/points clés` (FR : "Points clés", EN : "Insights") | ✅ `755fbb1` |

### 2.A — Landing marketing pivotée

Cible : section `landing.*` dans `apps/web/src/messages/{fr,en}.json` (la clé `_todo` Phase 1 a été supprimée).

Livré : hero subtitle reformulé, metrics neutralisées ("Temps gagné sur l'analyse", "Précision des extractions", "Décision plus rapide"), features réécrites pour cible élargie ("Extraction d'éléments clés", "Rapports & synthèses"), pricing parle d'"espaces actifs" / "workspaces" au lieu de "deals actifs". Mention DD premium explicitement conservée dans `pricing.enterprise.description`.

### 2.B — Persona chat généralisé

Livré :
- `apps/api/app/services/prompts/chat_personas.py` : `GENERAL_PERSONA` (default) + `DD_PERSONA` (préservé) + `get_persona(name)` avec fallback
- `ChatContext.system_prompt` désormais positional, résolu via `_load_org_persona` dans `prepare_context`
- Migration `20260512000000_add_chat_persona_to_organizations.sql` : colonne `organizations.chat_persona text default null`, backfill `where chat_persona is null set chat_persona='dd'` pour préserver l'UX des orgs DD historiques
- Sélecteur persona Settings → Organisation (`apps/web/src/components/settings/organization-tab.tsx`), admin-only, 2 options "Généraliste" / "Analyste DD (PE/VC/M&A)"

### 2.C — Rename UI `findings` → `insights/points clés`

Livré : 21 valeurs i18n × 2 langues + 2 strings hardcodées (`deal-page-header.tsx`, `deal-score.tsx`). Clés i18n inchangées, DB et API publique conservées (`finding.created` webhook reste). Fichier `findings-panel.tsx` non renommé (cohérence interne avec table DB `findings`).

### Finitions post-validation (commits supplémentaires)

- `db34789` : `/en` `/fr` landing publiques pour non-loggés (bug proxy Phase 1)
- `a85a0ee` : `auth.branding.description` pivot ("PE/VC/M&A" → "professionnels du savoir")
- `34eb5b6` : `deals.pageLabel` "Deal flow" → "Deals", `subtitle/emptyState` "investment files" → "workspaces"
- `83dce9b` : "red flag" → "alerte" dans `deal-score.tsx`
- `3a5245a` : `/terms`, `/privacy`, `/legal` accessibles publiquement (RGPD)

---

## Phase 3 — Migration DB `deals` → `workspaces` (LIVRÉ 2026-05-13)

**Spec exécutée** : [specs/done/02-pivot-generaliste-phase3.md](../specs/done/02-pivot-generaliste-phase3.md)
**Décision retenue** : **A — Big bang versionné** (pas de dual-mount v1/v2, pas d'usage externe attesté ; cf. handoff 049 sur l'état d'usage)

| Sous-phase | Contenu | Statut |
|---|---|---|
| **3.A** | Migration DB transactionnelle : tables `deals→workspaces`, `findings→insights`, 11 colonnes FK `deal_id→workspace_id`, indexes, contraintes, RLS, 3 RPCs super_admin recréées + vue `workspaces_with_counts` | ✅ `ea4c3d3` + migration `20260513000001` |
| **3.B** | Backend : routers renommés (workspaces.py, insights.py), prefix `/api/v2/`, models Pydantic (`Workspace`, `Insight`, ...), ~80 patterns de tokens compound, 30 fichiers tests | ✅ `d1f1a85` |
| **3.C** | Frontend : 30+ composants renommés (workspace-/insight-), hooks, stores, routes Next `[locale]/(workspace)/workspaces/[workspaceId]`, clés i18n, job types `scan_workspace`/`verify_insight` | ✅ `864233c` |
| **3.D** | MCP server : 9 tools renommés (list_workspaces, list_insights, ...), base URL `/api/v2/`, README, version bumpée 0.1.0→2.0.0 | ✅ |
| **3.E** | Webhook event `finding.created → insight.created`, header `X-Webhook-Version: 2` | ✅ |
| **3.F** | Docs : PRD v2.2, STRUCTURE, architecture, database, api-reference, user-guide, agents-guide, authentication, testing, roadmap-pivot (cette page), webhooks | ✅ |

### Préservé tel quel (intentionnel)

- Column DB `workspaces.deal_type` (valeur technique conservée — domains "equity/debt/ma/restructuring/other")
- `deal_risk_score` (terme scoring agent scanner, transversal aux personas)
- `chat_persona='dd'` (persona DD Phase 2 conservé)
- Type de livrable `dd_report` (clé DB stable, libellé UI = "Rapport complet")

### Validation

- 993 backend tests passing (pytest)
- 406 frontend tests passing (./node_modules/.bin/vitest run)
- 29 MCP tests passing (cd packages/mcp-server && pytest)
- npx tsc --noEmit clean
- npm run build OK

---

## Phase 4 — Templates verticaux premium (POST-PIVOT, à évaluer)

Une fois le pivot consolidé, opportunité commerciale : templates pré-configurés par segment qui customisent le persona chat + les prompts agents + la grille de livrables.

| Template | Persona | Insights pré-configurés | Livrables pré-configurés |
|---|---|---|---|
| **PE/VC DD** *(actuel)* | Analyste financier | Red flags, métriques, valorisation | Executive Summary, Investment Memo, Rapport DD |
| **Legal Review** | Juriste | Clauses risque, contradictions, references | Mémo juridique, Risk Matrix |
| **Research Synthesis** | Chercheur | Méthodologie, sources, citations | Literature Review, Bibliography |
| **Market Intelligence** | PM / Stratège | Concurrents, tendances, segments | Market Brief, Competitive Analysis |
| **Investigation Reporting** | Journaliste | Faits vérifiés, sources, contradictions | Article brief, Source map |

**Modèle économique** : templates inclus dans Team/Enterprise plan, gratuits pour Starter (1 template).

---

## Considérations transversales

### Tests & validation

- **Golden set RAG** : construire un corpus diversifié (PDF académique, contrat juridique, mémo financier, article presse, etc.) pour valider la qualité RAG cross-domain. Risque identifié depuis session 040, encore plus critique post-pivot.
- **Tests E2E** : au moins 1 parcours par persona prioritaire dans `apps/web/tests/`

### Communication externe

- **Pas de breaking côté API publique avant Phase 3** : les clés `dd_report`, `investment_memo`, `executive_summary` restent valides
- **Webhooks events** : aucun changement avant Phase 3
- **MCP server tools** : aucun changement avant Phase 3

### Cohérence doc

- Le **PRD** est la source de vérité produit (consolidée post-pivot)
- Ce **roadmap-pivot.md** est le plan d'exécution
- L'**architecture.md** est domain-agnostic et stable
- Les **handoffs/** documentent les sessions de pivot (047, à venir)
