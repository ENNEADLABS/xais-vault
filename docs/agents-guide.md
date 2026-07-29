# Les 4 Agents du Studio — Guide utilisateur

## Vue d'ensemble

```
Upload docs → Scanner → Points clés / Insights → Verifier/Researcher → Writer → DOCX
```

Tout passe par une **job queue asynchrone** : l'API retourne `202 Accepted` immediatement, le Worker poll les jobs toutes les 2 secondes.

> **Note wording** : les agents portent des noms internes stables (Scanner, Verifier, Researcher, Writer) et opèrent sur des entités DB nommées `insights`, `investigations`, `deliverables` — ces clés sont conservées pour rétro-compat API publique. L'UI rend ces entités sous des libellés généralistes ("Points clés" / "Insights", "Synthèse", "Mémo d'analyse", "Rapport complet") depuis la Phase 2 du pivot. Ce guide utilise indifféremment les deux selon le contexte (interne vs user-facing).

---

## 1. Scanner (analyse complete)

**Quand :** Tu cliques le bouton "Analyse" dans le Studio panel (3 modes).

**3 modes :**
- **Rapide** (~2 min) : 4096 tokens, points cles principaux
- **Standard** (~5 min) : 8192 tokens, analyse complete (defaut)
- **Approfondi** (~10 min) : 16384 tokens, cross-verification

**Ce qu'il fait :**
- Charge le texte extrait de **toutes** les sources de l'espace de travail
- Envoie le tout a Claude en une seule passe (JSON mode)
- Extrait des points cles structures (DB: `insights`) : alertes critiques (red_flag), metriques, observations, informations manquantes/contradictions

**Ce que tu vois :** Les points cles apparaissent dans l'onglet "Points cles" / "Insights" avec :
- **Severite** (critical / high / medium / low)
- **Confiance** (0-100%)
- **Citation** exacte du document source
- 3 boutons : Confirmer / Rejeter / Investiguer

**LLM :** Claude, 8192 tokens, temp 0.1, JSON mode

---

## 2. Verifier (cross-reference)

**Quand :** Tu confirmes un point cle → le Verifier passe automatiquement.

**Ce qu'il fait :**
- Prend **1 point cle** + re-lit **toutes** les sources
- Cherche activement des contradictions (pas juste confirmer)
- Rend un verdict : `confirmed` / `contradicted` / `inconclusive` / `nuanced`
- Cite les passages qui soutiennent ou contredisent

**Ce que tu vois :** Le statut du point cle change :
- confirmed → vert
- contradicted → rejete
- inconclusive/nuanced → reste pending

**LLM :** Claude, 4096 tokens, temp 0.1, JSON mode

---

## 3. Researcher (investigation approfondie)

**Quand :** Tu cliques "Investiguer" sur un point cle.

**Ce qu'il fait en 2 phases :**
1. **Recherche documentaire** — recherche semantique dans les chunks (embeddings Gemini + pgvector)
2. **Recherche web** — appel Tavily API pour des sources externes

Puis synthetise le tout en un **rapport Markdown** structure :
- Synthese (reponse directe)
- Analyse documentaire (citations)
- Recherche externe (URLs + sources web)
- Conclusion + recommandations + niveau de confiance

**Ce que tu vois :** Le rapport apparait dans l'onglet Investigations.

**LLM :** Claude, 4096 tokens, temp 0.2, Markdown (pas JSON)

---

## 4. Writer (generation DOCX)

**Quand :** Tu cliques "+ Generer" dans les Livrables.

**3 types disponibles :**

| Cle DB | UI (FR) | UI (EN) | Taille | Max tokens |
|---|---|---|---|---|
| `executive_summary` | Synthèse | Summary | 1-2 pages | 4,096 |
| `investment_memo` | Mémo d'analyse | Analysis Memo | 5-10 pages | 16,384 |
| `dd_report` | Rapport complet | Full Report | 15-30 pages | 32,768 |

Les cles DB sont conservees pour la retro-compat API publique (webhook `deliverable.ready`, route `/api/v2/deliverables`). Seuls les libelles UI sont generalises.

**Ce qu'il fait :**
1. Charge le contexte : espace de travail, points cles confirmes, investigations terminees
2. Genere un Markdown structure via Claude
3. Convertit en DOCX avec cover page, mise en forme, tables
4. Upload le fichier sur Supabase Storage

**Progression visible :** loading_data (5%) → generating_markdown (20%) → building_docx (70%) → uploading (90%) → done (100%)

**Ce que tu vois :** Le livrable avec boutons Apercu + Telecharger.

---

## Le flux complet typique

```
1. Upload PDF/DOCX             → sources indexees (texte + chunks + embeddings + entites du knowledge graph)
2. Lancer l'analyse            → Scanner traite tout → 10-20 points cles
3. Trier les points cles       → Confirmer / Rejeter / Investiguer
4. Investigations              → Researcher creuse chaque point cle investigue
5. Generer une Synthese        → Writer compile points cles + investigations → DOCX 1-2 pages
6. Generer un Rapport complet  → Writer version longue → DOCX 15-30 pages
```

---

## Architecture technique

### Flux de donnees

```
Frontend (Next.js)
  │
  │ HTTP POST → 202 Accepted
  ▼
API (FastAPI)
  │
  │ create_job(type, payload)
  ▼
Job Queue (table Supabase "jobs")
  │  status: pending → claimed → processing → completed/failed
  │
  │ Worker poll toutes les 2s
  ▼
Worker (FastAPI background loop)
  │
  │ Route vers l'agent selon job.type :
  │   index_source          → Indexation (texte, chunks, embeddings)
  │   scan_workspace             → Scanner
  │   verify_insight        → Verifier
  │   investigate           → Researcher
  │   generate_deliverable  → Writer
  ▼
LLM (Claude via packages/llm/)
  │  generate() / stream() / generate_with_tools()
  ▼
Resultats stockes en DB + webhooks emis
```

### Modeles de donnees

**Insights (UI: "Points cles" / "Insights") :**
- type : red_flag, metric, observation, missing_info
- severity : critical, high, medium, low
- confidence_score : 0-100
- status : pending → confirmed / rejected / investigating
- verification : verdict + evidence (JSONB)

**Investigations :**
- question + insight_id (optionnel)
- scope : documents, web, both
- report : contenu Markdown
- doc_references + web_sources (JSONB)

**Deliverables (UI: "Synthese" / "Memo d'analyse" / "Rapport complet") :**
- type : executive_summary, investment_memo, dd_report (cles DB conservees)
- status : pending → processing → completed / failed
- progress_percent : 5 → 100
- content_markdown + file_path + file_size_bytes

### Observabilite

Chaque execution d'agent est tracee dans `agent_traces` :
- tokens in/out, cout USD, duree, modele utilise
- Alimente les stats du super-admin dashboard

### Fichiers cles

| Composant | Chemin |
|---|---|
| Scanner | `apps/worker/app/agents/scanner.py` + `scanner_helpers.py` |
| Verifier | `apps/worker/app/agents/verifier.py` + `verifier_helpers.py` |
| Researcher | `apps/worker/app/agents/researcher.py` + `researcher_helpers.py` |
| Writer | `apps/worker/app/agents/writer.py` + `writer_helpers.py` |
| Prompts | `apps/worker/app/agents/prompts/*.txt` |
| Worker loop | `apps/worker/app/main.py` + `worker_loops.py` |
| Job queue | `packages/db/job_queue.py` |
| LLM abstraction | `packages/llm/` |
| Studio frontend | `apps/web/src/components/workspace/studio-panel.tsx` |
