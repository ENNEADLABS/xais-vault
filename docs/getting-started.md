# Getting Started — XAIS Vault v2

## Prerequis

- Python 3.12+
- Node.js 22+
- Projet Supabase (PostgreSQL 17)
- Cles API : Anthropic (Claude), Google (Gemini), Tavily
- Compte Stripe (plans payants, optionnel pour dev)

## Installation

### 1. Backend

```bash
# Creer et activer l'environnement virtuel
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Installer les dependances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Remplir .env avec vos cles (voir docs/environment.md)
```

### 2. Frontend

```bash
cd apps/web
npm install
```

### 3. Base de donnees

Executer dans le SQL Editor de Supabase :
1. `supabase/schema.sql` — Tables + indexes + triggers
2. `supabase/rls.sql` — Row-Level Security policies
3. `supabase/storage.sql` — Buckets Storage
Les fonctions RPC sont dans `supabase/migrations/` (appliquees automatiquement par Supabase CLI ou a executer manuellement).

## Lancement

```bash
# Terminal 1 — API
PYTHONPATH=. uvicorn apps.api.app.main:app --reload --port 8000

# Terminal 2 — Worker
PYTHONPATH=. python -m apps.worker.app.main

# Terminal 3 — Frontend
cd apps/web && npm run dev
```

L'application est accessible sur `http://localhost:3000`
L'API est accessible sur `http://localhost:8000/docs` (Swagger)

## Tests

```bash
# Backend (depuis la racine)
pytest -v --tb=short

# Avec couverture
pytest --cov=apps --cov=packages --cov-report=term-missing

# Frontend
cd apps/web && npx vitest run
```

Voir [docs/testing.md](testing.md) pour les details.
