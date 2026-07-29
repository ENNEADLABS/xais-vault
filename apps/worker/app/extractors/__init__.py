"""
Document extractors — convert uploaded files to plain text.

Each extractor returns an ExtractionResult with text content,
page count, word count, and optional metadata.

Supported formats: PDF, DOCX, XLSX/CSV, PPTX, TXT/MD.
"""

from dataclasses import dataclass, field


@dataclass
class ExtractionResult:
    """Result of a document text extraction."""
    text: str
    page_count: int
    word_count: int
    metadata: dict = field(default_factory=dict)


SUPPORTED_TYPES = {"pdf", "docx", "xlsx", "csv", "pptx", "txt", "md"}


async def extract(file_path: str, file_type: str) -> ExtractionResult:
    """Route extraction to the appropriate extractor based on file type."""
    if file_type not in SUPPORTED_TYPES:
        raise ValueError(f"Unsupported file type: {file_type}. Supported: {SUPPORTED_TYPES}")

    match file_type:
        case "pdf":
            from .pdf import extract_pdf
            return await extract_pdf(file_path)
        case "docx":
            from .docx import extract_docx
            return await extract_docx(file_path)
        case "xlsx" | "csv":
            from .xlsx import extract_xlsx
            return await extract_xlsx(file_path, file_type)
        case "pptx":
            from .pptx import extract_pptx
            return await extract_pptx(file_path)
        case "txt" | "md":
            from .text import extract_text
            return await extract_text(file_path)
        case _:
            raise ValueError(f"No extractor for type: {file_type}")
