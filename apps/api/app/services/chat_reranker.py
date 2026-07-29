"""
Reranker léger — Reciprocal Rank Fusion (RRF) sans modèle externe.

Supporte 2 modes :
- RRF-2 : vector + BM25 (hybrid search classique)
- RRF-3 : vector + BM25 + graph (avec knowledge graph)

Remplaçable par un reranker externe (Cohere, Jina) si besoin.
"""

RRF_K = 60  # Constante standard RRF — réduit l'impact des outliers
DEFAULT_GRAPH_WEIGHT = 0.5  # Poids relatif du signal graph


def rerank_rrf(
    chunks: list[dict],
    *,
    top_k: int = 15,
) -> list[dict]:
    """Rerank chunks using Reciprocal Rank Fusion on similarity + fts_rank.

    Chaque chunk doit avoir 'similarity' (vector score) et 'fts_rank' (BM25 score).
    Retourne les top_k chunks re-scorés avec un champ 'rrf_score'.
    """
    if not chunks:
        return []

    # Rangs vector (similarity décroissant)
    by_vector = sorted(chunks, key=lambda c: c.get("similarity", 0), reverse=True)
    vector_rank = {id(c): rank for rank, c in enumerate(by_vector, start=1)}

    # Rangs BM25 (fts_rank décroissant)
    by_fts = sorted(chunks, key=lambda c: c.get("fts_rank", 0), reverse=True)
    fts_rank = {id(c): rank for rank, c in enumerate(by_fts, start=1)}

    # Score RRF = sum(1 / (k + rank_i)) pour chaque système
    for chunk in chunks:
        v_rank = vector_rank[id(chunk)]
        f_rank = fts_rank[id(chunk)]
        chunk["rrf_score"] = 1 / (RRF_K + v_rank) + 1 / (RRF_K + f_rank)

    # Trier par RRF score décroissant et garder top_k
    chunks.sort(key=lambda c: c["rrf_score"], reverse=True)
    return chunks[:top_k]


def rerank_rrf3(
    chunks: list[dict],
    *,
    top_k: int = 15,
    graph_weight: float = DEFAULT_GRAPH_WEIGHT,
) -> list[dict]:
    """Rerank chunks using RRF-3 : vector + BM25 + graph score.

    Chaque chunk doit avoir :
    - 'similarity' (vector score)
    - 'fts_rank' (BM25 score)
    - 'graph_score' (optionnel, 0 si absent du graph search)

    Le graph_weight contrôle l'influence relative du signal graph :
    - 0.0 = ignore le graph (équivalent RRF-2)
    - 0.5 = contribution modérée (défaut)
    - 1.0 = même poids que vector et BM25

    Retourne les top_k chunks re-scorés avec 'rrf_score'.
    """
    if not chunks:
        return []

    # Rangs vector (similarity décroissant)
    by_vector = sorted(chunks, key=lambda c: c.get("similarity", 0), reverse=True)
    vector_rank = {id(c): rank for rank, c in enumerate(by_vector, start=1)}

    # Rangs BM25 (fts_rank décroissant)
    by_fts = sorted(chunks, key=lambda c: c.get("fts_rank", 0), reverse=True)
    fts_rank = {id(c): rank for rank, c in enumerate(by_fts, start=1)}

    # Rangs graph (graph_score décroissant)
    by_graph = sorted(chunks, key=lambda c: c.get("graph_score", 0), reverse=True)
    graph_rank = {id(c): rank for rank, c in enumerate(by_graph, start=1)}

    # Score RRF-3 = 1/(k+v) + 1/(k+f) + weight * 1/(k+g)
    for chunk in chunks:
        v_rank = vector_rank[id(chunk)]
        f_rank = fts_rank[id(chunk)]
        g_rank = graph_rank[id(chunk)]

        rrf_vector = 1 / (RRF_K + v_rank)
        rrf_fts = 1 / (RRF_K + f_rank)
        rrf_graph = graph_weight * (1 / (RRF_K + g_rank))

        chunk["rrf_score"] = rrf_vector + rrf_fts + rrf_graph

    chunks.sort(key=lambda c: c["rrf_score"], reverse=True)
    return chunks[:top_k]
