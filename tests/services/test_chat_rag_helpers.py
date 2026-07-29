"""Tests pour apps/api/app/services/chat_rag_helpers.py — merge graph/hybrid."""

from apps.api.app.services.chat_rag_helpers import merge_hybrid_and_graph


def _hybrid_chunk(chunk_id: str, sim: float = 0.8) -> dict:
    return {
        "id": chunk_id,
        "content": f"content-{chunk_id}",
        "source_id": "s1",
        "similarity": sim,
        "fts_rank": 0.1,
    }


def _graph_chunk(chunk_id: str, score: float = 1.0) -> dict:
    return {
        "chunk_id": chunk_id,
        "content": f"content-{chunk_id}",
        "source_id": "s1",
        "page_number": 1,
        "section_title": "Test",
        "graph_score": score,
        "matched_entities": ["Entity A"],
    }


class TestMergeHybridAndGraph:
    def test_no_graph_chunks(self):
        """Sans graph chunks, retourne les hybrid chunks inchangés."""
        hybrid = [_hybrid_chunk("c1"), _hybrid_chunk("c2")]
        merged, added = merge_hybrid_and_graph(hybrid, [])
        assert len(merged) == 2
        assert added == 0

    def test_graph_enriches_existing_chunks(self):
        """Graph score ajouté aux chunks hybrid existants."""
        hybrid = [_hybrid_chunk("c1")]
        graph = [_graph_chunk("c1", score=2.5)]

        merged, added = merge_hybrid_and_graph(hybrid, graph)

        assert len(merged) == 1
        assert added == 0
        assert merged[0]["graph_score"] == 2.5
        assert merged[0]["matched_entities"] == ["Entity A"]

    def test_graph_adds_new_chunks(self):
        """Chunks uniquement dans le graph sont ajoutés."""
        hybrid = [_hybrid_chunk("c1")]
        graph = [_graph_chunk("c1"), _graph_chunk("c2")]

        merged, added = merge_hybrid_and_graph(hybrid, graph)

        assert len(merged) == 2
        assert added == 1
        # Le chunk graph-only a similarity=0 et fts_rank=0
        graph_only = [c for c in merged if c.get("id") == "c2"]
        assert len(graph_only) == 1
        assert graph_only[0]["similarity"] == 0
        assert graph_only[0]["fts_rank"] == 0
        assert graph_only[0]["graph_score"] > 0

    def test_no_duplicates_in_merge(self):
        """Pas de doublons dans la fusion."""
        hybrid = [_hybrid_chunk("c1"), _hybrid_chunk("c2")]
        graph = [_graph_chunk("c1"), _graph_chunk("c2"), _graph_chunk("c3")]

        merged, added = merge_hybrid_and_graph(hybrid, graph)

        ids = [c.get("id") or c.get("chunk_id") for c in merged]
        assert len(ids) == 3
        assert added == 1

    def test_empty_both(self):
        """Deux listes vides → vide."""
        merged, added = merge_hybrid_and_graph([], [])
        assert merged == []
        assert added == 0

    def test_missing_graph_score_defaults_to_zero(self):
        """Hybrid chunks sans graph match ont graph_score = 0."""
        hybrid = [_hybrid_chunk("c1")]
        graph = [_graph_chunk("c2")]

        merged, _ = merge_hybrid_and_graph(hybrid, graph)

        c1 = [c for c in merged if c["id"] == "c1"][0]
        assert c1["graph_score"] == 0
