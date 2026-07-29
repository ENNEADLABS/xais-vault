"""
Tests for apps/api/app/services/chat_rag.py

DB and embedder are mocked. Tests prepare_context pipeline.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.app.services.chat_rag import (
    FETCH_COUNT,
    SIMILARITY_THRESHOLD,
    prepare_context,
)
from apps.api.app.services.chat_rag_helpers import (
    build_rag_metadata as _build_rag_metadata,
)

DEAL_ID = str(uuid.uuid4())
ORG_ID = str(uuid.uuid4())
SESSION_ID = str(uuid.uuid4())
SOURCE_ID = str(uuid.uuid4())
FAKE_EMBEDDING = [0.1] * 1536


def _make_chunk(**overrides) -> dict:
    base = {
        "source_id": SOURCE_ID,
        "content": "Contenu du chunk de test.",
        "page_number": 3,
        "section_title": "Financials",
        "similarity": 0.82,
    }
    return {**base, **overrides}


def _db_with_chunks(chunks: list[dict], sources: list[dict] | None = None) -> MagicMock:
    """DB mock: rpc returns chunks, table("sources") returns sources."""
    db = MagicMock()
    sources = sources or [{"id": SOURCE_ID, "name": "Memo.pdf"}]

    rpc_chain = MagicMock()
    rpc_chain.execute.return_value = MagicMock(data=chunks)
    db.rpc.return_value = rpc_chain

    sources_chain = MagicMock()
    for m in ("select", "in_", "eq"):
        getattr(sources_chain, m).return_value = sources_chain
    sources_chain.execute.return_value = MagicMock(data=sources)
    db.table.return_value = sources_chain

    return db



# ─── prepare_context ────────────────────────────────────────────


@pytest.mark.asyncio
class TestPrepareContext:
    @pytest.fixture(autouse=True)
    def _no_graph(self):
        """Désactive le knowledge graph dans les tests existants."""
        with patch(
            "apps.api.app.services.chat_rag.has_graph_data",
            new_callable=AsyncMock,
            return_value=False,
        ):
            yield
    async def test_returns_chat_context_with_chunks(self):
        """Returns ChatContext with chunks and source_map populated."""
        mock_embedder = AsyncMock()
        mock_embedder.embed_query.return_value = FAKE_EMBEDDING

        chunk = _make_chunk()
        db = _db_with_chunks([chunk])

        with patch(
            "apps.api.app.services.chat_rag.get_embedder", return_value=mock_embedder
        ):
            ctx = await prepare_context(
                db,
                query="Quelle est la valorisation ?",
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
            )

        assert len(ctx.chunks) == 1
        assert SOURCE_ID in ctx.source_map
        assert ctx.source_map[SOURCE_ID] == "Memo.pdf"

    async def test_prompt_contains_chunk_content(self):
        """The built prompt includes chunk content."""
        mock_embedder = AsyncMock()
        mock_embedder.embed_query.return_value = FAKE_EMBEDDING

        chunk = _make_chunk(content="ARR 2024 : 8M€")
        db = _db_with_chunks([chunk])

        with patch(
            "apps.api.app.services.chat_rag.get_embedder", return_value=mock_embedder
        ):
            ctx = await prepare_context(
                db,
                query="ARR ?",
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
            )

        assert "ARR 2024 : 8M€" in ctx.prompt

    async def test_no_chunks_returns_fallback_message(self):
        """When no chunks found, prompt contains fallback 'aucun document' message."""
        mock_embedder = AsyncMock()
        mock_embedder.embed_query.return_value = FAKE_EMBEDDING

        db = _db_with_chunks([])

        with patch(
            "apps.api.app.services.chat_rag.get_embedder", return_value=mock_embedder
        ):
            ctx = await prepare_context(
                db,
                query="Quelle est la valorisation ?",
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
            )

        assert ctx.chunks == []
        assert "Aucun document pertinent" in ctx.prompt

    async def test_context_truncated_at_budget(self):
        """Many chunks exceeding token budget → later chunks excluded."""
        mock_embedder = AsyncMock()
        mock_embedder.embed_query.return_value = FAKE_EMBEDDING

        # 10 chunks de 1000 tokens chacun (4000 chars) — dépasse le budget 8K
        chunks = []
        for i in range(10):
            sid = str(uuid.uuid4())
            chunks.append(
                _make_chunk(
                    content=f"Chunk {i}. " + "x" * 4000,
                    source_id=sid,
                )
            )
        last_chunk_content = "Ce chunk doit être exclu. " + "z" * 4000
        last_sid = str(uuid.uuid4())
        chunks.append(_make_chunk(content=last_chunk_content, source_id=last_sid))

        sources = [
            {"id": c["source_id"], "name": f"doc-{i}.pdf"} for i, c in enumerate(chunks)
        ]
        db = _db_with_chunks(chunks, sources=sources)

        with patch(
            "apps.api.app.services.chat_rag.get_embedder", return_value=mock_embedder
        ):
            ctx = await prepare_context(
                db,
                query="Test",
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
            )

        # Le dernier chunk ne devrait pas être dans le prompt (budget dépassé)
        assert "Ce chunk doit être exclu." not in ctx.prompt

    async def test_history_included_when_session_provided(self):
        """When session_id given, conversation history appears in prompt."""
        mock_embedder = AsyncMock()
        mock_embedder.embed_query.return_value = FAKE_EMBEDDING

        chunk = _make_chunk()
        db = _db_with_chunks([chunk])

        with (
            patch(
                "apps.api.app.services.chat_rag.get_embedder",
                return_value=mock_embedder,
            ),
            patch(
                "apps.api.app.services.chat_history.build_history_block",
                new_callable=AsyncMock,
                return_value="HISTORIQUE DE LA CONVERSATION :\nUtilisateur: Question précédente\n\n---\n\n",
            ),
        ):
            ctx = await prepare_context(
                db,
                query="Suite de la question",
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
                session_id=SESSION_ID,
            )

        assert "HISTORIQUE" in ctx.prompt
        assert "Question précédente" in ctx.prompt

    async def test_embedder_called_with_query(self):
        """Embedder is called with the user query."""
        mock_embedder = AsyncMock()
        mock_embedder.embed_query.return_value = FAKE_EMBEDDING
        db = _db_with_chunks([])

        with patch(
            "apps.api.app.services.chat_rag.get_embedder", return_value=mock_embedder
        ):
            await prepare_context(
                db,
                query="Ma question",
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
            )

        mock_embedder.embed_query.assert_awaited_once_with(
            "Ma question", dimensions=1536
        )

    async def test_rpc_called_with_correct_params(self):
        """search_chunks_hybrid RPC is called with workspace_id and correct params."""
        mock_embedder = AsyncMock()
        mock_embedder.embed_query.return_value = FAKE_EMBEDDING
        db = _db_with_chunks([])

        with patch(
            "apps.api.app.services.chat_rag.get_embedder", return_value=mock_embedder
        ):
            await prepare_context(
                db,
                query="Question",
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
            )

        # Premier appel = search_chunks_hybrid
        first_call = db.rpc.call_args_list[0]
        assert first_call[0][0] == "search_chunks_hybrid"
        params = first_call[0][1]
        assert params["target_workspace_id"] == DEAL_ID
        assert params["match_count"] == FETCH_COUNT
        assert params["similarity_threshold"] == SIMILARITY_THRESHOLD
        assert params["query_text"] == "Question"

    async def test_source_ids_filter_chunks(self):
        """source_ids fourni → seuls les chunks de ces sources sont gardés."""
        mock_embedder = AsyncMock()
        mock_embedder.embed_query.return_value = FAKE_EMBEDDING

        other_id = str(uuid.uuid4())
        c1 = _make_chunk(source_id=SOURCE_ID, content="Chunk gardé")
        c2 = _make_chunk(source_id=other_id, content="Chunk filtré")
        db = _db_with_chunks([c1, c2])

        with patch(
            "apps.api.app.services.chat_rag.get_embedder", return_value=mock_embedder
        ):
            ctx = await prepare_context(
                db,
                query="Test",
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
                source_ids=[SOURCE_ID],
            )

        assert len(ctx.chunks) == 1
        assert ctx.chunks[0]["source_id"] == SOURCE_ID
        assert "Chunk gardé" in ctx.prompt
        assert "Chunk filtré" not in ctx.prompt

    async def test_source_ids_none_keeps_all_chunks(self):
        """Sans source_ids, tous les chunks sont gardés."""
        mock_embedder = AsyncMock()
        mock_embedder.embed_query.return_value = FAKE_EMBEDDING

        other_id = str(uuid.uuid4())
        c1 = _make_chunk(source_id=SOURCE_ID)
        c2 = _make_chunk(source_id=other_id)
        sources = [
            {"id": SOURCE_ID, "name": "A.pdf"},
            {"id": other_id, "name": "B.pdf"},
        ]
        db = _db_with_chunks([c1, c2], sources=sources)

        with patch(
            "apps.api.app.services.chat_rag.get_embedder", return_value=mock_embedder
        ):
            ctx = await prepare_context(
                db,
                query="Test",
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
            )

        assert len(ctx.chunks) == 2

    async def test_rag_metadata_populated(self):
        """rag_metadata est correctement calculé."""
        mock_embedder = AsyncMock()
        mock_embedder.embed_query.return_value = FAKE_EMBEDDING

        other_id = str(uuid.uuid4())
        c1 = _make_chunk(source_id=SOURCE_ID, similarity=0.9)
        c2 = _make_chunk(source_id=SOURCE_ID, similarity=0.8)
        c3 = _make_chunk(source_id=other_id, similarity=0.7)
        sources = [
            {"id": SOURCE_ID, "name": "A.pdf"},
            {"id": other_id, "name": "B.pdf"},
        ]
        db = _db_with_chunks([c1, c2, c3], sources=sources)

        with patch(
            "apps.api.app.services.chat_rag.get_embedder", return_value=mock_embedder
        ):
            ctx = await prepare_context(
                db,
                query="Test",
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
            )

        meta = ctx.rag_metadata
        assert meta is not None
        assert meta.chunk_count == 3
        assert meta.source_count == 2
        assert meta.avg_similarity == round((0.9 + 0.8 + 0.7) / 3, 3)
        assert len(meta.sources_used) == 2

    async def test_rag_metadata_empty_chunks(self):
        """Sans chunks, rag_metadata est vide."""
        mock_embedder = AsyncMock()
        mock_embedder.embed_query.return_value = FAKE_EMBEDDING

        db = _db_with_chunks([])

        with patch(
            "apps.api.app.services.chat_rag.get_embedder", return_value=mock_embedder
        ):
            ctx = await prepare_context(
                db,
                query="Test",
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
            )

        meta = ctx.rag_metadata
        assert meta is not None
        assert meta.chunk_count == 0
        assert meta.source_count == 0
        assert meta.sources_used == []


# ─── _build_rag_metadata ──────────────────────────────────────────


class TestBuildRagMetadata:
    def test_empty_chunks_returns_zero(self):
        meta = _build_rag_metadata([], {})
        assert meta.chunk_count == 0
        assert meta.avg_similarity == 0.0

    def test_single_source(self):
        chunks = [_make_chunk(similarity=0.85), _make_chunk(similarity=0.75)]
        source_map = {SOURCE_ID: "Doc.pdf"}
        meta = _build_rag_metadata(chunks, source_map)
        assert meta.chunk_count == 2
        assert meta.source_count == 1
        assert meta.avg_similarity == 0.8
        assert meta.sources_used[0]["name"] == "Doc.pdf"
        assert meta.sources_used[0]["chunk_count"] == 2


