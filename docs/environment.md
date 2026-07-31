# Variables d'environnement — XAIS Vault v2

## Backend (obligatoires)

| Variable | Description |
|---|---|
| `SUPABASE_URL` | URL du projet Supabase |
| `SUPABASE_ANON_KEY` | Cle publique Supabase (auth cote client) |
| `SUPABASE_SERVICE_ROLE_KEY` | Cle admin (backend, bypass RLS) |
| `SUPABASE_JWT_SECRET` | Secret pour verification JWT |
| `ANTHROPIC_API_KEY` | Cle API Claude (analyse, chat, agents, livrables) |
| `GOOGLE_API_KEY` | Cle API Google (Gemini Embedding 2) |
| `TAVILY_API_KEY` | Cle API Tavily (recherche web, agent Chercheur) |
| `FRONTEND_URL` | URL du frontend Next.js (CORS) |
| `ENVIRONMENT` | `development` / `staging` / `production` |
| `XAIS_DATABASE_URL` | URL PostgreSQL utilisée uniquement par le script de bootstrap |

## Backend (optionnelles)

| Variable | Description | Defaut |
|---|---|---|
| `SENTRY_DSN` | DSN Sentry pour le monitoring | - |
| `ADMIN_USER_IDS` | UUIDs admin (comma-separated) | - |
| `REDIS_URL` | URL Redis pour rate limiting | `redis://localhost:6379` |
| `STRIPE_SECRET_KEY` | Cle API Stripe (plans payants) | - |
| `STRIPE_WEBHOOK_SECRET` | Secret webhook Stripe (`whsec_...`) | - |
| `STRIPE_PRICE_STARTER` | Price ID Stripe plan Starter | - |
| `STRIPE_PRICE_PREMIUM` | Price ID Stripe plan Premium | - |
| `STRIPE_PRICE_TEAM` | Price ID Stripe plan Team | - |
| `HEALTH_SECRET` | Token pour proteger `/health/detailed` en prod | - |

## Frontend

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | URL Supabase (meme que backend) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Cle publique Supabase |
| `NEXT_PUBLIC_API_URL` | URL de l'API backend |
| `NEXT_PUBLIC_STRIPE_PRICE_STARTER` | Price ID Stripe plan Starter |
| `NEXT_PUBLIC_STRIPE_PRICE_PREMIUM` | Price ID Stripe plan Premium |
| `NEXT_PUBLIC_STRIPE_PRICE_TEAM` | Price ID Stripe plan Team |
| `NEXT_PUBLIC_STRIPE_PRICE_STARTER_YEARLY` | Price ID Stripe plan Starter annuel |
| `NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_YEARLY` | Price ID Stripe plan Premium annuel |
| `NEXT_PUBLIC_STRIPE_PRICE_TEAM_YEARLY` | Price ID Stripe plan Team annuel |
| `NEXT_PUBLIC_SENTRY_DSN` | DSN Sentry pour le monitoring frontend (optionnel) |

## Configuration locale

```bash
supabase start
supabase status
cp .env.example .env
```

Le stack local utilise l'API Supabase `55321`, PostgreSQL `55322`, Studio `55323` et Mailpit `55324`. Reportez les clés `anon`, `service_role` et le secret JWT affichés par `supabase status` dans `.env`. Le fichier racine `.env` est partagé par Docker Compose avec l'API, le worker et le frontend.

Ne réutilisez pas `DATABASE_URL` : le bootstrap lit volontairement `XAIS_DATABASE_URL` afin de ne pas écraser la configuration d'un autre projet.

## Securite

- `.env` est dans `.gitignore` — jamais commite
- Les secrets ne sont jamais hardcodes dans le code
- Les API keys utilisateurs sont hashees en SHA-256 en DB
- Les secrets webhooks sont stockes en clair (necessaire pour signer)
