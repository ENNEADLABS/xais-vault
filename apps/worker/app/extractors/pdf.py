"""
PDF extractor — uses PyMuPDF (fitz) for fast, accurate text extraction.
Preserves page boundaries for citation tracking.
"""

import logging

import fitz  # PyMuPDF

from . import ExtractionResult

logger = logging.getLogger(__name__)


async def extract_pdf(file_path: str) -> ExtractionResult:
    """Extract text from a PDF file, preserving page structure."""
    doc = fitz.open(file_path)
    pages: list[str] = []

    try:
        for page in doc:
            text = page.get_text("text")
            if text.strip():
                pages.append(text)
    finally:
        doc.close()

    full_text = "\n\n--- PAGE BREAK ---\n\n".join(pages)
    word_count = len(full_text.split())

    logger.info(f"PDF extracted: {len(pages)} pages, {word_count} words — {file_path}")

    return ExtractionResult(
        text=full_text,
        page_count=len(pages),
        word_count=word_count,
        metadata={"extractor": "pymupdf"},
    )
