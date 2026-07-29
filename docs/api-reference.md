# API Reference — XAIS Vault v2

Base URL : `/api/v1`

Auth : Bearer JWT (Supabase) ou API Key (`xv_live_...`)
Header optionnel : `X-Organization-ID` (defaut: `default_organization_id` du profil)

Format de reponse :
```json
{
  "data": { ... },
  "usage": { "input_tokens": 123, "output_tokens": 456, "cost_usd": 0.012, "model_used": "claude-sonnet-4-20250514" },
  "meta": { "job_id": "..." }
}
```

Format d'erreur :
```json
{ "error": { "code": "not_found", "message": "Workspace not found" } }
```

---

## Workspaces

| Methode | Route | Role min | Description |
|---|---|---|---|
| `POST` | `/workspaces/` | analyst | Creer un workspace |
| `GET` | `/workspaces/` | viewer | Lister les workspaces (pagination, filtre status) |
| `GET` | `/workspaces/{workspace_id}` | viewer | Detail d'un workspace |
| `PATCH` | `/workspaces/{workspace_id}` | analyst | Modifier un workspace |
| `DELETE` | `/workspaces/{workspace_id}` | admin | Supprimer un workspace + cascade |
| `POST` | `/workspaces/{workspace_id}/scan` | analyst | Lancer un scan DD (mode: quick/standard/deep) |

## Sources

| Methode | Route | Role min | Description |
|---|---|---|---|
| `POST` | `/sources/` | analyst | Upload fichier (PDF/DOCX/XLSX/PPTX/TXT/MD/CSV) → 202 + job_id |
| `POST` | `/sources/text` | analyst | Ajouter du texte colle → 202 + job_id |
| `GET` | `/sources/` | viewer | Lister les sources d'un workspace |
| `GET` | `/sources/{source_id}` | viewer | Detail + texte extrait |
| `POST` | `/sources/{source_id}/reprocess` | analyst | Re-indexer une source en erreur |
| `DELETE` | `/sources/{source_id}` | analyst | Supprimer source + chunks |

## Insights

| Methode | Route | Role min | Description |
|---|---|---|---|
| `GET` | `/workspaces/{workspace_id}/insights/` | viewer | Lister les insights (type, severity, status) |
| `GET` | `/workspaces/{workspace_id}/insights/{insight_id}` | viewer | Detail d'un insight |
| `PATCH` | `/workspaces/{workspace_id}/insights/{insight_id}` | analyst | Changer le statut (confirm/reject/investigate) |

Actions PATCH :
- `confirm` → status = `confirmed`, reviewed_by = user_id
- `reject` → status = `rejected`, reviewed_by = user_id
- `investigate` → cree un job `verify_insight`, retourne `meta.job_id`

## Investigations

| Methode | Route | Role min | Description |
|---|---|---|---|
| `POST` | `/workspaces/{workspace_id}/investigations/` | analyst | Creer une investigation (question + scope + insight_id) |
| `GET` | `/workspaces/{workspace_id}/investigations/` | viewer | Lister les investigations |
| `GET` | `/workspaces/{workspace_id}/investigations/{id}` | viewer | Detail + rapport + sources web |

## Chat

| Methode | Route | Role min | Description |
|---|---|---|---|
| `POST` | `/workspaces/{workspace_id}/chat/` | analyst | Envoyer un message → SSE stream |
| `GET` | `/workspaces/{workspace_id}/chat/sessions` | viewer | Lister les sessions de chat |
| `GET` | `/workspaces/{workspace_id}/chat/sessions/{session_id}` | viewer | Historique d'une session |
| `PATCH` | `/workspaces/{workspace_id}/chat/sessions/{session_id}` | analyst | Renommer une session |

Le endpoint POST retourne un flux SSE :
```
event: session
data: {"id": "sess-1"}

event: content
data: {"text": "Bonjour"}

event: citations
data: {"citations": [...]}

event: done
data: {}
```

## Deliverables

