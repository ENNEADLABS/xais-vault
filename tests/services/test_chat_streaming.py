"""
Tests for apps/api/app/services/chat_streaming.py

Pure functions (parse_citations, clean_citations_from_text) tested without mocks.
stream_response() uses an async generator mock for the LLM.
"""

from unittest.mock import MagicMock, patch

import pytest

from apps.api.app.services.chat_rag import ChatContext
from apps.api.app.services.chat_streaming import (
    clean_citations_from_text,
    parse_citations,
    stream_response,
)
from packages.llm.types import LLMStreamChunk, LLMUsage

# ─── parse_citations ────────────────────────────────────────────


class TestParseCitations:
    def test_extracts_single_citation(self):
        """Parses one [SOURCE:...] tag correctly."""
        source_map = {"src-001": "Investment Memo"}
        content = "Le ARR est de 8M€ [SOURCE:src-001:7:Financials:ARR 2024 : 8,0M€]."
        citations = parse_citations(content, source_map)
        assert len(citations) == 1
        c = citations[0]
        assert c["source_id"] == "src-001"
        assert c["source_name"] == "Investment Memo"
        assert c["page_number"] == 7
        assert c["section_title"] == "Financials"
        assert c["quote"] == "ARR 2024 : 8,0M€"

    def test_extracts_multiple_citations(self):
        """Parses several [SOURCE:...] tags from one text."""
        source_map = {"src-001": "Memo", "src-002": "Term Sheet"}
        content = (
            "Valorisation [SOURCE:src-001:3:Valorisation:50M€]. "
            "Closing [SOURCE:src-002:1:Terms:42M€]."
        )
        citations = parse_citations(content, source_map)
        assert len(citations) == 2
        ids = [c["source_id"] for c in citations]
        assert "src-001" in ids
        assert "src-002" in ids

    def test_deduplicates_same_citation(self):
        """Identical citations (same source+page+quote prefix) appear once."""
        source_map = {"src-001": "Memo"}
        content = (
            "[SOURCE:src-001:3:Section:same quote] "
            "[SOURCE:src-001:3:Section:same quote]"
        )
        citations = parse_citations(content, source_map)
        assert len(citations) == 1

    def test_unknown_source_uses_fallback_name(self):
        """Source not in source_map gets 'Document inconnu'."""
        content = "[SOURCE:src-999:1:Section:quote]"
        citations = parse_citations(content, {})
        assert citations[0]["source_name"] == "Document inconnu"

    def test_unknown_page_returns_none(self):
        """Page '?' becomes None."""
        content = "[SOURCE:src-001:?:Section:quote]"
        citations = parse_citations(content, {"src-001": "Memo"})
        assert citations[0]["page_number"] is None

    def test_invalid_page_returns_none(self):
        """Non-numeric page becomes None."""
        content = "[SOURCE:src-001:abc:Section:quote]"
        citations = parse_citations(content, {"src-001": "Memo"})
        assert citations[0]["page_number"] is None

    def test_unknown_section_returns_none(self):
        """Section '?' becomes None."""
        content = "[SOURCE:src-001:3:?:quote]"
        citations = parse_citations(content, {"src-001": "Memo"})
        assert citations[0]["section_title"] is None

    def test_no_citations_returns_empty(self):
        """Text with no [SOURCE:...] tags returns empty list."""
        citations = parse_citations("Aucune citation ici.", {"src-001": "Memo"})
        assert citations == []


# ─── clean_citations_from_text ──────────────────────────────────


class TestCleanCitationsFromText:
    def test_removes_source_tags(self):
        """[SOURCE:...] tags are stripped from the text."""
        text = "Le ARR est de 8M€ [SOURCE:src-001:7:Financials:ARR] cette année."
        cleaned = clean_citations_from_text(text)
        assert "[SOURCE:" not in cleaned
        assert "Le ARR est de 8M€" in cleaned

    def test_removes_multiple_tags(self):
        """Multiple tags are all removed."""
        text = "[SOURCE:a:1:S:q] Texte [SOURCE:b:2:S:q] fin."
        cleaned = clean_citations_from_text(text)
        assert "[SOURCE:" not in cleaned

    def test_no_tags_unchanged(self):
        """Text without tags is returned as-is (stripped)."""
        text = "Aucune citation ici."
        assert clean_citations_from_text(text) == text

    def test_strips_surrounding_whitespace(self):
        """Leading/trailing whitespace is stripped."""
        text = "  [SOURCE:src:1:s:q]  "
        assert clean_citations_from_text(text) == ""


# ─── stream_response ────────────────────────────────────────────


@pytest.mark.asyncio
class TestStreamResponse:
    async def test_yields_text_chunks(self):
        """Yields (text, None) for each non-final chunk."""
        usage = LLMUsage(
            input_tokens=100, output_tokens=50, cost_usd=0.001, model="claude-test"
        )
        chunks = [
            LLMStreamChunk(content="Bonjour", is_final=False),
            LLMStreamChunk(content=" monde", is_final=False),
            LLMStreamChunk(content="", is_final=True, usage=usage),
        ]

        async def _gen(*args, **kwargs):
            for c in chunks:
                yield c

        mock_llm = MagicMock()
        mock_llm.stream = _gen

        context = ChatContext(
            chunks=[],
            prompt="test prompt",
            system_prompt="test-system",
            source_map={},
        )

        with patch(
            "apps.api.app.services.chat_streaming.get_llm", return_value=mock_llm
        ):
            results = []
            async for text, u in stream_response(context):
                results.append((text, u))

        texts = [r[0] for r in results if r[1] is None]
        final = [r for r in results if r[1] is not None]

        assert "Bonjour" in texts
        assert " monde" in texts
        assert len(final) == 1
        assert final[0][1] is usage

    async def test_final_chunk_yields_usage(self):
        """The final (is_final=True) chunk yields ("", usage)."""
        usage = LLMUsage(input_tokens=10, output_tokens=5, model="m")
        chunks = [LLMStreamChunk(content="", is_final=True, usage=usage)]

        async def _gen(*args, **kwargs):
            for c in chunks:
                yield c

        mock_llm = MagicMock()
        mock_llm.stream = _gen

        context = ChatContext(chunks=[], prompt="p", system_prompt="test-system", source_map={})

        with patch(
            "apps.api.app.services.chat_streaming.get_llm", return_value=mock_llm
        ):
            results = []
            async for text, u in stream_response(context):
                results.append((text, u))

        assert len(results) == 1
        assert results[0] == ("", usage)
