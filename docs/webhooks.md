# Webhooks — XAIS Vault v2

## Configuration

1. Creer un webhook via `POST /api/v2/webhooks/`
2. Le secret HMAC-SHA256 est retourne **une seule fois**
3. Configurer les events a ecouter : `["insight.created", "deliverable.completed"]`

## Payload sortant

```http
POST https://votre-url.com/webhook
Content-Type: application/json
X-Webhook-Signature: <HMAC-SHA256(secret, body)>
X-Webhook-Event: insight.created
User-Agent: XAIS-Vault-Webhook/1.0

{
  "event": "insight.created",
  "timestamp": "2026-03-16T12:00:00Z",
  "data": { ... }
}
```

## Verification (cote client)

```python
import hmac, hashlib

body_bytes = request.body  # bytes bruts
expected = hmac.new(
    secret.encode(),
    body_bytes,
    hashlib.sha256
).hexdigest()
assert hmac.compare_digest(expected, request.headers["X-Webhook-Signature"])
```

## Retry

| Tentative | Delai |
|---|---|
| 1 | Immediat |
| 2 | +1 minute |
| 3 | +5 minutes |

Apres 3 echecs, le `failure_count` du webhook est incremente.
Les deliveries sont tracees dans la table `webhook_deliveries`.

## Events disponibles

| Event | Declencheur |
|---|---|
| `source.ready` | Une source est indexee et prete |
| `source.failed` | L'indexation d'une source a echoue |
| `scan.completed` | Le Scanner a termine l'analyse du workspace |
| `insight.created` | Le Scanner produit un insight |
| `investigation.completed` | Le Chercheur termine une investigation |
| `deliverable.ready` | Le Redacteur termine un livrable DOCX |

## Test

Envoyer un event de test sans affecter les donnees :
```
POST /api/v2/webhooks/{id}/test
```

Retourne un event `test` avec un payload d'exemple.
