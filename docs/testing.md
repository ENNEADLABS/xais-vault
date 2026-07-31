# Tests — XAIS Vault v2

## Backend (pytest)

```bash
# Depuis la racine du projet
pytest -v --tb=short

# Avec couverture
pytest --cov=apps --cov=packages --cov-report=term-missing

# Un fichier specifique
pytest tests/routers/test_insights.py -v
```

### Structure

```
tests/
├── conftest.py                          → Fixtures partagees globales
├── routers/
│   ├── conftest.py                      → Fixtures partagees (client, auth mocks)
│   ├── test_workspaces.py               → CRUD workspaces
│   ├── test_sources.py                  → Upload + CRUD sources
│   ├── test_insights.py                 → CRUD insights + actions
│   ├── test_chat.py                     → Chat RAG + SSE
│   ├── test_investigations.py           → Investigations
│   ├── test_notes.py                    → CRUD notes
│   ├── test_deliverables.py             → Deliverables (synthese, memo, rapport)
│   ├── test_organizations.py            → CRUD organizations + chat_persona
│   ├── test_organization_members.py     → Membres, invitations, roles
│   ├── test_profile.py                  → Profil utilisateur
│   ├── test_api_keys.py                 → CRUD API keys
│   ├── test_webhooks.py                 → CRUD webhooks + deliveries
│   ├── test_admin.py                    → Admin endpoints
│   ├── test_super_admin.py              → Super-admin platform endpoints
│   └── test_billing.py                  → Billing / Stripe endpoints
├── services/
│   ├── test_auth.py                     → JWT + API key auth
│   ├── test_chat_engine.py              → Moteur de chat (orchestration SSE)
│   ├── test_chat_rag.py                 → Contexte RAG + embedding search
│   ├── test_chat_rag_helpers.py         → Helpers RAG (context block, rerank, fallback)
│   ├── test_chat_graph.py               → Graph search (knowledge graph RAG)
│   ├── test_chat_reranker.py            → RRF / RRF-3 reranking
│   ├── test_chat_history.py             → Historique + summarization
│   ├── test_chat_session.py             → Gestion sessions de chat
│   ├── test_chat_streaming.py           → Streaming SSE + citations
│   ├── test_chat_personas.py            → Personas chat (general / dd) — Phase 2.B
│   ├── test_suggested_questions_service.py → Questions a explorer cross-sources
│   ├── test_entity_extraction.py        → Extraction d'entites (knowledge graph)
│   ├── test_sse.py                      → Helpers SSE
│   ├── test_api_key_service.py          → Logique metier API keys
│   ├── test_api_key_rate_limit.py       → Rate limiting par cle
│   ├── test_plan_limits.py              → Limites par plan
│   ├── test_source_upload.py            → Upload sources
│   ├── test_webhook_service.py          → CRUD webhooks
│   ├── test_webhook_dispatcher.py       → Dispatch HMAC + retries
│   ├── test_chunking.py                 → Decoupage en chunks
│   ├── test_indexing.py                 → Pipeline indexation
│   ├── test_indexing_helpers.py         → Helpers indexation
│   ├── test_docx_builder.py             → Generation DOCX
│   ├── test_admin_stats.py              → Stats admin (overview)
│   ├── test_super_admin_stats.py        → Stats super-admin (platform)
│   └── test_billing.py                  → Logique metier billing / Stripe
├── agents/
│   ├── test_scanner.py                  → Agent Scanner
│   ├── test_scanner_helpers.py          → Helpers Scanner
│   ├── test_verifier.py                 → Agent Verificateur
│   ├── test_verifier_helpers.py         → Helpers Verificateur
│   ├── test_researcher.py               → Agent Chercheur
│   ├── test_researcher_helpers.py       → Helpers Chercheur
│   ├── test_writer.py                   → Agent Redacteur
│   └── test_writer_helpers.py           → Helpers Redacteur
├── middleware/
│   └── test_rate_limit.py               → Rate limiting middleware
├── db/
│   ├── test_job_queue.py                → Job queue operations
│   └── test_cleanup.py                  → Nettoyage des jobs expirés
├── llm/
│   ├── test_claude_provider.py          → Provider Claude
│   ├── test_gemini_embeddings.py        → Provider Gemini Embedding
│   └── test_factory.py                  → Factory LLM
├── workers/
│   ├── test_extractors.py               → Extracteurs (PDF, DOCX, XLSX, PPTX, TXT)
│   └── test_main.py                     → Boucle de polling worker
└── security/
    ├── test_auth_authorization.py       → IDOR : orgs, membres cross-tenant (21 tests)
    ├── test_injection_validation.py     → SSRF, DoS upload/texte, path traversal (26 tests)
    ├── test_infrastructure_config.py    → Security headers, /health, rate limit, RLS (14 tests)
    └── test_business_logic_dos.py       → Source flooding, job poisoning, SSE leak (18 tests)
```

### Tests de sécurité

Les tests dans `tests/security/` couvrent les vulnérabilités OWASP testées lors de l'audit 2026-03-18. Ils tournent avec le même runner (`pytest`) sans configuration spéciale.