| Methode | Route | Role min | Description |
|---|---|---|---|
| `GET` | `/workspaces/{workspace_id}/deliverables/` | viewer | Lister les livrables |
| `POST` | `/workspaces/{workspace_id}/deliverables/` | analyst | Generer un livrable → 202 + job_id |
| `GET` | `/workspaces/{workspace_id}/deliverables/{id}` | viewer | Detail + lien de telechargement |

Types : `executive_summary`, `investment_memo`, `dd_report`

## Notes

| Methode | Route | Role min | Description |
|---|---|---|---|
| `GET` | `/workspaces/{workspace_id}/notes/` | viewer | Lister les notes |
| `POST` | `/workspaces/{workspace_id}/notes/` | analyst | Creer une note |
| `PATCH` | `/workspaces/{workspace_id}/notes/{note_id}` | analyst | Modifier une note |
| `DELETE` | `/workspaces/{workspace_id}/notes/{note_id}` | analyst | Supprimer une note |

## API Keys

| Methode | Route | Role min | Description |
|---|---|---|---|
| `POST` | `/api-keys/` | analyst | Creer une cle API (secret retourne UNE fois) |
| `GET` | `/api-keys/` | analyst | Lister les cles (sans secrets) |
| `GET` | `/api-keys/{key_id}` | analyst | Detail + stats d'usage |
| `POST` | `/api-keys/{key_id}/rotate-secret` | analyst | Regener le secret |
| `DELETE` | `/api-keys/{key_id}` | analyst | Supprimer une cle |

## Webhooks

| Methode | Route | Role min | Description |
|---|---|---|---|
| `POST` | `/webhooks/` | admin | Creer un webhook (secret retourne UNE fois) |
| `GET` | `/webhooks/` | admin | Lister les webhooks |
| `GET` | `/webhooks/{id}` | admin | Detail d'un webhook |
| `PATCH` | `/webhooks/{id}` | admin | Modifier URL/events/is_active |
| `DELETE` | `/webhooks/{id}` | admin | Supprimer |
| `POST` | `/webhooks/{id}/rotate-secret` | admin | Regener le secret |
| `GET` | `/webhooks/{id}/deliveries` | admin | Historique des livraisons |
| `POST` | `/webhooks/{id}/test` | admin | Envoyer un event de test |

## Organisation Members

| Methode | Route | Role min | Description |
|---|---|---|---|
| `GET` | `/organizations/{org_id}/members` | viewer | Lister les membres |
| `POST` | `/organizations/{org_id}/members/invite` | admin | Inviter par email |
| `PATCH` | `/organizations/{org_id}/members/{id}` | admin | Changer le role |
| `DELETE` | `/organizations/{org_id}/members/{id}` | admin | Retirer un membre |
| `POST` | `/organizations/{org_id}/members/leave` | viewer | Quitter l'organisation |

## Profile

| Methode | Route | Auth | Description |
|---|---|---|---|
| `GET` | `/profile/` | JWT | Profil courant (auto-creation si absent) |
| `PATCH` | `/profile/` | JWT | Modifier display_name, avatar_url |

## Admin

| Methode | Route | Role min | Description |
|---|---|---|---|
| `GET` | `/admin/usage` | super_admin | Stats d'usage par mois et operation |
| `GET` | `/admin/overview` | super_admin | Vue globale org (membres, workspaces, sources, insights) |
| `GET` | `/admin/api-keys/usage` | super_admin | Stats d'usage des cles API |
| `GET` | `/admin/activity` | super_admin | Journal d'activite recent |

Note : les endpoints admin necessitent un `user_id` present dans `ADMIN_USER_IDS`.

## Billing

| Methode | Route | Role min | Description |
|---|---|---|---|
| `POST` | `/billing/checkout` | admin | Creer une session Stripe Checkout |
| `POST` | `/billing/portal` | admin | Creer un lien vers le portail Stripe |
| `GET` | `/billing/status` | admin | Statut d'abonnement de l'organisation |
| `POST` | `/billing/webhooks/stripe` | - | Webhook Stripe (verifie par signature) |

## Health

| Methode | Route | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | - | Health check basique (status + version) |
| `GET` | `/health/detailed` | `X-Health-Secret` | Health check detaille (latence Supabase, cache JWT) |

Note : `/health/detailed` est protege par le header `X-Health-Secret` en production.
