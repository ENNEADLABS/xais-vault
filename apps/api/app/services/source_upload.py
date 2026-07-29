"""
Source upload service — file validation, storage, record creation.

Extracted from the sources router for the 200-line-per-file rule.
"""

import logging
import mimetypes
import re
from pathlib import Path

from fastapi import HTTPException, UploadFile
from uuid_extensions import uuid7str

from packages.db.client import require_one
from packages.db.job_queue import create_job

from .source_validators import (
    ALLOWED_TYPES,
    MAX_FILE_SIZE,
    _check_source_flood_limit,
)

logger = logging.getLogger(__name__)


async def upload_file_source(
    *,
    workspace_id: str,
    organization_id: str,
    user_id: str,
    file: UploadFile,
    db,
) -> tuple[dict, dict]:
    """Validate, store, and create a source record from an uploaded file.

    Returns (source_dict, job_dict).
    """
    require_one(
        db.table("workspaces")
        .select("id")
        .eq("id", workspace_id)
        .eq("organization_id", organization_id)
        .execute(),
        "Workspace",
    )

    _check_source_flood_limit(db, workspace_id)

    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_TYPES.keys())}",
        )

    # Lire MAX+1 octets — si le fichier dépasse la limite, on le détecte sans charger
    # tout le contenu en RAM (évite le DoS via upload de fichiers géants).
    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum: {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    source_id = uuid7str()
    # Sanitize filename for Supabase Storage (no brackets, special chars)
    safe_name = Path(filename).stem
    safe_name = re.sub(r"[^\w\s\-.]", "", safe_name).strip()
    safe_name = re.sub(r"\s+", "_", safe_name)
    safe_filename = f"{safe_name}{ext}" if safe_name else f"file{ext}"
    storage_path = f"{organization_id}/{workspace_id}/{source_id}/{safe_filename}"

    content_type = (
        file.content_type
        or mimetypes.guess_type(filename)[0]
        or "application/octet-stream"
    )

    try:
        db.storage.from_("sources").upload(
            storage_path,
            content,
            file_options={"content-type": content_type},
        )
    except Exception:
        logger.exception("Storage upload failed for %s", storage_path)
        raise HTTPException(status_code=500, detail="Failed to upload file")

    try:
        result = (
            db.table("sources")
            .insert(
                {
                    "id": source_id,
                    "workspace_id": workspace_id,
                    "organization_id": organization_id,
                    "uploaded_by": user_id,
                    "name": filename,
                    "type": ALLOWED_TYPES[ext],
                    "file_path": storage_path,
                    "file_size_bytes": len(content),
                    "status": "pending",
                }
            )
            .execute()
        )
    except Exception:
        logger.exception("DB insert failed for source %s", source_id)
        raise HTTPException(status_code=500, detail="Failed to create source record")

    source = require_one(result, "Source")

    try:
        job = await create_job(
            db,
            type="index_source",
            payload={"source_id": source_id, "workspace_id": workspace_id},
            organization_id=organization_id,
        )
    except Exception:
        logger.exception("Job creation failed for source %s", source_id)
        raise HTTPException(status_code=500, detail="Failed to create job")

    return source, job


async def add_text_source(
    *,
    workspace_id: str,
    organization_id: str,
    user_id: str,
    name: str,
    content: str,
    db,
) -> tuple[dict, dict]:
    """Create a source record from pasted text.

    Returns (source_dict, job_dict).
    """
    require_one(
        db.table("workspaces")
        .select("id")
        .eq("id", workspace_id)
        .eq("organization_id", organization_id)
        .execute(),
        "Workspace",
    )

    _check_source_flood_limit(db, workspace_id)

    source_id = uuid7str()

    result = (
        db.table("sources")
        .insert(
            {
                "id": source_id,
                "workspace_id": workspace_id,
                "organization_id": organization_id,
                "uploaded_by": user_id,
                "name": name,
                "type": "txt",
                "file_size_bytes": len(content.encode("utf-8")),
                "status": "pending",
                "extracted_text": content,
                "word_count": len(content.split()),
            }
        )
        .execute()
    )

    source = require_one(result, "Source")

    job = await create_job(
        db,
        type="index_source",
        payload={"source_id": source_id, "workspace_id": workspace_id, "skip_extraction": True},
        organization_id=organization_id,
    )

    return source, job
