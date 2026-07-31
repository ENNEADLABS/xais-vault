# Getting Started — XAIS Vault v2

## Prérequis

- Docker
- Supabase CLI et client PostgreSQL (`psql`)
- Python 3.12 et Node.js 24 / npm 11 pour le développement natif
- Clés API Anthropic, Google et Tavily

## Installation

### Parcours recommandé avec Docker

```bash
supabase start
./scripts/bootstrap-database.sh

cp .env.example .env
# Reporter dans .env les clés affichées par `supabase status`,
# puis renseigner ANTHROPIC_API_KEY, GOOGLE_API_KEY et TAVILY_API_KEY.

docker compose up --build
```

L'application est disponible sur `http://localhost:3000`, l'API sur `http://localhost:8000/docs` et Supabase Studio sur `http://localhost:55323`.

Le script de bootstrap refuse d'écrire dans une base contenant déjà les tables XAIS Vault. Pour recommencer localement, utilisez `supabase db reset`, puis relancez le script.

### Développement natif

```bash
# Backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install --require-hashes -r requirements-dev.txt

# Frontend
cd apps/web
npm ci
```

## Lancement

```bash
# Terminal 1 — API
PYTHONPATH=. uvicorn apps.api.app.main:app --reload --port 8000

# Terminal 2 — Worker
PYTHONPATH=. python -m apps.worker.app.main

# Terminal 3 — Frontend
cd apps/web && npm run dev
```

## Tests

```bash
# Backend (depuis la racine)
pytest -v --tb=short

# Avec couverture
pytest --cov=apps --cov=packages --cov-report=term-missing

# Frontend
cd apps/web && npm test
```

Voir [le guide des tests](testing.md) pour les détails.
