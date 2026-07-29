"""
Script de diagnostic qualité RAG post-normalisation L2.

Vérifie :
1. Distribution des normes L2 des vecteurs en base (doivent être ≈ 1.0)
2. Scores de similarité sur des queries de test
3. Pertinence des résultats (top-K cohérents)

Usage : PYTHONPATH=. python scripts/rag_quality_check.py
"""

import asyncio
import math
import sys

from dotenv import load_dotenv

load_dotenv()

from packages.db.client import get_supabase, safe_get_list
from packages.llm.factory import get_embedder

# ─── Constantes ──────────────────────────────────────────────
SAMPLE_SIZE = 50  # Nombre de chunks à vérifier pour les normes
NORM_TOLERANCE = 0.01  # Tolérance autour de 1.0


def check_l2_norms(db) -> dict:
    """Vérifie que les vecteurs en base sont bien normalisés L2."""
    print("\n══ 1. Vérification des normes L2 ══")

    # Récupérer un échantillon de chunks avec embeddings
    result = (
        db.table("chunks")
        .select("id, embedding, source_id")
        .limit(SAMPLE_SIZE)
        .execute()
    )
    chunks = safe_get_list(result)

    if not chunks:
        print("   ⚠ Aucun chunk trouvé en base")
        return {"status": "empty", "count": 0}

    norms = []
    bad_norms = []

    for chunk in chunks:
        emb = chunk.get("embedding")
        if not emb:
            continue

        # L'embedding peut être une string "[0.1, 0.2, ...]" ou une liste
        if isinstance(emb, str):
            emb = [float(x) for x in emb.strip("[]").split(",")]

        norm = math.sqrt(sum(x * x for x in emb))
        norms.append(norm)

        if abs(norm - 1.0) > NORM_TOLERANCE:
            bad_norms.append({"id": chunk["id"], "norm": norm})

    if not norms:
        print("   ⚠ Aucun embedding trouvé")
        return {"status": "no_embeddings", "count": 0}

    avg_norm = sum(norms) / len(norms)
    min_norm = min(norms)
    max_norm = max(norms)

    print(f"   Échantillon : {len(norms)} vecteurs")
    print(f"   Norme moyenne : {avg_norm:.6f}")
    print(f"   Norme min     : {min_norm:.6f}")
    print(f"   Norme max     : {max_norm:.6f}")

    if bad_norms:
        print(
            f"   ⚠ {len(bad_norms)} vecteurs hors tolérance (|norm - 1.0| > {NORM_TOLERANCE})"
        )
        for b in bad_norms[:5]:
            print(f"     - chunk {b['id'][:8]}... norm={b['norm']:.6f}")
    else:
        print(f"   ✓ Tous les vecteurs dans la tolérance ({NORM_TOLERANCE})")

    return {
        "status": "ok" if not bad_norms else "issues",
        "count": len(norms),
        "avg_norm": avg_norm,
        "min_norm": min_norm,
        "max_norm": max_norm,
        "bad_count": len(bad_norms),
    }


def get_deals_with_chunks(db) -> list[dict]:
    """Liste les deals qui ont des chunks indexés."""
    result = db.rpc("get_deals_with_chunk_count", {}).execute()
    # Fallback si la RPC n'existe pas
    if not result.data:
        # Requête directe
        result = db.table("chunks").select("deal_id").limit(1).execute()
        chunks = safe_get_list(result)
        if chunks:
            deal_id = chunks[0]["deal_id"]
            deal_result = (
                db.table("deals").select("id, name").eq("id", deal_id).execute()
            )
            return safe_get_list(deal_result)
    return safe_get_list(result)


