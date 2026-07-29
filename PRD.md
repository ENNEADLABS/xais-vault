# XAIS Vault — Product Requirements Document (PRD)

> Version : 2.2
> Date : 13 mai 2026
> Statut : Pivot généraliste Phases 1+2+3 livrées — voir [docs/roadmap-pivot.md](docs/roadmap-pivot.md) pour Phase 4
> Historique : v1.0 (14 mars 2026) — positionnement PE/VC/M&A exclusif ; v2.0 (alignement post Phase 1) ; v2.1 (alignement post Phase 2) ; v2.2 (alignement post Phase 3, migration DB deals→workspaces + findings→insights + /api/v2/)

---

## 1. Vision produit

**XAIS Vault** est une plateforme d'intelligence documentaire qui aide à comprendre, relier et exploiter des dossiers documentaires complexes — guidée par des agents IA spécialisés avec l'humain dans la boucle.

**En une phrase :** L'utilisateur upload un dossier, l'IA le comprend, l'humain décide quoi approfondir, et le système génère les livrables.

### 1.1 Cas d'usage premium : Due Diligence PE/VC/M&A

Le workflow DD (scan red flags, vérification croisée, deep research, rapports d'investissement) est un cas d'usage premium supporté nativement avec un vocabulaire, des livrables et des agents adaptés. Voir §3.2 (workflow agents) et §3.2 ÉTAPE 4 (livrables).

---

## 2. Utilisateur cible

Cible élargie : tout professionnel qui traite du volume documentaire et a besoin d'extraire de la valeur de ses sources.

| Profil | Usage |
|--------|-------|
| **Chercheur / Doctorant** | Synthèse de littérature, extraction de citations, comparaison cross-papers |
| **Juriste / Avocat** | Analyse de contrats, recherche de clauses, comparaison de versions |
| **Consultant** | Synthèse de rapports clients, benchmark sectoriel, mémo de mission |
| **Journaliste / Investigateur** | Analyse de documents, fact-checking, recherche transverse de sources |
| **Product Manager** | Synthèse de feedback utilisateurs, études de marché, veille concurrentielle |
| **Étudiant** | Synthèse de cours, fiches de révision, exploration thématique |
| **Analyste PE/VC/M&A** *(premium)* | Due diligence, screening de cibles, préparation IC — workflow DD complet |
| **Viewer** | Lecture seule (collaborateurs, clients, validateurs, auditeurs) |

---

## 3. Architecture fonctionnelle

### 3.1 Modèle de données principal

```
Organization (espace de travail — fonds, cabinet, équipe de recherche, rédaction, etc.)
  ├── chat_persona (NULL = généraliste par défaut, "dd" = analyste DD premium)
  └── Members (users avec rôles : admin, analyst, viewer)
       └── Workspaces (table `workspaces`, ex-`deals` — UI "Workspaces" / "Espaces")
            └── Sources (documents uploadés)
            └── Chat Sessions (conversations RAG)
            └── Insights (table `insights`, ex-`findings` — UI "Points clés" FR, "Insights" EN)
            └── Investigations (recherches approfondies, lient un insight optionnel)
            └── Deliverables (livrables générés ; type `dd_report` conservé pour le rapport DD)
            └── Notes (annotations structurées, peuvent linker un insight)
```

Les **clés DB** sont désormais `workspaces`, `insights` (renommées en Phase 3, migration `20260513000000`).
Le type de livrable `dd_report` est conservé (libellé UI = "Rapport complet").
L'API publique est exposée sous `/api/v2/` (l'ancienne `/api/v1/` est supprimée).

### 3.2 Les 3 panneaux

#### Panneau gauche — Sources

Upload et gestion des documents du workspace.

**Types de sources supportés :**

| Format | Extension | Extracteur | Priorité |
|--------|-----------|------------|----------|
| PDF | .pdf | PyMuPDF (fitz) | MVP |
| Word | .docx | python-docx | MVP |
| Excel | .xlsx, .xls, .csv | openpyxl + pandas | MVP |
| PowerPoint | .pptx | python-pptx | MVP |
| Texte | .txt, .md | direct read | MVP |

Pas de YouTube, pas d'URL scraping.

**Cycle de vie d'une source :**

```
Upload → Extraction texte → Embedding (Gemini Embedding 2)
                          → Résumé + Topics (Claude)
                          → Scan léger automatique (Agent Scanner)
                          → Prête
```

**Affichage :** inspiré de Google NotebookLM — chaque source montre un résumé, les topics détectés, et des questions suggérées.

#### Panneau central — Chat

Chat RAG avec les documents du workspace.

**Architecture RAG hybride :**

| Mode | Quand | Comment | LLM |
|------|-------|---------|-----|
| **RAG vectoriel** | Chat quotidien | Gemini Embedding 2 → pgvector → top-k chunks → Claude | Claude |
| **Full context** | Agents DD, livrables | Documents complets injectés dans le context window | Claude |

