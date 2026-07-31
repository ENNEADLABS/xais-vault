# Guide utilisateur — XAIS Vault

> Intelligence documentaire pour les professionnels du savoir — chercheurs, juristes, consultants, journalistes, PMs, étudiants et analystes PE/VC/M&A. Uploadez vos documents, l'IA les comprend, vous décidez.

---

## 1. Premiers pas

> Cette version publique n'est pas exploitée comme un service hébergé. Les étapes
> ci-dessous supposent une installation locale ou un déploiement que vous contrôlez.

### Créer un compte

1. Ouvrir l'URL de votre instance XAIS Vault
2. Cliquer **Sign up** — email + mot de passe
3. Confirmer l'email (lien Supabase Auth)
4. Créer votre organisation au premier login (onboarding)

### Inviter des collaborateurs

Settings → Members → **Invite** → entrer l'email et choisir le rôle :

| Rôle | Ce qu'il peut faire |
|---|---|
| `viewer` | Lire les workspaces, insights, historique chat |
| `analyst` | + Créer workspaces, uploader, chatbot, générer livrables |
| `admin` | + Inviter membres, webhooks, supprimer workspaces |

---

## 2. Créer un espace de travail (workspace)

1. Dashboard → **Nouveau Workspace**
2. Renseigner nom + (optionnel) type, secteur, description
3. L'espace apparaît en statut `pending` jusqu'au premier upload

> Le terme "Workspace" est conservé côté DB et API publique pour rétro-compat. Côté UI, vous pouvez considérer un Workspace comme un "espace de travail" ou un "dossier" — qu'il s'agisse d'un dossier d'investissement, d'une revue de contrat, d'une synthèse de littérature ou d'une enquête journalistique.

---

## 3. Uploader des documents

Dans la vue workspace → onglet **Sources** :

- Formats supportés : PDF, DOCX, XLSX, PPTX, TXT, MD, CSV
- Ou coller du texte brut via **Add text**
- Chaque upload déclenche un job d'indexation (extraction → chunking → embedding)
- Statut en temps réel : `pending` → `processing` → `ready` (ou `failed`)

> Attendez que toutes les sources soient `ready` avant de lancer un scan.

---

## 4. Analyser le dossier

Onglet **Points clés** (FR) / **Insights** (EN) → **Lancer l'analyse** :

- L'agent Scanner analyse l'ensemble des sources
- Durée : 30 sec à 3 min selon le volume
- Résultat : points clés catégorisés par type et sévérité (rendus comme "Insights / Points clés" en UI ; les clés internes DB restent `insights`)

### Types de points clés

| Type interne | UI |
|---|---|
| `red_flag` | Alerte critique à examiner (point d'attention, risque, anomalie) |
| `metric` | Chiffre clé / métrique extraite |
| `observation` | Information neutre notable |
| `missing_info` | Donnée manquante / contradiction |

### Actions sur un point clé

- **Confirmer** → valide le point clé (marqué reviewed)
- **Rejeter** → écarte le point clé
- **Investiguer** → déclenche une vérification approfondie (agent Vérificateur)

---

## 5. Chat avec le dossier

Onglet **Chat** :

- Posez n'importe quelle question sur le workspace
- Les réponses incluent des **citations** avec numéro de page et source
- Les sessions sont sauvegardées et renommables
- Utilisable en parallèle du scan

Exemples de questions (selon votre usage) :
- Analyste DD : *"Quel est le chiffre d'affaires 2023 ?"* / *"Compare les marges sur les 3 derniers exercices."*
- Juriste : *"Quelles sont les clauses de non-concurrence ?"* / *"Liste les obligations de confidentialité."*
- Chercheur : *"Quelle méthodologie est utilisée dans le papier de 2024 ?"* / *"Compare les résultats des 3 études."*
- Consultant : *"Synthétise les recommandations des rapports clients."* / *"Quels sont les KPIs récurrents ?"*
- Journaliste : *"Croise les déclarations sur le sujet X entre les 5 sources."* / *"Y a-t-il des contradictions ?"*

### Persona du chat assistant

Le persona par défaut est **généraliste** (assistant d'analyse documentaire). Si vous travaillez majoritairement sur des dossiers PE/VC/M&A, vous pouvez basculer sur le persona **Analyste DD** dans Settings → Organisation → "Persona de l'assistant chat". Le cadrage des réponses s'adapte au profil sélectionné (le format de citation reste identique).

---

## 6. Investigations

Depuis un point clé → **Investiguer**, ou onglet **Investigations** → **Nouvelle investigation** :

- L'agent Chercheur croise le dossier interne avec des sources web (Tavily)
- Produit un mini-rapport avec preuves et verdict
- Durée : 1 à 5 min selon la complexité

---

## 7. Générer un livrable

Onglet **Deliverables** → **Générer** :

| Type interne | UI | Contenu |
|---|---|---|
| `executive_summary` | Synthèse | Synthèse 2-3 pages (board, comité, équipe) |
| `investment_memo` | Mémo d'analyse | Mémo structuré (analyse approfondie, recommandations) |
| `dd_report` | Rapport complet | Rapport complet (cas premium DD : couverture exhaustive ; cas généraliste : version longue avec sections détaillées) |

- Format : DOCX téléchargeable
- Le document reprend les points clés confirmés et les investigations terminées
- Les types internes (clés DB) restent `executive_summary`, `investment_memo`, `dd_report` pour rétro-compat API publique ; seuls les libellés UI sont généralisés

---

## 8. Notes

Onglet **Notes** :

- Notes libres attachées au workspace (markdown)
- Visible par tous les membres
- Non exportées dans les livrables (usage interne)

---

## 9. API programmatique

Settings → **API Keys** → **Créer une clé** :

```bash
curl -H "Authorization: Bearer xv_live_..." \
     http://localhost:8000/api/v2/workspaces/
```

- Le secret est affiché **une seule fois** à la création — le noter immédiatement
- Limites : RPM (requêtes/minute) + RPD (requêtes/jour) selon le plan
- Documentation interactive : `http://localhost:8000/docs` par défaut

---

## 10. Webhooks

Settings → **Webhooks** → **Créer** :

Events disponibles :
- `source.ready` — indexation terminée
- `source.failed` — indexation échouée
- `insight.created` — insight créé par le scan
- `scan.completed` — scan terminé
- `investigation.completed` — investigation terminée
- `deliverable.ready` — livrable prêt

Chaque livraison est signée avec HMAC-SHA256. Vérifier la signature :

```python
import hmac, hashlib

def verify(payload: bytes, secret: str, signature: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## 11. Plans et limites

| Plan | Espaces actifs | Sources/espace | Analyses/mois | Chat |
|---|---|---|---|---|
| Starter (199€/mois) | 5 | 50 | 50 | Inclus |
| Premium (299€/mois) | 10 | 50 | 100 | Inclus |
| Team (499€/mois) | 20 | 50 | 200 | Inclus |
| Enterprise (sur devis) | Illimité | Illimité | Illimité | Illimité |

Upgrade : Settings → **Facturation**.

---

## Besoin d'aide ?

- Documentation technique : [guide de démarrage](getting-started.md)
- API interactive : `/docs` sur l'API
- Support : ce snapshot pédagogique est fourni sans support garanti
