"""
Tests for apps/api/app/services/source_upload.py.

Supabase DB and job queue are mocked — no external calls.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from apps.api.app.services.source_upload import add_text_source, upload_file_source

DEAL_ID = str(uuid.uuid4())
ORG_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
SOURCE_ROW = {
    "id": str(uuid.uuid4()),
    "workspace_id": DEAL_ID,
    "organization_id": ORG_ID,
    "name": "test.pdf",
    "type": "pdf",
    "status": "pending",
}
JOB_ROW = {"id": str(uuid.uuid4()), "type": "index_source", "status": "pending"}


# ─── Helpers ──────────────────────────────────────────────────


def _make_upload_file(
    filename: str = "report.pdf",
    content: bytes = b"fake pdf",
    content_type: str = "application/pdf",
):
    f = MagicMock()
    f.filename = filename
    f.content_type = content_type
    f.read = AsyncMock(return_value=content)
    return f


def _make_db(*, deal_exists: bool = True, insert_data=None, storage_raises=None, insert_raises=None):
    """Build a Supabase mock for source_upload tests."""
    db = MagicMock()

    # workspaces chain
    deals_chain = MagicMock()
    for m in ("select", "eq"):
        getattr(deals_chain, m).return_value = deals_chain
    deals_chain.execute.return_value = MagicMock(
        data=[{"id": DEAL_ID}] if deal_exists else []
    )

    # sources insert chain
    sources_chain = MagicMock()
    if insert_raises:
        sources_chain.insert.side_effect = insert_raises
    else:
        row = insert_data or SOURCE_ROW
        sources_chain.insert.return_value.execute.return_value = MagicMock(data=[row])

    def table_side_effect(name):
        if name == "workspaces":
            return deals_chain
        return sources_chain

    db.table.side_effect = table_side_effect

    # storage
    if storage_raises:
        db.storage.from_.return_value.upload.side_effect = storage_raises

    return db


# ─── upload_file_source ────────────────────────────────────────


class TestUploadFileSource:
    @pytest.mark.asyncio
    @patch("apps.api.app.services.source_upload.create_job", new_callable=AsyncMock)
    async def test_valid_pdf_creates_source_and_job(self, mock_create_job):
        """Happy path: valid PDF returns (source, job) tuple."""
        mock_create_job.return_value = JOB_ROW
        db = _make_db()
        f = _make_upload_file("report.pdf", b"x" * 100)

        source, job = await upload_file_source(
            workspace_id=DEAL_ID, organization_id=ORG_ID, user_id=USER_ID, file=f, db=db,
        )

        assert source["status"] == "pending"
        mock_create_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsupported_extension_raises_400(self):
        """Unknown file extension raises HTTPException 400."""
        db = _make_db()
        f = _make_upload_file("virus.exe", b"data")

        with pytest.raises(HTTPException) as exc:
            await upload_file_source(
                workspace_id=DEAL_ID, organization_id=ORG_ID, user_id=USER_ID, file=f, db=db,
            )
        assert exc.value.status_code == 400
        assert ".exe" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_file_too_large_raises_400(self):
        """File over 50 MB raises HTTPException 400."""
        db = _make_db()
        big_content = b"x" * (51 * 1024 * 1024)  # 51 MB
        f = _make_upload_file("big.pdf", big_content)

        with pytest.raises(HTTPException) as exc:
            await upload_file_source(
                workspace_id=DEAL_ID, organization_id=ORG_ID, user_id=USER_ID, file=f, db=db,
            )
        assert exc.value.status_code == 400
        assert "too large" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_storage_upload_failure_raises_500(self):
        """Storage failure raises HTTPException 500."""
        db = _make_db(storage_raises=Exception("Bucket full"))
        f = _make_upload_file()

        with pytest.raises(HTTPException) as exc:
            await upload_file_source(
                workspace_id=DEAL_ID, organization_id=ORG_ID, user_id=USER_ID, file=f, db=db,
            )
        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_db_insert_failure_raises_500(self):
        """DB insert failure raises HTTPException 500."""
        db = _make_db(insert_raises=Exception("DB error"))
        f = _make_upload_file()

        with pytest.raises(HTTPException) as exc:
            await upload_file_source(
                workspace_id=DEAL_ID, organization_id=ORG_ID, user_id=USER_ID, file=f, db=db,
            )
        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    @patch("apps.api.app.services.source_upload.create_job", new_callable=AsyncMock)
    async def test_sanitizes_filename_special_chars(self, mock_create_job):
        """Storage path uses sanitized filename without special characters."""
        mock_create_job.return_value = JOB_ROW
        db = _make_db()
        f = _make_upload_file("report [2024] (final)!.pdf", b"data")

        await upload_file_source(
            workspace_id=DEAL_ID, organization_id=ORG_ID, user_id=USER_ID, file=f, db=db,
        )

        upload_call = db.storage.from_.return_value.upload.call_args
        storage_path = upload_call.args[0]
        assert "[" not in storage_path
        assert "]" not in storage_path
        assert "(" not in storage_path
        assert "!" not in storage_path

    @pytest.mark.asyncio
    async def test_deal_not_found_raises_404(self):
        """Missing workspace raises HTTPException 404."""
        db = _make_db(deal_exists=False)
        f = _make_upload_file()

        with pytest.raises(HTTPException) as exc:
            await upload_file_source(
                workspace_id=DEAL_ID, organization_id=ORG_ID, user_id=USER_ID, file=f, db=db,
            )
        assert exc.value.status_code == 404


# ─── add_text_source ──────────────────────────────────────────


class TestAddTextSource:
    @pytest.mark.asyncio
    @patch("apps.api.app.services.source_upload.create_job", new_callable=AsyncMock)
    async def test_creates_source_with_extracted_text(self, mock_create_job):
        """Text source stores the pasted content in extracted_text."""
        mock_create_job.return_value = JOB_ROW
        text_row = {**SOURCE_ROW, "type": "txt", "extracted_text": "Hello world"}
        db = _make_db(insert_data=text_row)

        source, _ = await add_text_source(
            workspace_id=DEAL_ID, organization_id=ORG_ID, user_id=USER_ID,
            name="pasted.txt", content="Hello world", db=db,
        )

        assert source["type"] == "txt"

    @pytest.mark.asyncio
    @patch("apps.api.app.services.source_upload.create_job", new_callable=AsyncMock)
    async def test_creates_job_with_skip_extraction_flag(self, mock_create_job):
        """Job payload includes skip_extraction=True for text sources."""
        mock_create_job.return_value = JOB_ROW
        db = _make_db()

        await add_text_source(
            workspace_id=DEAL_ID, organization_id=ORG_ID, user_id=USER_ID,
            name="notes.txt", content="Investment notes", db=db,
        )

        call_kwargs = mock_create_job.call_args.kwargs
        assert call_kwargs["payload"]["skip_extraction"] is True

    @pytest.mark.asyncio
    async def test_deal_not_found_raises_404(self):
        """Missing workspace raises HTTPException 404."""
        db = _make_db(deal_exists=False)

        with pytest.raises(HTTPException) as exc:
            await add_text_source(
                workspace_id=DEAL_ID, organization_id=ORG_ID, user_id=USER_ID,
                name="notes.txt", content="content", db=db,
            )
        assert exc.value.status_code == 404