**Fonctionnalités chat :**
- Questions en langage naturel sur les documents
- Réponses sourcées avec citations pointant vers le document et la page/section
- Sessions de conversation (créer, renommer, supprimer)
- Sauvegarder une réponse en note
- Sauvegarder une réponse comme source (pour la réutiliser dans le chat)
- Persona généraliste par défaut (`general`) — configurable au niveau organisation via Settings → Organisation (depuis Phase 2.B). Persona `dd` disponible pour les workflows PE/VC/M&A. Les orgs existantes au backfill 2026-05-12 ont été migrées vers `dd` pour préserver leur UX.

#### Panneau droit — Agents & Analyse

Workflow de due diligence en 4 étapes avec human-in-the-loop.

**ÉTAPE 1 — Scan automatique**

Déclenché automatiquement quand les sources passent à "prête".

| Élément | Détail |
|---------|--------|
| **Trigger** | Automatique post-indexation |
| **Agent** | Scanner |
| **Input** | Toutes les sources du workspace (full context) |
| **Output** | Liste de insights (red flags, métriques clés, observations) |
| **Affichage** | Dashboard avec insights classés par sévérité + score de confiance |

Chaque insight a :
- Un type (red_flag, metric, observation, missing_info)
- Une sévérité (critical, high, medium, low)
- Un score de confiance (0-100)
- Une citation source (document + page/section)
- Un statut (pending, confirmed, investigating, rejected)

**ÉTAPE 2 — Vérification**

Déclenché manuellement par l'utilisateur pour chaque insight.

| Action utilisateur | Ce qui se passe |
|-------------------|-----------------|
| ✅ Confirmer | Le insight est marqué "confirmed" — il sera inclus dans les livrables |
| 🔍 Approfondir | L'Agent Vérificateur cross-référence entre les documents du workspace |
| ❌ Rejeter | Le insight est marqué "rejected" — exclu des livrables |

L'Agent Vérificateur :
- Compare les données entre les différentes sources (ex: valorisation dans le mémo vs term sheet)
- Détecte les incohérences numériques (ex: CA dans le BP vs comptes certifiés)
- Vérifie la cohérence temporelle (ex: dates, milestones)
- Retourne un verdict enrichi avec les preuves croisées

**ÉTAPE 3 — Deep Research**

Déclenché manuellement par l'utilisateur sur un point spécifique.

| Élément | Détail |
|---------|--------|
| **Trigger** | L'utilisateur sélectionne un insight ou pose une question libre |
| **Agent** | Chercheur |
| **Input** | Le contexte du insight + les documents du workspace + accès web |
| **Capacités web** | Recherche de concurrents, taille de marché, réglementation, brevets, actualités |
| **Output** | Mini-rapport d'investigation avec sources web citées |
| **Affichage** | Rapport inline dans le panneau droit, rattaché au insight |

**ÉTAPE 4 — Génération de livrables**

Déclenché manuellement quand l'utilisateur estime avoir suffisamment d'éléments.

Trois formats de livrables (clés DB internes conservées entre parenthèses) :

| Livrable | Clé DB | Contenu | Format |
|----------|--------|---------|--------|
| **Synthèse** | `executive_summary` | 1-2 pages, synthèse du dossier, métriques clés, points clés | DOCX |
| **Mémo d'analyse** | `investment_memo` | 5-10 pages, argumentaire structuré, risques, recommandation | DOCX |
| **Rapport complet** | `dd_report` | 15-30 pages, analyse complète, tous les insights, recherches, preuves | DOCX |

Les livrables intègrent :
- Les insights confirmés (avec citations sources)
- Les résultats des investigations (avec sources web)
- Les métriques extraites
- Un scoring global du dossier

---

## 4. Multi-tenant & Rôles

### Organizations

| Champ | Détail |
|-------|--------|
| name | Nom du fonds / cabinet |
| slug | URL-friendly (ex: `acme-capital`) |
| plan | starter, team, enterprise |
| stripe_customer_id | Lien Stripe |

### Rôles

| Rôle | Permissions |
|------|-------------|
| **admin** | Tout (gestion membres, billing, settings org) |
| **analyst** | CRUD workspaces, sources, chat, agents, livrables, notes |
| **viewer** | Lecture seule (workspaces, sources, livrables, notes) |

### Isolation des données

- RLS PostgreSQL par `organization_id` sur toutes les tables
- Un user appartient à 1+ organizations
- Un workspace appartient à 1 organization
- Tous les enfants d'un workspace (sources, insights, etc.) héritent de l'organization_id

---

## 5. Billing (Stripe)

