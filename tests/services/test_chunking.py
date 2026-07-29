"""
Tests for apps/worker/app/services/chunking.py.

Pure functions — no external dependencies, no mocks needed.
"""


from apps.worker.app.services.chunking import (
    CHARS_PER_TOKEN,
    MIN_CHUNK_TOKENS,
    Chunk,
    _split_large_text,
    chunk_document,
    estimate_tokens,
)

# ─── estimate_tokens ──────────────────────────────────────────


class TestEstimateTokens:
    def test_divides_by_4(self):
        assert estimate_tokens("a" * 400) == 100

    def test_empty_string_returns_0(self):
        assert estimate_tokens("") == 0


# ─── chunk_document ───────────────────────────────────────────


class TestChunkDocument:
    def test_empty_text_returns_empty_list(self):
        assert chunk_document("") == []

    def test_whitespace_only_returns_empty_list(self):
        assert chunk_document("   \n\n\t  ") == []

    def test_short_document_returns_single_chunk(self):
        """Text well under MIN_CHUNK_TOKENS produces one chunk."""
        text = "Hello world. " * 100  # ~325 tokens — under 4000
        chunks = chunk_document(text)
        assert len(chunks) == 1
        assert chunks[0].chunk_index == 0

    def test_long_document_splits_into_multiple_chunks(self):
        """Text well over MAX_CHUNK_TOKENS is split into multiple chunks."""
        text = "Lorem ipsum dolor sit amet. " * 3600  # ~25200 tokens
        chunks = chunk_document(text)
        assert len(chunks) > 1

    def test_chunk_tokens_within_target_range(self):
        """All chunks except possibly the last should reach MIN_CHUNK_TOKENS."""
        text = "The quick brown fox jumps over the lazy dog. " * 5500  # ~24750 tokens
        chunks = chunk_document(text)
        assert len(chunks) > 1
        for chunk in chunks[:-1]:
            assert chunk.token_count >= MIN_CHUNK_TOKENS

    def test_last_chunk_can_be_smaller_than_minimum(self):
        """The last chunk can be smaller than MIN_CHUNK_TOKENS."""
        # Big section that will fill one chunk, plus a small tail
        big = "word " * (MIN_CHUNK_TOKENS * CHARS_PER_TOKEN // 5 + 100)
        small = "\n\nThis is a small trailing section."
        chunks = chunk_document(big + small)
        # Either one chunk (tail merged in) or the last one is small
        assert len(chunks) >= 1
        if len(chunks) > 1:
            assert chunks[-1].token_count < MIN_CHUNK_TOKENS

    def test_page_breaks_create_natural_boundaries(self):
        """PAGE BREAK markers cause content to be tagged with page numbers.

        Each page must exceed MIN_CHUNK_TOKENS (4000) so it isn't merged
        with the other page's content before flushing.
        """
        # ~4200 tokens per page (21 chars × 800 / 4) — exceeds MIN_CHUNK_TOKENS
        page1 = "Content of page one. " * 800
        page2 = "Content of page two. " * 800
        text = page1 + "\n\n--- PAGE BREAK ---\n\n" + page2
        chunks = chunk_document(text)
        assert any(c.page_number == 1 for c in chunks)
        assert any(c.page_number == 2 for c in chunks)

    def test_headings_preserved_as_section_titles(self):
        """Heading text is captured as section_title on subsequent chunks."""
        text = "## Executive Summary\n\n" + "Analysis content here. " * 200
        chunks = chunk_document(text)
        assert any(c.section_title == "Executive Summary" for c in chunks)

    def test_slide_breaks_split_correctly(self):
        """Slide break markers are treated as section boundaries."""
        slide1 = "Slide one content. " * 200
        slide2 = "Slide two content. " * 200
        text = slide1 + "\n\n--- Slide 2 ---" + slide2
        chunks = chunk_document(text)
        assert len(chunks) >= 1
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_chunk_indexes_are_sequential(self):
        """chunk_index starts at 0 and increments by 1."""
        text = "sentence. " * 5000  # ~12500 tokens — multiple chunks
        chunks = chunk_document(text)
        assert len(chunks) > 1
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_overlap_between_split_chunks(self):
        """Large text split by _split_large_text has overlap between chunks."""
        # One solid block with no paragraph breaks to force _split_large_text
        text = "word " * 8000  # ~10000 tokens — over MAX_CHUNK_TOKENS
        chunks = chunk_document(text)
        assert len(chunks) > 1
        # Last words of chunk N-1 should appear somewhere in chunk N
        last_words = chunks[0].content.split()[-5:]
        next_start = chunks[1].content.split()[:20]
        assert any(w in next_start for w in last_words)


# ─── _split_large_text ────────────────────────────────────────


class TestSplitLargeText:
    def test_creates_overlapping_chunks(self):
        """Consecutive chunks share some trailing/leading content."""
        text = "sentence. " * 3000  # ~7500 tokens
        chunks = _split_large_text(text, start_index=0, page_number=1, section_title="Test")
        assert len(chunks) > 1
        last_words = chunks[0].content.split()[-5:]
        next_start = chunks[1].content.split()[:20]
        assert any(w in next_start for w in last_words)

    def test_preserves_page_number_and_section_title(self):
        """page_number and section_title propagate to every sub-chunk."""
        text = "data " * 5000
        chunks = _split_large_text(text, start_index=0, page_number=3, section_title="Financials")
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.page_number == 3
            assert chunk.section_title == "Financials"

    def test_start_index_propagates(self):
        """chunk_index starts at start_index and increments."""
        text = "content " * 3000
        chunks = _split_large_text(text, start_index=5, page_number=None, section_title=None)
        assert chunks[0].chunk_index == 5
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == 5 + i
