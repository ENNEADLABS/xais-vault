# MAGIC DOC: Architecture — XAIS Vault v2

> Architecture domain-agnostic : le code (`workspaces`, `insights`, `sources`, etc.) supporte le cas d'usage premium DD PE/VC ainsi que les autres personas listées dans [PRD.md §2](../PRD.md). Le wording user-facing (i18n) est généraliste depuis le pivot Phases 1+2 (livrées 2026-05-12). Le persona du chat assistant est configurable par organisation (`organizations.chat_persona`) — défaut `general`, optionnel `dd`. Voir [roadmap-pivot.md](./roadmap-pivot.md) pour le renommage DB prévu en Phase 3.

## Vue d'ensemble

```
apps/
├── api/          → FastAPI REST API (auth, CRUD, SSE streaming)
├── worker/       → FastAPI worker (jobs: indexation, agents, livrables, webhooks)
└── web/          → Next.js 16 frontend (App Router, i18n)

packages/
├── core/         → Config partagée (variables d'env, agent schemas)
├── llm/          → Abstraction LLM (Protocol + providers Claude/Gemini)
├── db/           → Client Supabase + job queue PostgreSQL
└── mcp-server/   → MCP Server (9 tools pour intégration IA)

supabase/
├── schema.sql    → Schema initial (source de vérité, 24 tables)
├── rls.sql       → Row-Level Security policies
├── storage.sql   → Buckets Storage (sources, deliverables)
├── seed.sql      → Données de démo
├── migrations/   → Migrations incrémentales (RAG v2/v3, chat_persona, premium plan, etc.) — appliquées via `supabase db push --linked`
└── rpc/          → Fonctions SQL (search_chunks_hybrid, graph_search, etc.)
```

## Flux de données

```
[Frontend] --JWT--> [API] --job--> [DB jobs] --poll--> [Worker]
    |                  |                                    |
    |                  +-- CRUD Supabase (service role) ----+
    |                                                       |
    +-- Supabase Realtime <-- UPDATE sources/insights/etc --+
```

1. Le frontend appelle **uniquement** l'API backend (`/api/v2/...`)
2. Le frontend utilise Supabase JS **uniquement** pour l'auth (JWT)
3. L'API crée des jobs en DB pour le travail lourd, retourne 202 Accepted
4. Le Worker poll les jobs toutes les 2s et les exécute
5. Supabase Realtime notifie le frontend quand les données changent

## Multi-tenant

Toutes les tables ont `organization_id`. Le RLS filtre par organisation.
Defense in depth : le code filtre aussi par `organization_id` dans chaque requête.

## RAG (Retrieval-Augmented Generation)

Pipeline chat RAG implémenté dans `apps/api/app/services/chat_*.py` :

```
Question utilisateur
  │
  ├─→ Embedding (Gemini 1536 dims, cache Redis)
  │
  ├─→ Hybrid search (vector cosine + full-text ts_rank, RPC search_chunks_hybrid)
  │    └─→ over-fetch 50 candidats
  │
  ├─→ Graph search (si le workspace a des entités) — RPC graph_search
  │    └─→ traverse chunks ↔ entities ↔ relations
  │
  ├─→ Fusion + reranking
  │    ├─→ RRF (Reciprocal Rank Fusion) si pas de graph
  │    └─→ RRF-3 (3 sources : vector, text, graph) si graph présent
  │
  ├─→ Top-K (15) + filtrage source_ids optionnel + budget tokens (8K)
  │
  └─→ System prompt (persona-dépendant : `general` / `dd`) + history block + context block + query
       └─→ Stream Claude → citations parsing → SSE event stream
```

**Modules** :
- `chat_rag.py` : orchestrateur `prepare_context` (embedding → search → rerank → prompt)
- `chat_rag_helpers.py` : `build_context_block`, `merge_hybrid_and_graph`, `fulltext_fallback`, `build_rag_metadata`
- `chat_graph.py` : `graph_search`, `has_graph_data`
- `chat_reranker.py` : `rerank_rrf`, `rerank_rrf3`
- `chat_history.py` : résumé automatique des conversations > 15 messages (colonnes `chat_sessions.history_summary` + `history_summary_until`)
- `chat_streaming.py` : streaming Claude + parsing citations `[SOURCE:id:page:section:quote]`
- `prompts/chat_personas.py` : 2 personas (`general`, `dd`) avec parité fonctionnelle sur les règles de citation

## Knowledge Graph

Tables `entities`, `entity_relations`, `chunk_entities` (cf. [database.md](./database.md#knowledge-graph)).

**Pipeline d'extraction** (lors de l'indexation d'une source) :
1. `entity_extraction.py` (worker) : LLM scan chaque chunk pour extraire entités (`company`, `person`, `metric`, `clause`, `date`, `amount`) + relations
2. Embedding des entités pour fuzzy matching cross-sources
3. Liens `chunk_entities` (jonction many-to-many)

**Visualisation** : composant `apps/web/src/components/workspace/insights/graph-tab.tsx` (Force Graph 2D, nœuds colorés par type, clic → popup question contextuelle).

**Questions suggérées** : `suggested_questions_service.py` agrège les questions générées par source à l'indexation (déduplication case-insensitive) pour exposer un point d'entrée d'exploration dans le Studio Overview.

## Agents IA

| Agent | Fichiers | LLM | Input | Output |
|---|---|---|---|---|
| Scanner | `scanner.py` + `scanner_helpers.py` | Claude | Sources completes | Insights (red flags, metriques, observations) |
| Verificateur | `verifier.py` + `verifier_helpers.py` | Claude | Insight + sources | Verdict enrichi + preuves croisees |
| Chercheur | `researcher.py` + `researcher_helpers.py` | Claude + Tavily | Question + contexte | Mini-rapport d'investigation |
| Redacteur | `writer.py` + `writer_helpers.py` | Claude | Insights + investigations | Livrable DOCX |

Chaque agent :
- Utilise `packages/llm/` (jamais d'appel SDK direct)
- Enregistre son execution dans `agent_traces` (input, output, tokens, cout, duree)
- Est declenche via la job queue (pas `asyncio.create_task`)

## Job Queue

Table `jobs` avec locking PostgreSQL :
```sql
SELECT ... WHERE status = 'pending' AND locked_until < now()
FOR UPDATE SKIP LOCKED LIMIT 1
```

Types de jobs : `index_source`, `scan_workspace`, `verify_insight`, `investigate`, `generate_deliverable`, `dispatch_webhook`

## Stack technique

| Couche | Technologie |
|---|---|
| Frontend | Next.js 16, TypeScript, Tailwind v4, Base UI + shadcn/ui |
| Etat serveur | TanStack React Query |
| Etat UI | Zustand |
| i18n | next-intl |
| Backend API | FastAPI, Pydantic, Python 3.12 |
| Worker | FastAPI (polling loop) |
| BDD | Supabase PostgreSQL 17 |
| Auth | Supabase Auth (JWT) + API Keys (HMAC) |
| LLM texte | Claude via `packages/llm/` |
| Embeddings | Gemini Embedding 2 (1536 dims) |
| Recherche web | Tavily API |
| Storage | Supabase Storage (S3-compatible) |
| Realtime | Supabase Realtime |
| Rate limiting | Redis (via REDIS_URL) |
| Monitoring | Sentry |
| Hosting backend | Render (API + Worker) |
| Hosting frontend | Vercel |