async def test_search_quality(db, deal_id: str, deal_name: str) -> dict:
    """Teste la qualité de recherche sur un deal."""
    print(f"\n══ 2. Test de recherche — Deal: {deal_name} ══")

    embedder = get_embedder()

    # Queries de test génériques pour due diligence
    test_queries = [
        "Quel est le chiffre d'affaires ?",
        "Quels sont les risques identifiés ?",
        "Quelle est la structure de l'actionnariat ?",
        "Résumé de l'activité de l'entreprise",
        "Quelles sont les perspectives de croissance ?",
    ]

    results_summary = []

    for query in test_queries:
        print(f'\n   Query: "{query}"')

        query_embedding = await embedder.embed_query(query, dimensions=1536)

        # Vérifier que le query embedding est normalisé
        q_norm = math.sqrt(sum(x * x for x in query_embedding))
        print(f"   Norme query embedding: {q_norm:.6f}")

        search_result = db.rpc(
            "search_chunks_hybrid",
            {
                "query_embedding": query_embedding,
                "query_text": query,
                "target_workspace_id": deal_id,
                "match_count": 5,
                "similarity_threshold": 0.0,  # Pas de seuil pour voir la distribution
            },
        ).execute()

        chunks = safe_get_list(search_result)

        if not chunks:
            print("   ⚠ Aucun résultat")
            results_summary.append({"query": query, "count": 0, "scores": []})
            continue

        scores = [c.get("similarity", 0) for c in chunks]
        print(f"   Résultats: {len(chunks)} chunks")
        print(f"   Scores: {' | '.join(f'{s:.4f}' for s in scores)}")

        # Aperçu du meilleur résultat
        best = chunks[0]
        content_preview = best.get("content", "")[:150].replace("\n", " ")
        print(f"   Top-1 (sim={scores[0]:.4f}): {content_preview}...")

        results_summary.append(
            {
                "query": query,
                "count": len(chunks),
                "scores": scores,
                "top_score": scores[0] if scores else 0,
            }
        )

    return {"deal": deal_name, "results": results_summary}


def analyze_score_distribution(search_results: dict):
    """Analyse la distribution des scores."""
    print("\n══ 3. Analyse globale ══")

    all_scores = []
    for r in search_results.get("results", []):
        all_scores.extend(r.get("scores", []))

    if not all_scores:
        print("   ⚠ Pas de scores à analyser")
        return

    above_065 = sum(1 for s in all_scores if s >= 0.65)
    above_070 = sum(1 for s in all_scores if s >= 0.70)
    above_080 = sum(1 for s in all_scores if s >= 0.80)

    print(f"   Total scores analysés : {len(all_scores)}")
    print(f"   Moyenne              : {sum(all_scores) / len(all_scores):.4f}")
    print(f"   Min / Max            : {min(all_scores):.4f} / {max(all_scores):.4f}")
    print(
        f"   ≥ 0.65 (seuil RAG)  : {above_065}/{len(all_scores)} ({above_065 / len(all_scores) * 100:.0f}%)"
    )
    print(
        f"   ≥ 0.70              : {above_070}/{len(all_scores)} ({above_070 / len(all_scores) * 100:.0f}%)"
    )
    print(
        f"   ≥ 0.80              : {above_080}/{len(all_scores)} ({above_080 / len(all_scores) * 100:.0f}%)"
    )

    # Verdict
    avg_top = sum(
        r["top_score"] for r in search_results["results"] if r["top_score"] > 0
    ) / max(1, sum(1 for r in search_results["results"] if r["top_score"] > 0))
    print(f"\n   Score moyen top-1    : {avg_top:.4f}")

    if avg_top >= 0.75:
        print("   ✓ VERDICT: Qualité RAG BONNE — les scores post-L2 sont cohérents")
    elif avg_top >= 0.65:
        print(
            "   ~ VERDICT: Qualité RAG ACCEPTABLE — peut être améliorée (chunking, prompts)"
        )
    else:
        print(
            "   ✗ VERDICT: Qualité RAG FAIBLE — investiguer (embeddings, chunking, données)"
        )


async def main():
    print("╔══════════════════════════════════════════════╗")
    print("║   Diagnostic qualité RAG post-L2 normalize  ║")
    print("╚══════════════════════════════════════════════╝")

    db = get_supabase()

    # Étape 1 : Vérifier les normes L2
    check_l2_norms(db)

    # Trouver un deal avec des chunks
    print("\n   Recherche d'un deal avec chunks indexés...")
    chunks_result = db.table("chunks").select("deal_id").limit(1).execute()
    chunks = safe_get_list(chunks_result)

    if not chunks:
        print("   ⚠ Aucun chunk en base — impossible de tester la recherche")
        print("   → Indexer d'abord un document via le worker")
        sys.exit(0)

    deal_id = chunks[0]["deal_id"]
    deal_result = db.table("deals").select("id, name").eq("id", deal_id).execute()
    deals = safe_get_list(deal_result)
    deal_name = deals[0]["name"] if deals else "Inconnu"

    # Compter les chunks du deal
    count_result = (
        db.table("chunks").select("id", count="exact").eq("deal_id", deal_id).execute()
    )
    chunk_count = count_result.count or len(safe_get_list(count_result))
    print(f"   Deal: {deal_name} ({deal_id[:8]}...) — {chunk_count} chunks")

    # Étape 2 : Tester la recherche
    search_results = await test_search_quality(db, deal_id, deal_name)

    # Étape 3 : Analyse globale
    analyze_score_distribution(search_results)

    print("\n══ Fin du diagnostic ══\n")


if __name__ == "__main__":
    asyncio.run(main())
