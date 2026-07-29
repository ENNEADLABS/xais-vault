# CLAUDE.md — XAIS Vault v2

Référence : `PRD.md` (vision+scope), `STRUCTURE.md` (structure détaillée), `docs/` (technique).
Conventions détaillées → `.claude/rules/` (path-scopés, auto-chargés).

## Feature flags
- `AUTO_SCAN_ENABLED` (default: `false`) — `true` déclenche le scan DD auto quand sources prêtes. OFF en Studio v2 (lancement manuel).

## Commandes
- **API** : `PYTHONPATH=. uvicorn apps.api.app.main:app --reload --port 8000`
- **Worker** : `PYTHONPATH=. python -m apps.worker.app.main`
- **Web** : `cd apps/web && npm run dev`
- **Tests backend** : `pytest -v --tb=short` | coverage : `--cov=apps --cov=packages`
- **Tests frontend** : `cd apps/web && npm test`
- **Lint** : `ruff check .`

## Conventions (non-obvious)
- Tables/colonnes DB : `snake_case` (+ pluriel pour tables)
- Schemas Pydantic : `PascalCase` (`DealCreate`, `FindingResponse`)
- Env vars : `UPPER_SNAKE_CASE`

## Rules projet
- Frontend → API backend (`/api/v1/...`) uniquement ; Supabase JS côté client seulement pour l'auth JWT
- API ne fait pas de travail lourd → crée un job en DB, retourne 202
- CI IA review actif sur chaque PR (`.github/workflows/claude-review.yml`) — requiert `ANTHROPIC_API_KEY`

## Deploy
- API + Worker : Render | Frontend : Vercel | Branche : main
- URL prod API : https://xais-vault-api.onrender.com/health
- URL prod Web : https://xais-vault.vercel.app
- Validation prod (bloquante) : `pytest`, `npx tsc --noEmit` (apps/web), `npx vitest run` (apps/web)