```bash
# Tous les tests de sécurité
pytest tests/security/ -v

# Une phase spécifique
pytest tests/security/test_auth_authorization.py -v
```

Chaque fichier correspond à une phase de l'audit :
- **Phase 1** — Auth & IDOR (`test_auth_authorization.py`)
- **Phase 2** — Injection & Validation (`test_injection_validation.py`)
- **Phase 3** — Infrastructure & Config (`test_infrastructure_config.py`)
- **Phase 4** — Business Logic & DoS (`test_business_logic_dos.py`)

### Pattern de test router

```python
# 1. Mock DB avec dependency override
db = MagicMock()
chain = MagicMock()
for m in ("select", "eq", "order"):
    getattr(chain, m).return_value = chain
chain.execute.return_value = MagicMock(data=[...])
db.table.return_value = chain

# 2. Override auth
async def _dep():
    return AuthContext(user_id="...", organization_id="...", role="analyst", auth_method="jwt")

# 3. Injecter
app.dependency_overrides[get_db] = lambda: db
app.dependency_overrides[require_analyst] = _dep

# 4. Tester
r = await client.get("/api/v2/workspaces/")
assert r.status_code == 200

# 5. Cleanup
app.dependency_overrides.clear()
```

### Multi-call DB mock

Pour les endpoints qui font plusieurs requetes DB :
```python
call_count = [0]
def side_effect():
    call_count[0] += 1
    if call_count[0] == 1:
        return MagicMock(data=[{"id": DEAL_ID}])  # workspace check
    return MagicMock(data=[insight])                # actual query
db.table.return_value.execute.side_effect = side_effect
```

## Frontend (Vitest)

```bash
cd apps/web

# Tous les tests
npx vitest run

# Avec couverture
npx vitest run --coverage

# Watch mode
npx vitest

# Un fichier specifique
npx vitest run src/lib/hooks/use-workspaces.test.tsx
```

### Structure

```
apps/web/src/
├── lib/hooks/
│   ├── use-workspaces.test.tsx                        → useWorkspaces + useCreateWorkspace
│   ├── use-workspace.test.tsx                         → useWorkspace (single workspace)
│   ├── use-sources.test.tsx                      → useSources + useUploadSource
│   ├── use-chat.test.tsx                         → useSendMessage, SSE streaming
│   ├── use-chat-messages.test.tsx                → useChatMessages
│   ├── use-chat-sessions.test.tsx                → useChatSessions
│   ├── use-insights.test.tsx                     → useInsights
│   ├── use-investigations.test.tsx               → useInvestigations
│   ├── use-deliverables.test.tsx                 → useDeliverables
│   ├── use-notes.test.tsx                        → useNotes
│   ├── use-organization.test.tsx                 → useOrganization
│   ├── use-profile.test.tsx                      → useProfile
│   ├── use-admin.test.tsx                        → useAdmin
│   ├── use-api-keys.test.tsx                     → useApiKeys
│   ├── use-billing.test.tsx                      → useBilling
│   └── use-login-form.test.tsx                   → useLoginForm
├── components/
│   ├── workspaces/workspace-card.test.tsx                  → WorkspaceCard
│   ├── workspace/insights/insight-card.test.tsx       → InsightCard + actions
│   └── settings/
│       ├── webhooks-tab.test.tsx                 → WebhooksTab
│       ├── webhook-row.test.tsx                  → WebhookRow
│       ├── webhook-deliveries-dialog.test.tsx    → WebhookDeliveriesDialog
│       ├── webhook-secret-dialog.test.tsx        → WebhookSecretDialog
│       ├── create-webhook-dialog.test.tsx        → CreateWebhookDialog
│       └── billing-section.test.tsx              → BillingSection
└── tests/
    ├── setup.ts                                  → Config globale (jsdom, matchers)
    └── render.tsx                                → renderWithProviders() helper
```

### Pattern de test hook

```tsx
function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

const { result } = renderHook(() => useDeals(), { wrapper: createWrapper() });
```

### Simulation SSE

```tsx
function createSSEStream(events: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const event of events) {
        controller.enqueue(encoder.encode(event + "\n"));
      }
      controller.close();
    },
  });
}

function sseLines(event: string, data: Record<string, unknown>): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}`;
}
```

## Couverture

| Scope | Tests | Seuil CI |
|---|---|---|
| Backend (pytest) | 993 tests | 60% |
| Frontend (vitest) | 406 tests, 53 fichiers | - |

### Piège connu

`npx vitest` peut résoudre une version cached (4.1.6) qui ne charge plus jsdom (`ReferenceError: document is not defined` sur tous les tests qui montent un composant). Utiliser le binaire local explicite si la suite échoue mass :

```bash
cd apps/web && ./node_modules/.bin/vitest run
```

## CI

`.github/workflows/ci.yml` :
- Backend : Python 3.12, `pytest` avec `--cov` minimum 60%
- Frontend : Node 22, `npm run build` (validation du build)
