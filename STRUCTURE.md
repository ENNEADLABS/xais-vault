# Structure du projet XAIS Vault v2

```
xais-vault/
├── CLAUDE.md                        # Instructions pour Claude Code
├── PRD.md                           # Product Requirements Document
├── README.md                        # Vitrine GitHub
├── docker-compose.yml               # Setup local (API + Worker + Redis)
├── render.yaml                      # Config déploiement Render (API + Worker)
│
├── apps/
│   ├── api/                         # FastAPI — Serveur API
│   │   ├── app/
│   │   │   ├── main.py              # Entry point + lifespan + middleware
│   │   │   ├── config.py            # Variables d'environnement
│   │   │   ├── dependencies.py      # Dépendances FastAPI (auth, org, permissions, RBAC)
│   │   │   ├── middleware/
│   │   │   │   └── rate_limit.py    # Rate limiting middleware
│   │   │   ├── routers/
│   │   │   │   ├── workspaces.py         # CRUD workspaces
│   │   │   │   ├── sources.py       # Upload + CRUD sources
│   │   │   │   ├── chat.py          # Chat RAG + streaming SSE
│   │   │   │   ├── insights.py      # CRUD insights + actions (confirm/reject/investigate)
│   │   │   │   ├── investigations.py # Lancer + consulter les deep research
│   │   │   │   ├── deliverables.py  # Générer + télécharger les livrables
│   │   │   │   ├── notes.py         # CRUD notes
│   │   │   │   ├── entities.py      # Knowledge graph entities + relations
│   │   │   │   ├── organizations.py # CRUD organizations (incl. chat_persona)
│   │   │   │   ├── organization_members.py # Membres, invitations, rôles
│   │   │   │   ├── profile.py       # Profil utilisateur courant
│   │   │   │   ├── api_keys.py      # CRUD API keys
│   │   │   │   ├── webhooks.py      # CRUD webhooks + deliveries
│   │   │   │   ├── admin.py         # Admin org-level endpoints (stats, members admin)
│   │   │   │   ├── billing.py       # Stripe checkout, portal, webhooks
│   │   │   │   ├── health.py        # /health endpoint
│   │   │   │   └── super_admin.py   # Dashboard super-admin cross-org (6 endpoints)
│   │   │   ├── models/
│   │   │   │   ├── common.py        # ApiResponse, UsageInfo, PaginatedResponse
│   │   │   │   ├── workspace.py          # WorkspaceCreate, WorkspaceResponse, etc.
│   │   │   │   ├── source.py        # SourceCreate, SourceResponse, etc.
│   │   │   │   ├── chat.py          # ChatMessage, ChatSession, etc.
│   │   │   │   ├── insight.py       # FindingResponse, FindingAction, etc.
│   │   │   │   ├── investigation.py # InvestigationCreate, InvestigationResponse
│   │   │   │   ├── deliverable.py   # DeliverableCreate, DeliverableResponse
│   │   │   │   ├── note.py          # NoteCreate, NoteResponse, etc.
│   │   │   │   ├── organization.py  # OrgCreate, MemberInvite, etc.
│   │   │   │   ├── profile.py       # ProfileResponse, ProfileUpdate
│   │   │   │   ├── api_key.py       # ApiKeyCreate, ApiKeyResponse, etc.
│   │   │   │   ├── webhook.py        # WebhookCreate, WebhookResponse, etc.
│   │   │   │   └── super_admin.py   # PlatformOverview, OrgMetrics, UserActivity, etc.
│   │   │   └── services/
│   │   │       ├── auth.py                  # JWT verification + API key validation (façade)
│   │   │       ├── auth_jwt.py              # JWT decode (PyJWT + SUPABASE_JWT_SECRET)
│   │   │       ├── auth_org.py              # Résolution org + RBAC
│   │   │       ├── chat_rag.py              # Orchestrateur RAG (embedding → search → rerank → prompt)
│   │   │       ├── chat_rag_helpers.py      # build_context_block, merge_hybrid_and_graph, etc.
│   │   │       ├── chat_rag_types.py        # ChatContext, RagMetadata (dataclasses)
│   │   │       ├── chat_graph.py            # Graph search (knowledge graph)
│   │   │       ├── chat_reranker.py         # RRF / RRF-3 reranking
│   │   │       ├── chat_history.py          # Conversation summarization
│   │   │       ├── chat_session.py          # Gestion des sessions de chat
│   │   │       ├── chat_streaming.py        # Streaming SSE + parsing citations
│   │   │       ├── sse.py                   # Helpers SSE (event builder, stream)
│   │   │       ├── suggested_questions_service.py # Questions à explorer cross-sources
│   │   │       ├── source_validators.py     # Validation upload (MIME, taille, etc.)
│   │   │       ├── source_upload.py         # Upload + stockage Supabase Storage
│   │   │       ├── api_key_service.py       # Logique métier API keys
│   │   │       ├── api_key_rate_limit.py    # Rate limiting par clé (RPM/RPD)
│   │   │       ├── plan_limits.py           # Vérification limites par plan
│   │   │       ├── billing.py               # Logique billing (plan ↔ limites)
│   │   │       ├── billing_stripe.py        # Mapping Stripe price_id ↔ plan
│   │   │       ├── billing_webhooks.py      # Handler events Stripe (checkout, subscription)
│   │   │       ├── admin_stats.py           # Stats org-level (overview)
│   │   │       ├── webhook_service.py       # CRUD webhooks + deliveries
│   │   │       ├── super_admin_stats.py     # Stats cross-org (RPCs SQL + agrégation)
│   │   │       └── prompts/
│   │   │           └── chat_personas.py     # GENERAL_PERSONA + DD_PERSONA + get_persona() (Phase 2.B)
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── worker/                      # FastAPI — Worker de jobs
│   │   ├── app/
│   │   │   ├── main.py              # Entry point + polling loop
│   │   │   ├── worker_loops.py      # Boucles de polling (jobs, cleanup)
│   │   │   ├── config.py
│   │   │   ├── job_runner.py        # Dispatcher de jobs par type
│   │   │   ├── prompts/             # Prompts longs externalisés (writer_system, verifier_system, etc.)
│   │   │   ├── agents/
│   │   │   │   ├── scanner.py       # Agent Scanner (red flags, métriques)
│   │   │   │   ├── scanner_helpers.py
│   │   │   │   ├── verifier.py      # Agent Vérificateur (cross-référence)
│   │   │   │   ├── verifier_helpers.py
│   │   │   │   ├── researcher.py    # Agent Chercheur (docs + web)
│   │   │   │   ├── researcher_helpers.py
│   │   │   │   ├── writer.py        # Agent Rédacteur (livrables DOCX)
│   │   │   │   ├── writer_helpers.py
│   │   │   │   └── prompts/         # Prompts systèmes des agents
│   │   │   ├── extractors/
│   │   │   │   ├── pdf.py           # PyMuPDF (fitz)
│   │   │   │   ├── docx.py          # python-docx
│   │   │   │   ├── xlsx.py          # openpyxl + pandas
│   │   │   │   ├── pptx.py          # python-pptx
│   │   │   │   └── text.py          # TXT, MD, CSV
│   │   │   └── services/
│   │   │       ├── indexing.py            # Pipeline: extract → chunk → embed → summarize
│   │   │       ├── indexing_helpers.py
│   │   │       ├── chunking.py            # Découpage intelligent (4000-6000 tokens)
│   │   │       ├── chunking_helpers.py
│   │   │       ├── entity_extraction.py   # Extraction entités LLM (knowledge graph)
│   │   │       ├── entity_extraction_helpers.py
│   │   │       ├── docx_builder.py        # Génération DOCX (livrables)
│   │   │       ├── docx_sections.py       # Sections du document DOCX
│   │   │       ├── docx_styles.py         # Styles du document DOCX
│   │   │       ├── webhook_dispatcher.py  # HMAC-SHA256 + retries
│   │   │       ├── webhook_security.py    # Signature HMAC + verification
│   │   │       └── webhook_trigger.py     # Helpers déclenchement events
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── web/                         # Next.js 16 — Frontend
│       ├── src/
│       │   ├── app/
│       │   │   ├── [locale]/                   # Routing localisé (next-intl) : fr (default), en
│       │   │   │   ├── layout.tsx              # Layout root avec providers
│       │   │   │   ├── page.tsx                # Landing page (publique)
│       │   │   │   ├── (auth)/                 # Login, signup, callback
│       │   │   │   ├── (app)/                  # Routes authentifiées (workspaces list, settings, API keys)
│       │   │   │   ├── (workspace)/                 # Vue workspace (3 panneaux + studio panel)
│       │   │   │   ├── (marketing)/            # Pages marketing additionnelles
│       │   │   │   └── (legal)/                # /terms, /privacy, /legal (publiques depuis fix 3a5245a)
│       │   │   └── proxy.ts                    # Middleware Supabase Auth + locale routing
│       │   ├── components/
│       │   │   ├── ui/              # Base UI + shadcn components + theme-toggle.tsx
│       │   │   ├── layout/          # ThreePanelLayout, Sidebar, Header
│       │   │   ├── workspace/            # Sources, Chat, Insights, Notes, Deliverables
│       │   │   │   ├── source-card.tsx           # Source card expandable
│       │   │   │   ├── source-card-details.tsx   # Détails source (résumé, topics, stats)
│       │   │   │   ├── sources-panel.tsx         # Panneau sources (search, drag&drop)
│       │   │   │   ├── sources-panel-header.tsx  # Header avec stats agrégées
│       │   │   │   ├── sources-panel-collapsed.tsx # Vue collapsed
│       │   │   │   ├── source-upload-dialog.tsx  # Dialog upload
│       │   │   │   ├── chat-panel.tsx            # Panneau chat (orchestrateur)
│       │   │   │   ├── smart-prompts-bar.tsx     # Prompts contextuels
│       │   │   │   ├── chat/                     # Sous-composants chat
│       │   │   │   │   ├── chat-input.tsx        # Input avec @mention
│       │   │   │   │   ├── message-list.tsx      # Liste messages + suggestions
│       │   │   │   │   ├── message-bubble.tsx    # Bulle message + feedback
│       │   │   │   │   ├── citation-badge.tsx    # Badge citation cliquable
│       │   │   │   │   └── focus-source-indicator.tsx # Indicateur mode focus
│       │   │   │   ├── studio-overview.tsx       # Vue Studio (score, risques, timeline)
│       │   │   │   ├── workspace-score.tsx            # Donut chart Workspace Score
│       │   │   │   ├── activity-timeline.tsx     # Timeline activité récente
│       │   │   │   ├── insights/                 # Sous-composants Studio panel
│       │   │   │   │   ├── risk-matrix.tsx       # Matrice de risques
│       │   │   │   │   ├── severity-counters.tsx # Compteurs par sévérité
│       │   │   │   │   ├── scan-tab.tsx          # Onglet "Points clés" / "Insights" (post-Phase 2.C)
│       │   │   │   │   ├── scan-status-header.tsx # Header avec statut scan
│       │   │   │   │   ├── insight-card.tsx      # Card individuelle d'insight
│       │   │   │   │   ├── insight-detail-modal.tsx # Modal détail insight/insight
│       │   │   │   │   ├── insights-toolbar.tsx  # Toolbar filtres + actions
│       │   │   │   │   ├── investigations-tab.tsx # Onglet investigations
│       │   │   │   │   ├── notes-tab.tsx         # Onglet notes
│       │   │   │   │   ├── graph-tab.tsx         # Onglet "Graphe" (Force Graph 2D, Phase 1.B)
│       │   │   │   │   ├── graph-node-detail.tsx # Popup détail entité (bonus UX Phase 1.B)
│       │   │   │   │   └── deliverable-card.tsx  # Card livrable
│       │   │   ├── super-admin/      # Dashboard super-admin (cross-org)
│       │   │   │   ├── dashboard.tsx         # Layout + 3 onglets (Activity/Health/Overview)
│       │   │   │   ├── overview-cards.tsx    # KPIs globaux (grille 2x4)
│       │   │   │   ├── org-table.tsx         # Tableau orgs triable
│       │   │   │   ├── activity-feed.tsx     # Feed chronologique (polling 30s)
│       │   │   │   ├── user-activity-table.tsx # Activité par user + filtre org
│       │   │   │   └── health-panel.tsx      # Jobs failed, taux de succès
│       │   │   ├── settings/
│       │   │   │   ├── settings-tabs.tsx        # Layout tabs Settings
│       │   │   │   ├── profile-tab.tsx          # Onglet Profil utilisateur
│       │   │   │   ├── organization-tab.tsx     # Onglet Organisation + sélecteur persona chat (Phase 2.B)
│       │   │   │   ├── members-list.tsx         # Liste membres
│       │   │   │   ├── invite-member-dialog.tsx # Dialog invitation
│       │   │   │   ├── api-keys-tab.tsx         # Onglet Clés API
│       │   │   │   ├── webhooks-tab.tsx         # Onglet Webhooks
│       │   │   │   ├── webhook-row.tsx          # Row table webhook
│       │   │   │   ├── webhook-deliveries-dialog.tsx
│       │   │   │   ├── webhook-secret-dialog.tsx
│       │   │   │   ├── create-webhook-dialog.tsx
│       │   │   │   ├── billing-section.tsx      # Bloc plan + upgrade
│       │   │   │   ├── danger-zone-tab.tsx      # Suppression org
│       │   │   │   ├── delete-org-dialog.tsx
│       │   │   │   └── admin/                   # Sous-composants admin org
│       │   │   │       └── org-overview.tsx
│       │   │   └── theme-provider.tsx           # next-themes wrapper (light/dark)
│       │   ├── lib/
│       │   │   ├── api.ts           # Client API (fetch wrappers typés)
│       │   │   ├── supabase/        # Client Supabase (auth only)
│       │   │   ├── hooks/           # TanStack Query hooks
│       │   │   │   ├── use-drag-drop.ts      # Hook drag & drop réutilisable
│       │   │   │   └── use-mention-dropdown.ts # Hook @mention pour chat input
│       │   │   └── i18n/            # next-intl config + messages
│       │   ├── stores/              # Zustand stores (UI state)
│       │   │   └── workspace-interaction-store.ts  # Cross-panel interactions (prefill, focus, scroll)
│       │   └── types/               # TypeScript types
│       ├── package.json
│       ├── next.config.ts
│       └── tsconfig.json
│
├── packages/
│   ├── core/                        # Config partagée API + Worker
│   │   ├── config.py                # Variables d'environnement centralisées
│   │   └── agent_schemas.py         # Schemas Pydantic pour les agents
│   │
│   ├── llm/                         # Abstraction LLM
│   │   ├── base.py                  # Protocol LLMProvider
│   │   ├── types.py                 # LLMResponse, LLMUsage, LLMStreamChunk
│   │   ├── claude.py                # Provider Anthropic Claude
│   │   ├── gemini_embeddings.py     # Provider Gemini Embedding 2 (1536 dims)
│   │   ├── response_parser.py       # Parsing réponses structurées
│   │   └── factory.py               # Factory singleton
│   │
│   ├── db/                          # Client DB partagé
│   │   ├── client.py                # Supabase client (service role)
│   │   ├── redis_client.py          # Cache Redis/in-memory avec fallback automatique
│   │   └── job_queue.py             # Job queue PostgreSQL (SKIP LOCKED)
│   │
│   └── mcp-server/                  # MCP Server (Model Context Protocol)
│       └── src/
│           ├── server.py            # Serveur MCP HTTP
│           ├── client.py            # Client API wrapper
│           └── tools.py             # 9 tools exposés (workspaces, sources, chat, etc.)
│
├── supabase/
│   ├── schema.sql                   # Schema initial (24 tables)
│   ├── rls.sql                      # Policies RLS
│   ├── storage.sql                  # Buckets configuration
│   ├── seed.sql                     # Données de démo
│   ├── migrations/                  # Migrations incrémentales (RAG v2/v3, chat_persona, premium plan, etc.)
│   └── rpc/                         # Fonctions SQL (search_chunks_hybrid, graph_search, etc.)
│
├── tests/                           # Tests backend (pytest) — 993 tests
│   ├── conftest.py                  # Fixtures partagées
│   ├── routers/                     # Tests des routers API (12 fichiers)
│   ├── services/                    # Tests des services API + Worker
│   ├── agents/                      # Tests des 4 agents IA (scanner, verifier, researcher, writer)
│   ├── workers/                     # Tests extracteurs + main worker
│   ├── middleware/                  # Tests rate limiting
│   ├── db/                          # Tests job queue + cleanup
│   ├── llm/                         # Tests providers LLM (claude, gemini, factory)
│   └── security/                   # Tests de sécurité OWASP — 79 tests (audit 2026-03-18)
│
├── docs/
│   ├── architecture.md              # Vue d'ensemble + RAG + knowledge graph + agents
│   ├── api-reference.md             # Endpoints REST
│   ├── database.md                  # Schema tables + colonnes
│   ├── authentication.md            # JWT + API keys flow
│   ├── webhooks.md                  # HMAC signing + events
│   ├── testing.md                   # Catalog tests + patterns
│   ├── environment.md               # Variables d'env
│   ├── getting-started.md           # Setup local
│   ├── user-guide.md                # Guide utilisateur
│   ├── agents-guide.md              # Guide technique des 4 agents IA
│   ├── roadmap-pivot.md             # Phases 1+2 livrées, Phase 3 à venir
│   └── security-audit.md            # Rapport d'audit de sécurité (2026-03-18)
│
├── specs/
│   ├── todo/                        # Specs en attente d'exécution
│   ├── done/                        # Specs livrées (Phase 1, Phase 2, etc.)
│   ├── deferred/                    # Specs différées (raison documentée)
│   └── handoffs/                    # Handoffs de session
│
├── scripts/                         # Scripts utilitaires (rag_quality_check.py, etc.)
├── design-reference/                # Captures référence design
├── screenshots/                     # Screenshots produit
│
└── .github/
    └── workflows/
        └── ci.yml                   # CI unique (backend pytest + frontend build)
```
