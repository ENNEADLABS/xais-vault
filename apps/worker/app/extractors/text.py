"""
TXT/MD extractor — direct file read with encoding detection.
"""

import logging

from . import ExtractionResult

logger = logging.getLogger(__name__)


async def extract_text(file_path: str) -> ExtractionResult:
    """Extract text from a plain text or markdown file."""
    # Try UTF-8 first, fallback to latin-1
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1") as f:
            text = f.read()

    word_count = len(text.split())
    # Estimate pages (~500 words per page)
    page_count = max(1, word_count // 500)

    logger.info(f"Text extracted: ~{page_count} pages, {word_count} words — {file_path}")

    return ExtractionResult(
        text=text,
        page_count=page_count,
        word_count=word_count,
        metadata={"extractor": "direct_read"},
    )
