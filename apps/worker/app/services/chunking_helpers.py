"""
Chunking helpers — internal splitting and merging logic.

Extracted from chunking.py for the 200-line-per-file rule.
Contains _Section, all split/merge functions, and the shared Chunk model.
"""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CHARS_PER_TOKEN = 4
MIN_CHUNK_TOKENS = 400
MAX_CHUNK_TOKENS = 800
OVERLAP_TOKENS = 100  # Overlap between split chunks for context continuity

# Patterns for natural split boundaries (ordered by priority)
PAGE_BREAK = re.compile(r"\n\n--- PAGE BREAK ---\n\n")
HEADING = re.compile(r"\n(#{1,6} .+)")
SLIDE_BREAK = re.compile(r"\n\n--- Slide \d+ ---")
DOUBLE_NEWLINE = re.compile(r"\n\n+")


@dataclass
class Chunk:
    """A single text chunk ready for embedding."""

    content: str
    chunk_index: int
    token_count: int
    page_number: int | None = None
    section_title: str | None = None


@dataclass
class _Section:
    """Intermediate section before merging into chunks."""

    text: str
    tokens: int
    page_number: int | None
    section_title: str | None


def estimate_tokens(text: str) -> int:
    """Estimate token count from character count."""
    return len(text) // CHARS_PER_TOKEN


def _split_into_sections(text: str) -> list[_Section]:
    """Split text into sections on natural boundaries with metadata."""
    pages = PAGE_BREAK.split(text)
    sections: list[_Section] = []

    for page_idx, page_text in enumerate(pages, start=1):
        page_num = page_idx if len(pages) > 1 else None

        parts = _split_on_boundaries(page_text)

        current_heading: str | None = None
        for part in parts:
            stripped = part.strip()
            if not stripped:
                continue

            heading_match = re.match(r"^(#{1,6}) (.+)$", stripped, re.MULTILINE)
            if heading_match:
                current_heading = heading_match.group(2).strip()

            sections.append(
                _Section(
                    text=stripped,
                    tokens=estimate_tokens(stripped),
                    page_number=page_num,
                    section_title=current_heading,
                )
            )

    return sections


def _split_on_boundaries(text: str) -> list[str]:
    """Split text on headings and double newlines, keeping delimiters."""
    parts = SLIDE_BREAK.split(text)
    result: list[str] = []

    for part in parts:
        sub_parts = HEADING.split(part)
        for sub in sub_parts:
            if estimate_tokens(sub) > MAX_CHUNK_TOKENS:
                result.extend(DOUBLE_NEWLINE.split(sub))
            else:
                result.append(sub)

    return result


def _merge_and_split(sections: list[_Section]) -> list[Chunk]:
    """Merge small sections and split oversized ones to hit target range."""
    chunks: list[Chunk] = []
    buffer_texts: list[str] = []
    buffer_tokens = 0
    buffer_page: int | None = None
    buffer_title: str | None = None
    chunk_index = 0

    def flush_buffer():
        nonlocal chunk_index, buffer_texts, buffer_tokens, buffer_page, buffer_title
        if not buffer_texts:
            return
        content = "\n\n".join(buffer_texts)
        tokens = estimate_tokens(content)
        if tokens > 0:
            chunks.append(
                Chunk(
                    content=content,
                    chunk_index=chunk_index,
                    token_count=tokens,
                    page_number=buffer_page,
                    section_title=buffer_title,
                )
            )
            chunk_index += 1
        buffer_texts = []
        buffer_tokens = 0
        buffer_page = None
        buffer_title = None

    for section in sections:
        if section.tokens > MAX_CHUNK_TOKENS:
            flush_buffer()
            for sub_chunk in _split_large_text(
                section.text, chunk_index, section.page_number, section.section_title
            ):
                chunks.append(sub_chunk)
                chunk_index = sub_chunk.chunk_index + 1
            continue

        if buffer_tokens + section.tokens > MAX_CHUNK_TOKENS and buffer_texts:
            flush_buffer()

        buffer_texts.append(section.text)
        buffer_tokens += section.tokens
        if buffer_page is None:
            buffer_page = section.page_number
        if buffer_title is None:
            buffer_title = section.section_title

        if buffer_tokens >= MIN_CHUNK_TOKENS:
            flush_buffer()

    flush_buffer()

    return chunks


def _split_large_text(
    text: str,
    start_index: int,
    page_number: int | None,
    section_title: str | None,
) -> list[Chunk]:
    """Split an oversized text block with overlap between chunks."""
    chunks: list[Chunk] = []
    target_chars = MIN_CHUNK_TOKENS * CHARS_PER_TOKEN
    overlap_chars = OVERLAP_TOKENS * CHARS_PER_TOKEN
    chunk_index = start_index

    pos = 0
    while pos < len(text):
        end = pos + target_chars

        if end < len(text):
            search_start = max(pos + target_chars - 500, pos)
            search_end = min(pos + MAX_CHUNK_TOKENS * CHARS_PER_TOKEN, len(text))
            segment = text[search_start:search_end]

            for pattern in [". ", ".\n", "\n\n", "\n"]:
                last_break = segment.rfind(pattern)
                if last_break != -1:
                    end = search_start + last_break + len(pattern)
                    break

        chunk_text = text[pos:end].strip()
        if chunk_text:
            chunks.append(
                Chunk(
                    content=chunk_text,
                    chunk_index=chunk_index,
                    token_count=estimate_tokens(chunk_text),
                    page_number=page_number,
                    section_title=section_title,
                )
            )
            chunk_index += 1

        pos = end - overlap_chars if end < len(text) else end

    return chunks
