"""
Sources router — file upload, text paste, CRUD.

Upload logic extracted to services/source_upload.py.
"""

from fastapi import APIRouter, Depends, File, UploadFile

from packages.db.client import require_one, safe_get_list
from packages.db.job_queue import create_job

from ..dependencies import DB, AnalystAuth, ViewerAuth, require_scope_dep
from ..models.common import ApiResponse, JobAccepted
from ..models.source import SourceResponse, SourceTextCreate
from ..services.source_upload import add_text_source, upload_file_source

router = APIRouter()


@router.post(
    "/",
    status_code=202,
    dependencies=[Depends(require_scope_dep("sources:write"))],
)
async def upload_source(
    workspace_id: str,
    auth: AnalystAuth,
    db: DB,
    file: UploadFile = File(...),
):
    """Upload a file as a source. Returns 202 Accepted."""
    source, job = await upload_file_source(
        workspace_id=workspace_id,
        organization_id=auth.organization_id,
        user_id=auth.user_id,
        file=file,
        db=db,
    )
    return ApiResponse(
        data=SourceResponse(**source),
        meta={"job_id": job["id"]},
    )


@router.post(
    "/text",
    status_code=202,
    dependencies=[Depends(require_scope_dep("sources:write"))],
)
async def add_text(
    workspace_id: str,
    body: SourceTextCreate,
    auth: AnalystAuth,
    db: DB,
):
    """Add pasted text as a source. Returns 202 Accepted."""
    source, job = await add_text_source(
        workspace_id=workspace_id,
        organization_id=auth.organization_id,
        user_id=auth.user_id,
        name=body.name,
        content=body.content,
        db=db,
    )
    return ApiResponse(
        data=SourceResponse(**source),
        meta={"job_id": job["id"]},
    )


@router.get("/", dependencies=[Depends(require_scope_dep("sources:read"))])
async def list_sources(workspace_id: str, auth: ViewerAuth, db: DB):
    """List all sources in a workspace."""
    sources = safe_get_list(
        db.table("sources")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .order("created_at", desc=True)
        .execute()
    )
    return ApiResponse(data=[SourceResponse(**s) for s in sources])


@router.get(
    "/{source_id}",
    dependencies=[Depends(require_scope_dep("sources:read"))],
)
async def get_source(workspace_id: str, source_id: str, auth: ViewerAuth, db: DB):
    """Get a single source with full details."""
    source = require_one(
        db.table("sources")
        .select("*")
        .eq("id", source_id)
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Source",
    )
    return ApiResponse(data=SourceResponse(**source))


@router.post(
    "/{source_id}/reprocess",
    status_code=202,
    dependencies=[Depends(require_scope_dep("sources:write"))],
)
async def reprocess_source(workspace_id: str, source_id: str, auth: AnalystAuth, db: DB):
    """Re-trigger processing for a failed or outdated source."""
    require_one(
        db.table("sources")
        .select("id, status")
        .eq("id", source_id)
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Source",
    )

    db.table("sources").update(
        {
            "status": "pending",
            "error_message": None,
        }
    ).eq("id", source_id).execute()

    db.table("chunks").delete().eq("source_id", source_id).execute()

    job = await create_job(
        db,
        type="index_source",
        payload={"source_id": source_id, "workspace_id": workspace_id},
        organization_id=auth.organization_id,
    )
    return JobAccepted(job_id=job["id"])


@router.delete(
    "/{source_id}",
    status_code=204,
    dependencies=[Depends(require_scope_dep("sources:write"))],
)
async def delete_source(workspace_id: str, source_id: str, auth: AnalystAuth, db: DB):
    """Delete a source and its chunks (CASCADE)."""
    source = require_one(
        db.table("sources")
        .select("id, file_path")
        .eq("id", source_id)
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute(),
        "Source",
    )

    if source.get("file_path"):
        try:
            db.storage.from_("sources").remove([source["file_path"]])
        except Exception:
            pass

    db.table("sources").delete().eq("id", source_id).execute()
