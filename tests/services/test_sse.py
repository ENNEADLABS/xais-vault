"""
Tests for apps/api/app/services/sse.py

sse_event() is a pure function. build_chat_event_stream() is tested with
mocked stream_response and persist_messages.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.app.services.chat_rag import ChatContext
from apps.api.app.services.sse import build_chat_event_stream, sse_event
from packages.llm.types import LLMUsage

SESSION_ID = "session-abc"
ORG_ID = "org-xyz"


# ─── sse_event ──────────────────────────────────────────────────


class TestSseEvent:
    def test_dict_payload_serialized_as_json(self):
        """dict data is JSON-serialized in the event."""
        event = sse_event("content", {"text": "Bonjour"})
        assert event.startswith("event: content\n")
        assert '"text": "Bonjour"' in event
        assert event.endswith("\n\n")

    def test_list_payload_serialized_as_json(self):
        """list data is JSON-serialized."""
        event = sse_event("citations", [{"source_id": "src-001"}])
        assert "event: citations\n" in event
        assert '"source_id"' in event

    def test_string_payload_passed_through(self):
        """String data is used as-is, not double-encoded."""
        event = sse_event("done", "{}")
        assert "data: {}" in event

    def test_format_has_double_newline_terminator(self):
        """SSE events must end with \\n\\n."""
        event = sse_event("session", {"id": SESSION_ID})
        assert event.endswith("\n\n")

    def test_unicode_preserved(self):
        """Non-ASCII characters are preserved (ensure_ascii=False)."""
        event = sse_event("content", {"text": "Valorisation : 50M€"})
        assert "50M€" in event

    def test_empty_dict_payload(self):
        """Empty dict produces valid empty JSON object."""
        event = sse_event("done", {})
        data_line = [line for line in event.split("\n") if line.startswith("data:")][0]
        assert json.loads(data_line[len("data: ") :]) == {}


# ─── build_chat_event_stream ────────────────────────────────────


def _make_context(source_map: dict | None = None) -> ChatContext:
    return ChatContext(
        chunks=[],
        prompt="Test prompt",
        system_prompt="test-system",
        source_map=source_map or {},
    )


async def _make_stream(*text_chunks: str, usage: LLMUsage | None = None):
    """Async generator that yields (text, None) then ("", usage)."""
    for t in text_chunks:
        yield t, None
    if usage:
        yield "", usage


@pytest.mark.asyncio
class TestBuildChatEventStream:
    async def test_first_event_is_session(self):
        """First yielded event is 'session' with session_id."""
        context = _make_context()
        db = MagicMock()

        async def _fake_stream(_):
            return
            yield  # make it an async generator

        with (
            patch(
                "apps.api.app.services.sse.stream_response", side_effect=_fake_stream
            ),
            patch("apps.api.app.services.sse.persist_messages", new=AsyncMock()),
        ):
            events = []
            async for chunk in build_chat_event_stream(
                context=context,
                session_id=SESSION_ID,
                organization_id=ORG_ID,
                user_content="Question",
                db=db,
            ):
                events.append(chunk)

        assert events[0].startswith("event: session\n")
        assert SESSION_ID in events[0]

    async def test_content_events_streamed(self):
        """Text chunks produce 'content' events."""
        context = _make_context()
        usage = LLMUsage(input_tokens=10, output_tokens=5, model="m")
        db = MagicMock()

        async def _fake_stream(_):
            yield "Bonjour", None
            yield " monde", None
            yield "", usage

        with (
            patch(
                "apps.api.app.services.sse.stream_response", side_effect=_fake_stream
            ),
            patch("apps.api.app.services.sse.persist_messages", new=AsyncMock()),
        ):
            events = []
            async for chunk in build_chat_event_stream(
                context=context,
                session_id=SESSION_ID,
                organization_id=ORG_ID,
                user_content="Q",
                db=db,
            ):
                events.append(chunk)

        content_events = [e for e in events if e.startswith("event: content\n")]
        texts = [json.loads(e.split("data: ")[1]) for e in content_events]
        all_text = "".join(t["text"] for t in texts)
        assert "Bonjour monde" == all_text

    async def test_citations_event_emitted(self):
        """'citations' event is emitted after streaming."""
        source_map = {"src-001": "Memo"}
        context = _make_context(source_map=source_map)
        usage = LLMUsage(input_tokens=10, output_tokens=5, model="m")
        db = MagicMock()

        async def _fake_stream(_):
            yield "Résultat [SOURCE:src-001:1:S:quote]", None
            yield "", usage

        with (
            patch(
                "apps.api.app.services.sse.stream_response", side_effect=_fake_stream
            ),
            patch("apps.api.app.services.sse.persist_messages", new=AsyncMock()),
        ):
            events = []
            async for chunk in build_chat_event_stream(
                context=context,
                session_id=SESSION_ID,
                organization_id=ORG_ID,
                user_content="Q",
                db=db,
            ):
                events.append(chunk)

        citations_events = [e for e in events if e.startswith("event: citations\n")]
        assert len(citations_events) == 1
        payload = json.loads(citations_events[0].split("data: ")[1])
        assert "citations" in payload
        assert payload["citations"][0]["source_id"] == "src-001"

    async def test_usage_event_emitted(self):
        """'usage' event is emitted with token/cost data."""
        context = _make_context()
        usage = LLMUsage(
            input_tokens=100, output_tokens=50, cost_usd=0.002, model="claude-test"
        )
        db = MagicMock()

        async def _fake_stream(_):
            yield "Texte", None
            yield "", usage

        with (
            patch(
                "apps.api.app.services.sse.stream_response", side_effect=_fake_stream
            ),
            patch("apps.api.app.services.sse.persist_messages", new=AsyncMock()),
        ):
            events = []
            async for chunk in build_chat_event_stream(
                context=context,
                session_id=SESSION_ID,
                organization_id=ORG_ID,
                user_content="Q",
                db=db,
            ):
                events.append(chunk)

        usage_events = [e for e in events if e.startswith("event: usage\n")]
        assert len(usage_events) == 1
        payload = json.loads(usage_events[0].split("data: ")[1])
        assert payload["input_tokens"] == 100
        assert payload["model"] == "claude-test"

    async def test_done_event_always_last(self):
        """'done' event is always the last event yielded."""
        context = _make_context()
        db = MagicMock()

        async def _fake_stream(_):
            yield "OK", None
            yield "", LLMUsage()

        with (
            patch(
                "apps.api.app.services.sse.stream_response", side_effect=_fake_stream
            ),
            patch("apps.api.app.services.sse.persist_messages", new=AsyncMock()),
        ):
            events = []
            async for chunk in build_chat_event_stream(
                context=context,
                session_id=SESSION_ID,
                organization_id=ORG_ID,
                user_content="Q",
                db=db,
            ):
                events.append(chunk)

        assert events[-1].startswith("event: done\n")

    async def test_error_during_stream_yields_error_event(self):
        """Exceptions during streaming produce an 'error' event."""
        context = _make_context()
        db = MagicMock()

        async def _failing_stream(_):
            yield "Début", None
            raise RuntimeError("LLM unavailable")

        with (
            patch(
                "apps.api.app.services.sse.stream_response", side_effect=_failing_stream
            ),
            patch("apps.api.app.services.sse.persist_messages", new=AsyncMock()),
        ):
            events = []
            async for chunk in build_chat_event_stream(
                context=context,
                session_id=SESSION_ID,
                organization_id=ORG_ID,
                user_content="Q",
                db=db,
            ):
                events.append(chunk)

        error_events = [e for e in events if e.startswith("event: error\n")]
        assert len(error_events) == 1
        # Done event still emitted after error
        assert events[-1].startswith("event: done\n")

    async def test_persist_messages_called_after_stream(self):
        """persist_messages is called once with full content after streaming."""
        context = _make_context()
        usage = LLMUsage(input_tokens=10, output_tokens=5, model="m")
        db = MagicMock()
        mock_persist = AsyncMock()

        async def _fake_stream(_):
            yield "Bonjour", None
            yield " monde", None
            yield "", usage

        with (
            patch(
                "apps.api.app.services.sse.stream_response", side_effect=_fake_stream
            ),
            patch("apps.api.app.services.sse.persist_messages", new=mock_persist),
        ):
            async for _ in build_chat_event_stream(
                context=context,
                session_id=SESSION_ID,
                organization_id=ORG_ID,
                user_content="Q",
                db=db,
            ):
                pass

        mock_persist.assert_awaited_once()
        call_kwargs = mock_persist.call_args.kwargs
        assert call_kwargs["session_id"] == SESSION_ID
        assert call_kwargs["user_content"] == "Q"
        assert "Bonjour monde" in call_kwargs["assistant_content"]