| Plan | Prix | Users | Workspaces actifs | Analyses/mois |
|------|------|-------|-------------------|---------------|
| **Starter** | 199€/mois | 1 | 5 | 50 |
| **Premium** | 299€/mois | 1 | 10 | 100 |
| **Team** | 499€/mois | 5 | 20 | 200 |
| **Enterprise** | Sur devis | Illimité | Illimité | Illimité |

- **Workspace** = un workspace d'analyse (équivalent notebook)
- **Analyse** = une requête chat OU une action d'agent OU une génération de livrable
- Dépassement : l'utilisateur est notifié, pas bloqué (facturation overage)
- Free trial : 14 jours Team plan

---

## 6. API Publique & Webhooks

### API Keys
- Format : `xv_live_{32_hex}` (prod) / `xv_test_{32_hex}` (test)
- Stockage : SHA256 en DB
- Scopes : `*`, `read`, `workspaces`, `sources`, `chat`, `agents`, `deliverables`
- Rate limiting : configurable par clé (RPM/RPD), stocké Redis
- Disponible uniquement sur plan Enterprise

### Webhooks
- Événements : `source.ready`, `source.failed`, `scan.completed`, `insight.created`, `investigation.completed`, `deliverable.ready`
- Sécurité : HMAC-SHA256 sur chaque livraison
- Retries : exponentiels (1min, 5min, 30min)
- Dispatch : via le Worker (pas le process API)

---

## 7. Stack technique

| Couche | Technologie |
|--------|-------------|
| **Frontend** | Next.js 16, React 19, TypeScript strict |
| **UI** | Base UI + shadcn/ui, Tailwind CSS 4 |
| **State** | TanStack React Query (serveur) + Zustand (UI) |
| **Backend API** | FastAPI, Python 3.12, Pydantic v2 |
| **Backend Worker** | FastAPI (process séparé), même codebase |
| **DB** | Supabase PostgreSQL 17 (nouveau projet) |
| **Auth** | Supabase Auth, JWT vérifié (PyJWT) |
| **Storage** | Supabase Storage (documents uploadés) |
| **Realtime** | Supabase Realtime (statut sources, progression agents) |
| **LLM texte** | Claude (Anthropic) — analyse, chat, agents, livrables |
| **LLM embeddings** | Gemini Embedding 2 (1536 dims) |
| **Vectoriel** | pgvector (Supabase) |
| **Cache** | Redis (rate limiting en dev — in-memory en prod pour l'instant) |
| **Billing** | Stripe (subscriptions + metered usage) |
| **Hosting API** | Render (2 services : API + Worker) |
| **Hosting frontend** | Vercel |
| **CI/CD** | GitHub Actions |
| **Monitoring** | Sentry (backend + frontend) |
| **Web search** | Tavily |

---

## 8. Features exclues du MVP (conscient et assumé)

| Feature | Raison de l'exclusion |
|---------|----------------------|
| Audio Overviews (TTS) | Faible valeur ajoutée vs effort, à reconsidérer post-validation produit |
| Infographies (image gen) | Faible valeur ajoutée vs effort, à reconsidérer post-validation produit |
| Global Chat (cross-workspaces) | Complexité vs valeur — peut-être post-Phase 4 |
| Research jobs (web) | Remplacé par l'Agent Chercheur intégré au workflow |
| Studio (data tables, slides indépendants) | Remplacé par les livrables (synthèse, mémo, rapport) générés par les agents |
| Templates verticaux pré-configurés | Phase 4 — post-Phase 3 (livré 2026-05-13, migration `deals → workspaces`) |
| YouTube sources | Hors scope MVP, à évaluer post-Phase 4 |
| URL scraping (custom) | Remplacé par la recherche web Tavily des agents |

**Features anciennement exclues, désormais livrées** :
- Knowledge Graph (ForceGraph2D) : livré Phase 1.B (`812ad63`), onglet "Graphe" du Studio avec entités/relations interactives
- Sélecteur de persona chat : livré Phase 2.B (`8b7dd91`), Settings → Organisation
- Admin Dashboard : livré (super-admin overview, org table, summarization panel, graph panel)

---

## 9. Phases de développement

| Phase | Contenu | Durée estimée |
|-------|---------|---------------|
| **0** | Setup repo, CLAUDE.md, schema DB, structure monorepo | 1-2 jours |
| **1** | Fondations : auth, CRUD, job queue, worker, extracteurs | 1 semaine |
| **2** | Chat RAG hybride + streaming SSE | 1 semaine |
| **3** | Agents DD (scanner, vérificateur, chercheur, rédacteur) | 2 semaines |
| **4** | Multi-tenant + billing Stripe | 1 semaine |
| **5** | API publique + webhooks + MCP server | 3-4 jours |
| **6** | Frontend complet | 2 semaines (en parallèle) |
| **7** | Tests, polish, démo, README | 1 semaine |
