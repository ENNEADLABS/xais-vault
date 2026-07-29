"""
Intelligent chunking — split documents into semantic chunks for embedding.

Strategy:
  1. Split on natural boundaries (page breaks, headings, double newlines)
  2. Merge small sections to reach target size (4000-6000 tokens)
  3. Split oversized sections with overlap for context continuity
  4. Preserve section titles for citation tracking

Token estimation: ~4 characters per token (conservative for mixed content).
"""

import logging

from .chunking_helpers import (
    CHARS_PER_TOKEN,
    MAX_CHUNK_TOKENS,
    MIN_CHUNK_TOKENS,
    OVERLAP_TOKENS,
    Chunk,
    _merge_and_split,
    _split_into_sections,
    _split_large_text,
    estimate_tokens,
)

logger = logging.getLogger(__name__)

# Re-export public API for backward compatibility
__all__ = [
    "CHARS_PER_TOKEN",
    "MAX_CHUNK_TOKENS",
    "MIN_CHUNK_TOKENS",
    "OVERLAP_TOKENS",
    "Chunk",
    "_split_large_text",
    "chunk_document",
    "estimate_tokens",
]


def chunk_document(text: str) -> list[Chunk]:
    """Split a document into semantic chunks of 4000-6000 tokens.

    Pipeline:
      1. Split into sections on natural boundaries
      2. Tag each section with page number and heading
      3. Merge small sections into target-size chunks
      4. Split oversized sections with overlap
    """
    if not text.strip():
        return []

    sections = _split_into_sections(text)
    chunks = _merge_and_split(sections)

    logger.info(
        f"Chunked document: {len(chunks)} chunks, "
        f"tokens range [{min(c.token_count for c in chunks)}-{max(c.token_count for c in chunks)}]"
    )
    return chunks
