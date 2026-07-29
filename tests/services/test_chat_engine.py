"""
Tests for chat engine services:
  - apps/api/app/services/chat_rag.py (prepare_context)
  - apps/api/app/services/chat_streaming.py (parse_citations, stream_response)
  - apps/api/app/services/sse.py (build_chat_event_stream)
  - apps/api/app/services/chat_session.py (get_or_create_session)

All LLM and DB calls are mocked.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.app.services.chat_rag import ChatContext, prepare_context
from apps.api.app.services.chat_session import get_or_create_session
from apps.api.app.services.chat_streaming import (
    clean_citations_from_text,
    parse_citations,
    stream_response,
)
from apps.api.app.services.sse import build_chat_event_stream
from packages.llm.types import LLMStreamChunk, LLMUsage

# ─── Constants ─────────────────────────────────────────────────

ORG_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
DEAL_ID = str(uuid.uuid4())
SESSION_ID = str(uuid.uuid4())
SOURCE_ID = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()


# ─── Helpers ───────────────────────────────────────────────────


def _db_rpc_with_chunks(chunks: list[dict]) -> MagicMock:
    """Mock DB with rpc returning chunks and table for source name lookup."""
    db = MagicMock()

    rpc_chain = MagicMock()
    rpc_chain.execute.return_value = MagicMock(data=chunks)
    db.rpc.return_value = rpc_chain

    src_chain = MagicMock()
    for m in ("select", "in_", "eq"):
        getattr(src_chain, m).return_value = src_chain
    src_chain.execute.return_value = MagicMock(
        data=[{"id": SOURCE_ID, "name": "BP.xlsx"}]
    )
    db.table.return_value = src_chain

    return db


def _db_for_session(session_rows: list[dict]) -> MagicMock:
    """Mock DB for chat session queries."""
    db = MagicMock()
    chain = MagicMock()
    for m in ("select", "eq", "insert"):
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(data=session_rows)
    db.table.return_value = chain
    return db


async def _collect_sse_events(gen) -> list[str]:
    """Collect all SSE event strings from an async generator."""
    events = []
    async for chunk in gen:
        events.append(chunk)
    return events


def _parse_event_names(events: list[str]) -> list[str]:
    """Extract event names from SSE strings."""
    names = []
    for e in events:
        for line in e.split("\n"):
            if line.startswith("event:"):
                names.append(line.replace("event:", "").strip())
    return names


# ─── prepare_context ────────────────────────────────────────────


@pytest.mark.asyncio
class TestPrepareContext:
    async def test_context_with_chunks(self):
        """Chunks found → prompt contains content, source_map is populated."""
        chunks = [
            {
                "source_id": SOURCE_ID,
                "content": "ARR 2024 : 8M€",
                "page_number": 7,
                "section_title": "Financials",
            }
        ]
        db = _db_rpc_with_chunks(chunks)

        embedder = AsyncMock()
        embedder.embed_query.return_value = [0.1] * 1536

        with patch(
            "apps.api.app.services.chat_rag.get_embedder", return_value=embedder
        ):
            ctx = await prepare_context(
                db,
                query="ARR?",
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
            )

        assert len(ctx.chunks) == 1
        assert "ARR 2024 : 8M€" in ctx.prompt
        assert ctx.source_map[SOURCE_ID] == "BP.xlsx"

    async def test_context_no_chunks(self):
        """No chunks found → prompt contains fallback message."""
        db = _db_rpc_with_chunks([])

        embedder = AsyncMock()
        embedder.embed_query.return_value = [0.0] * 1536

        with patch(
            "apps.api.app.services.chat_rag.get_embedder", return_value=embedder
        ):
            ctx = await prepare_context(
                db,
                query="?",
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
            )

        assert ctx.chunks == []
        assert "Aucun document pertinent" in ctx.prompt

    async def test_context_with_history(self):
        """Session history → prompt contains HISTORIQUE header."""
        db = _db_rpc_with_chunks([])

        embedder = AsyncMock()
        embedder.embed_query.return_value = [0.0] * 1536

        with (
            patch("apps.api.app.services.chat_rag.get_embedder", return_value=embedder),
            patch(
                "apps.api.app.services.chat_history.build_history_block",
                new_callable=AsyncMock,
                return_value="HISTORIQUE DE LA CONVERSATION :\nUtilisateur: Question précédente\n\n---\n\n",
            ),
        ):
            ctx = await prepare_context(
                db,
                query="Suite?",
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
                session_id=SESSION_ID,
            )

        assert "HISTORIQUE" in ctx.prompt

    async def test_context_budget_truncation(self):
        """Chunks exceeding token budget are truncated."""
        from apps.api.app.services.chat_rag import MAX_CONTEXT_TOKENS

        # Each chunk is ~5K tokens (20K chars) — exceeds 8K budget
        big_content = "x" * (MAX_CONTEXT_TOKENS * 4 // 2 + 1000)
        chunks = [
            {
                "source_id": SOURCE_ID,
                "content": big_content,
                "page_number": 1,
                "section_title": "S1",
            },
            {
                "source_id": SOURCE_ID,
                "content": big_content,
                "page_number": 2,
                "section_title": "S2",
            },
        ]
        db = _db_rpc_with_chunks(chunks)

        embedder = AsyncMock()
        embedder.embed_query.return_value = [0.0] * 1536

        with patch(
            "apps.api.app.services.chat_rag.get_embedder", return_value=embedder
        ):
            ctx = await prepare_context(
                db,
                query="?",
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
            )

        # Prompt tokens should be under budget (8K tokens × 4 chars)
        assert len(ctx.prompt) < MAX_CONTEXT_TOKENS * 4 * 2


# ─── parse_citations ────────────────────────────────────────────


class TestParseCitations:
    def test_parse_valid_citation(self):
        """[SOURCE:id:page:section:quote] is correctly parsed."""
        text = f"L'ARR est de 8M€. [SOURCE:{SOURCE_ID}:7:Financials:ARR 8M]"
        citations = parse_citations(text, {SOURCE_ID: "BP.xlsx"})

        assert len(citations) == 1
        c = citations[0]
        assert c["source_id"] == SOURCE_ID
        assert c["source_name"] == "BP.xlsx"
        assert c["page_number"] == 7
        assert c["quote"] == "ARR 8M"

    def test_parse_deduplicates_same_citation(self):
        """Duplicate citations are removed."""
        tag = f"[SOURCE:{SOURCE_ID}:7:Fin:ARR 8M]"
        text = f"Réponse {tag} et encore {tag}"
        citations = parse_citations(text, {SOURCE_ID: "BP.xlsx"})
        assert len(citations) == 1

    def test_parse_no_citations(self):
        """Text without [SOURCE:...] returns empty list."""
        citations = parse_citations("Réponse sans source.", {})
        assert citations == []

    def test_page_unknown(self):
        """page='?' → page_number is None."""
        text = f"[SOURCE:{SOURCE_ID}:?:Section:quote]"
        citations = parse_citations(text, {SOURCE_ID: "Doc.pdf"})
        assert len(citations) == 1
        assert citations[0]["page_number"] is None

    def test_source_name_unknown(self):
        """source_id not in source_map → source_name is 'Document inconnu'."""
        text = "[SOURCE:unknown-id:3:Section:quote]"
        citations = parse_citations(text, {})
        assert len(citations) == 1
        assert citations[0]["source_name"] == "Document inconnu"


# ─── build_chat_event_stream ────────────────────────────────────


@pytest.mark.asyncio
class TestBuildChatEventStream:
    async def test_stream_protocol(self):
        """Sequence: session → content → citations → usage → done."""
        usage = MagicMock(
            input_tokens=10, output_tokens=5, cost_usd=0.001, model="claude-4"
        )

        async def fake_stream(context):
            yield "Réponse.", None
            yield "", usage

        ctx = ChatContext(chunks=[], prompt="test", system_prompt="test-system", source_map={})

        with patch("apps.api.app.services.sse.stream_response", fake_stream):
            with patch(
                "apps.api.app.services.sse.persist_messages",
                new_callable=AsyncMock,
            ):
                events = await _collect_sse_events(
                    build_chat_event_stream(
                        context=ctx,
                        session_id=SESSION_ID,
                        organization_id=ORG_ID,
                        user_content="Q?",
                        db=MagicMock(),
                    )
                )

        names = _parse_event_names(events)
        assert "session" in names
        assert "content" in names
        assert "citations" in names
        assert "usage" in names
        assert "done" in names
        assert names[-1] == "done"

    async def test_stream_error_yields_error_event(self):
        """Exception in stream_response → error event before done."""

        async def failing_stream(context):
            raise RuntimeError("LLM down")
            yield  # make it a generator

        ctx = ChatContext(chunks=[], prompt="test", system_prompt="test-system", source_map={})

        with patch("apps.api.app.services.sse.stream_response", failing_stream):
            events = await _collect_sse_events(
                build_chat_event_stream(
                    context=ctx,
                    session_id=SESSION_ID,
                    organization_id=ORG_ID,
                    user_content="Q?",
                    db=MagicMock(),
                )
            )

        names = _parse_event_names(events)
        assert "error" in names
        assert "done" in names

    async def test_persist_messages_called(self):
        """persist_messages is called after streaming completes."""

        async def fake_stream(context):
            yield "Réponse.", None
            yield (
                "",
                MagicMock(input_tokens=1, output_tokens=1, cost_usd=0.0, model="m"),
            )

        ctx = ChatContext(chunks=[], prompt="test", system_prompt="test-system", source_map={})

        with patch("apps.api.app.services.sse.stream_response", fake_stream):
            with patch(
                "apps.api.app.services.sse.persist_messages",
                new_callable=AsyncMock,
            ) as mock_persist:
                await _collect_sse_events(
                    build_chat_event_stream(
                        context=ctx,
                        session_id=SESSION_ID,
                        organization_id=ORG_ID,
                        user_content="Q?",
                        db=MagicMock(),
                    )
                )

        mock_persist.assert_called_once()
        call_kwargs = mock_persist.call_args.kwargs
        assert call_kwargs["session_id"] == SESSION_ID
        assert "Réponse." in call_kwargs["assistant_content"]


# ─── get_or_create_session ──────────────────────────────────────


@pytest.mark.asyncio
class TestGetOrCreateSession:
    async def test_existing_session_returned(self):
        """Existing session_id → same ID returned without insert."""
        db = _db_for_session([{"id": SESSION_ID}])
        result = await get_or_create_session(
            db,
            session_id=SESSION_ID,
            workspace_id=DEAL_ID,
            organization_id=ORG_ID,
            user_id=USER_ID,
            first_message="Bonjour",
        )
        assert result == SESSION_ID

    async def test_new_session_created(self):
        """session_id=None → new session inserted, its ID returned."""
        new_id = str(uuid.uuid4())
        db = _db_for_session([{"id": new_id}])

        result = await get_or_create_session(
            db,
            session_id=None,
            workspace_id=DEAL_ID,
            organization_id=ORG_ID,
            user_id=USER_ID,
            first_message="Première question",
        )
        assert result == new_id

    async def test_session_not_found_raises_404(self):
        """session_id provided but not in DB → HTTPException 404."""
        from fastapi import HTTPException

        db = _db_for_session([])  # empty → session not found

        with pytest.raises(HTTPException) as exc:
            await get_or_create_session(
                db,
                session_id=SESSION_ID,
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
                user_id=USER_ID,
                first_message="Q?",
            )
        assert exc.value.status_code == 404


# ─── stream_response ────────────────────────────────────────────


@pytest.mark.asyncio
class TestStreamResponse:
    async def test_yields_content_chunks(self):
        """stream_response yields (text, None) for each non-final chunk."""

        async def _mock_stream(*args, **kwargs):
            yield LLMStreamChunk(content="Bonjour ", is_final=False)
            yield LLMStreamChunk(content="monde", is_final=False)
            yield LLMStreamChunk(
                content="",
                is_final=True,
                usage=LLMUsage(
                    input_tokens=10, output_tokens=5, cost_usd=0.001, model="m"
                ),
            )

        mock_llm = MagicMock()
        mock_llm.stream = _mock_stream
        ctx = ChatContext(chunks=[], prompt="test", system_prompt="test-system", source_map={})

        with patch(
            "apps.api.app.services.chat_streaming.get_llm", return_value=mock_llm
        ):
            results = []
            async for text, usage in stream_response(ctx):
                results.append((text, usage))

        assert results[0] == ("Bonjour ", None)
        assert results[1] == ("monde", None)

    async def test_yields_final_usage(self):
        """Last yield is ('', LLMUsage) with correct usage data."""
        expected_usage = LLMUsage(
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.001,
            model="claude-sonnet-4-20250514",
        )

        async def _mock_stream(*args, **kwargs):
            yield LLMStreamChunk(content="Text", is_final=False)
            yield LLMStreamChunk(content="", is_final=True, usage=expected_usage)

        mock_llm = MagicMock()
        mock_llm.stream = _mock_stream
        ctx = ChatContext(chunks=[], prompt="test", system_prompt="test-system", source_map={})

        with patch(
            "apps.api.app.services.chat_streaming.get_llm", return_value=mock_llm
        ):
            results = []
            async for text, usage in stream_response(ctx):
                results.append((text, usage))

        last_text, last_usage = results[-1]
        assert last_text == ""
        assert last_usage is expected_usage

    async def test_final_only_stream(self):
        """Stream with only a final chunk yields a single ('', LLMUsage)."""
        usage = LLMUsage(input_tokens=5, output_tokens=0, cost_usd=0.0, model="m")

        async def _mock_stream(*args, **kwargs):
            yield LLMStreamChunk(content="", is_final=True, usage=usage)

        mock_llm = MagicMock()
        mock_llm.stream = _mock_stream
        ctx = ChatContext(chunks=[], prompt="test", system_prompt="test-system", source_map={})

        with patch(
            "apps.api.app.services.chat_streaming.get_llm", return_value=mock_llm
        ):
            results = []
            async for text, u in stream_response(ctx):
                results.append((text, u))

        assert len(results) == 1
        assert results[0] == ("", usage)


# ─── clean_citations_from_text ───────────────────────────────────


class TestCleanCitationsFromText:
    def test_removes_citation_tags(self):
        """[SOURCE:...] tags are removed from the display text."""
        text = f"Résultat [SOURCE:{SOURCE_ID}:7:Financials:ARR 8M]. Fin."
        cleaned = clean_citations_from_text(text)
        assert "[SOURCE:" not in cleaned
        assert "Résultat" in cleaned
        assert "Fin." in cleaned

    def test_no_tags_unchanged(self):
        """Text without [SOURCE:...] is returned unchanged."""
        text = "Simple text without citations."
        assert clean_citations_from_text(text) == text

    def test_multiple_tags_removed(self):
        """Multiple [SOURCE:...] tags are all removed."""
        tag1 = f"[SOURCE:{SOURCE_ID}:1:S1:q1]"
        tag2 = f"[SOURCE:{SOURCE_ID}:2:S2:q2]"
        text = f"Text {tag1} more {tag2} end"
        cleaned = clean_citations_from_text(text)
        assert "[SOURCE:" not in cleaned
        assert "Text" in cleaned
        assert "more" in cleaned
