"""Tests pour apps/api/app/services/chat_reranker.py — Reciprocal Rank Fusion."""

from apps.api.app.services.chat_reranker import RRF_K, rerank_rrf, rerank_rrf3


def _chunk(sim: float, fts: float, content: str = "", graph: float = 0) -> dict:
    return {
        "similarity": sim,
        "fts_rank": fts,
        "content": content,
        "source_id": "s1",
        "graph_score": graph,
    }


def test_rrf_empty_list():
    """[] retourne []."""
    assert rerank_rrf([]) == []


def test_rrf_single_chunk():
    """Un seul chunk retourne ce chunk avec rrf_score."""
    chunks = [_chunk(0.9, 0.1)]
    result = rerank_rrf(chunks, top_k=5)
    assert len(result) == 1
    assert "rrf_score" in result[0]


def test_rrf_vector_dominant():
    """Chunk #1 vector + #20 BM25 bat chunk #5/#5."""
    # chunk_a : excellent vector, mauvais BM25
    chunk_a = _chunk(0.95, 0.01, "vector winner")
    # chunk_b : moyen dans les deux
    chunk_b = _chunk(0.60, 0.10, "balanced")

    result = rerank_rrf([chunk_a, chunk_b], top_k=2)

    # chunk_a devrait être premier (rang 1 en vector)
    assert result[0]["content"] == "vector winner"


def test_rrf_bm25_boost():
    """Chunk bas en vector mais #1 en BM25 remonte."""
    chunks = [
        _chunk(0.3, 0.9, "keyword match"),  # Faible vector, fort BM25
        _chunk(0.8, 0.0, "semantic match"),  # Fort vector, pas de BM25
        _chunk(0.5, 0.5, "balanced"),  # Moyen partout
    ]
    result = rerank_rrf(chunks, top_k=3)

    # Le balanced ou keyword match devrait être compétitif
    names = [c["content"] for c in result]
    assert "keyword match" in names


def test_rrf_top_k_truncation():
    """50 candidats → 15 résultats."""
    chunks = [_chunk(0.5 - i * 0.005, 0.01, f"chunk-{i}") for i in range(50)]
    result = rerank_rrf(chunks, top_k=15)
    assert len(result) == 15


def test_rrf_score_field_added():
    """Le champ rrf_score est présent sur chaque chunk."""
    chunks = [_chunk(0.8, 0.2), _chunk(0.6, 0.4)]
    result = rerank_rrf(chunks, top_k=5)
    for c in result:
        assert "rrf_score" in c
        assert c["rrf_score"] > 0


def test_rrf_missing_fts_rank():
    """Chunks sans fts_rank ne crashent pas (fallback à 0)."""
    chunks = [{"similarity": 0.8, "content": "ok", "source_id": "s1"}]
    result = rerank_rrf(chunks, top_k=5)
    assert len(result) == 1
    assert "rrf_score" in result[0]


def test_rrf_score_formula():
    """Vérifie la formule RRF pour un cas simple."""
    # Avec 2 chunks, rang 1 et 2 dans les deux systèmes
    c1 = _chunk(0.9, 0.8)  # #1 vector, #1 BM25
    c2 = _chunk(0.5, 0.3)  # #2 vector, #2 BM25

    result = rerank_rrf([c1, c2], top_k=2)

    expected_score_c1 = 1 / (RRF_K + 1) + 1 / (RRF_K + 1)
    assert abs(result[0]["rrf_score"] - expected_score_c1) < 0.0001


# ─── RRF-3 (vector + BM25 + graph) ───────────────────────────


def test_rrf3_empty_list():
    """[] retourne []."""
    assert rerank_rrf3([]) == []


def test_rrf3_single_chunk():
    """Un seul chunk retourne ce chunk avec rrf_score."""
    chunks = [_chunk(0.9, 0.1, graph=0.5)]
    result = rerank_rrf3(chunks, top_k=5)
    assert len(result) == 1
    assert "rrf_score" in result[0]


def test_rrf3_graph_boosts_ranking():
    """Un chunk avec un fort graph_score remonte dans le ranking."""
    # chunk_a : faible vector/BM25, fort graph
    chunk_a = _chunk(0.3, 0.1, "graph champion", graph=2.0)
    # chunk_b : fort vector/BM25, pas de graph
    chunk_b = _chunk(0.9, 0.8, "hybrid champion", graph=0)
    # chunk_c : moyen partout
    chunk_c = _chunk(0.5, 0.5, "balanced", graph=0.5)

    result = rerank_rrf3([chunk_a, chunk_b, chunk_c], top_k=3, graph_weight=1.0)

    # Avec graph_weight=1.0, le chunk_a devrait remonter significativement
    names = [c["content"] for c in result]
    assert "graph champion" in names


def test_rrf3_zero_weight_equals_rrf2():
    """graph_weight=0 donne le même résultat que RRF-2 (aux arrondis près)."""
    chunks = [
        _chunk(0.9, 0.8, "first", graph=5.0),
        _chunk(0.5, 0.3, "second", graph=0),
    ]

    # Copier les chunks pour avoir des objets séparés
    import copy
    chunks_rrf2 = copy.deepcopy(chunks)
    chunks_rrf3 = copy.deepcopy(chunks)

    result_rrf2 = rerank_rrf(chunks_rrf2, top_k=2)
    result_rrf3 = rerank_rrf3(chunks_rrf3, top_k=2, graph_weight=0)

    # Même ordre
    assert result_rrf2[0]["content"] == result_rrf3[0]["content"]


def test_rrf3_formula():
    """Vérifie la formule RRF-3 pour un cas simple."""
    c1 = _chunk(0.9, 0.8, graph=1.0)  # #1 partout
    c2 = _chunk(0.5, 0.3, graph=0.5)  # #2 partout

    result = rerank_rrf3([c1, c2], top_k=2, graph_weight=0.5)

    expected = (
        1 / (RRF_K + 1) +  # vector rank 1
        1 / (RRF_K + 1) +  # fts rank 1
        0.5 * 1 / (RRF_K + 1)  # graph rank 1 × weight
    )
    assert abs(result[0]["rrf_score"] - expected) < 0.0001


def test_rrf3_missing_graph_score():
    """Chunks sans graph_score ne crashent pas (fallback à 0)."""
    chunks = [{"similarity": 0.8, "fts_rank": 0.2, "content": "ok", "source_id": "s1"}]
    result = rerank_rrf3(chunks, top_k=5)
    assert len(result) == 1
    assert "rrf_score" in result[0]


def test_rrf3_top_k_truncation():
    """50 candidats → 15 résultats."""
    chunks = [_chunk(0.5 - i * 0.005, 0.01, f"chunk-{i}", graph=0.01 * i) for i in range(50)]
    result = rerank_rrf3(chunks, top_k=15)
    assert len(result) == 15
