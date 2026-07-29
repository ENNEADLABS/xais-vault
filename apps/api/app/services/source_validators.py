"""
Source validation constants and helpers — flood limit, allowed types, size limit.
"""

from fastapi import HTTPException

ALLOWED_TYPES = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "docx",
    ".xlsx": "xlsx",
    ".xls": "xlsx",
    ".csv": "csv",
    ".pptx": "pptx",
    ".txt": "txt",
    ".md": "md",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_SOURCES_PER_WORKSPACE = 200  # Anti-flooding — évite la saturation du worker


def _check_source_flood_limit(db, workspace_id: str) -> None:
    """Lever 429 si le workspace a trop de sources (protection DoS)."""
    result = (
        db.table("sources").select("id", count="exact").eq("workspace_id", workspace_id).execute()
    )
    # result.count est un int en prod (supabase-py), ou MagicMock/None en tests.
    count = result.count if isinstance(result.count, int) else len(result.data or [])
    if count >= MAX_SOURCES_PER_WORKSPACE:
        raise HTTPException(
            status_code=429,
            detail=f"Too many sources in this workspace (max {MAX_SOURCES_PER_WORKSPACE}).",
        )
