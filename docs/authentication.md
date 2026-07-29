# Authentification — XAIS Vault v2

## Flux JWT (utilisateurs)

```
[Browser] → Supabase Auth UI (login/signup)
    ↓
[Supabase] → JWT + refresh token (httpOnly cookie via @supabase/ssr)
    ↓
[Frontend] → Extrait JWT du cookie → Authorization: Bearer <JWT>
    ↓
[API] → Verifie JWT via supabase.auth.get_user(token)
    ↓
[Dependencies] → AuthContext { user_id, organization_id, role, auth_method }
```

## Roles (RBAC)

| Role | Permissions |
|---|---|
| `admin` | Tout (inviter membres, webhooks, supprimer workspaces, etc.) |
| `analyst` | CRUD workspaces/sources/insights, chat, generer livrables, API keys |
| `viewer` | Lecture seule (workspaces, insights, chat history) |

Dependencies FastAPI :
- `require_viewer` → admin, analyst, viewer
- `require_analyst` → admin, analyst
- `require_admin` → admin uniquement
- `authenticate` → JWT valide, pas de contexte org

## Flux API Key (programmatique)

```
Client → Authorization: Bearer xv_live_abc123...
    ↓
[API] → Hash SHA-256 → lookup dans api_keys → rate limit check
    ↓
[Dependencies] → AuthContext { user_id, organization_id, role, auth_method: "api_key" }
```

Restrictions API Key :
- Ne peut PAS gerer les API keys (pas d'auto-privilege-escalation)
- Ne peut PAS gerer les webhooks
- Rate limits : RPM (requests/minute) + RPD (requests/day)
- Secret affiche UNE seule fois a la creation

## Resolution de l'organisation

1. Header `X-Organization-ID` (si fourni)
2. Sinon : `default_organization_id` du profil utilisateur
3. Verification : l'utilisateur doit etre membre de l'organisation
4. Le role est lu depuis `organization_members`

## Defense in depth

- RLS Supabase filtre par `organization_id` au niveau DB
- Le code filtre aussi par `organization_id` dans chaque requete
- Meme si un bug bypass le code, le RLS protege les donnees
