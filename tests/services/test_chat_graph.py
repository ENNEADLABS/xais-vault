"""Tests pour apps/api/app/services/chat_graph.py."""

import uuid
from unittest.mock import MagicMock

import pytest

from apps.api.app.services.chat_graph import graph_search, has_graph_data

DEAL_ID = str(uuid.uuid4())
FAKE_EMBEDDING = [0.1] * 1536


def _db_with_graph_chunks(chunks: list[dict]) -> MagicMock:
    """DB mock: rpc retourne des chunks graph."""
    db = MagicMock()
    rpc_chain = MagicMock()
    rpc_chain.execute.return_value = MagicMock(data=chunks)
    db.rpc.return_value = rpc_chain
    return db


def _db_with_entity_count(count: int) -> MagicMock:
    """DB mock: entities count retourne count."""
    db = MagicMock()
    chain = MagicMock()
    for m in ("select", "eq", "limit"):
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(count=count)
    db.table.return_value = chain
    return db


# ─── graph_search ─────────────────────────────────────────────


@pytest.mark.asyncio
class TestGraphSearch:
    async def test_returns_chunks_from_rpc(self):
        """Retourne les chunks du RPC search_graph_chunks."""
        chunks = [
            {
                "chunk_id": "c1",
                "content": "Acme détient 60%",
                "source_id": "s1",
                "page_number": 3,
                "section_title": "Capitalistique",
                "graph_score": 1.5,
                "matched_entities": ["Acme SAS"],
            }
        ]
        db = _db_with_graph_chunks(chunks)

        result = await graph_search(
            db, query_embedding=FAKE_EMBEDDING, workspace_id=DEAL_ID,
        )

        assert len(result) == 1
        assert result[0]["graph_score"] == 1.5
        assert "Acme SAS" in result[0]["matched_entities"]

    async def test_empty_graph_returns_empty(self):
        """Graph vide retourne liste vide."""
        db = _db_with_graph_chunks([])
        result = await graph_search(
            db, query_embedding=FAKE_EMBEDDING, workspace_id=DEAL_ID,
        )
        assert result == []

    async def test_rpc_called_with_correct_params(self):
        """RPC est appelée avec les bons paramètres."""
        db = _db_with_graph_chunks([])
        await graph_search(
            db, query_embedding=FAKE_EMBEDDING, workspace_id=DEAL_ID,
        )

        db.rpc.assert_called_once()
        call_args = db.rpc.call_args
        assert call_args[0][0] == "search_graph_chunks"
        params = call_args[0][1]
        assert params["target_workspace_id"] == DEAL_ID
        assert params["query_embedding"] == FAKE_EMBEDDING

    async def test_rpc_error_returns_empty(self):
        """Si le RPC échoue, retourne liste vide (pas de crash)."""
        db = MagicMock()
        db.rpc.side_effect = Exception("RPC timeout")

        result = await graph_search(
            db, query_embedding=FAKE_EMBEDDING, workspace_id=DEAL_ID,
        )
        assert result == []


# ─── has_graph_data ────────────────────────────────────────────


class TestHasGraphData:
    async def test_returns_true_when_entities_exist(self):
        db = _db_with_entity_count(5)
        assert await has_graph_data(db, workspace_id=DEAL_ID) is True

    async def test_returns_false_when_no_entities(self):
        db = _db_with_entity_count(0)
        assert await has_graph_data(db, workspace_id=DEAL_ID) is False

    async def test_returns_false_on_error(self):
        db = MagicMock()
        db.table.side_effect = Exception("DB error")
        assert await has_graph_data(db, workspace_id=DEAL_ID) is False
