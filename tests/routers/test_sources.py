"""
Tests for apps/api/app/routers/sources.py

All external dependencies are mocked:
  - Supabase DB via dependency override
  - upload_file_source / add_text_source patched directly
  - Auth via dependency override (bypasses JWT)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from apps.api.app.dependencies import (
    get_db,
    require_analyst,
    require_auth,
    require_viewer,
)
from apps.api.app.main import app
from apps.api.app.services.auth import AuthContext

# ─── Constants ─────────────────────────────────────────────────

ORG_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
DEAL_ID = str(uuid.uuid4())
SOURCE_ID = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()
BASE = f"/api/v2/workspaces/{DEAL_ID}/sources"


# ─── Helpers ───────────────────────────────────────────────────


def _make_source(**overrides) -> dict:
    base = {
        "id": SOURCE_ID,
        "workspace_id": DEAL_ID,
        "organization_id": ORG_ID,
        "name": "Report.pdf",
        "type": "pdf",
        "file_size_bytes": 1024,
        "status": "pending",
        "error_message": None,
        "page_count": None,
        "word_count": None,
        "summary": None,
        "topics": None,
        "suggested_questions": None,
        "uploaded_by": USER_ID,
        "created_at": NOW,
    }
    return {**base, **overrides}


def _make_auth(role: str = "analyst") -> AuthContext:
    return AuthContext(
        user_id=USER_ID, organization_id=ORG_ID, role=role, auth_method="jwt"
    )


def _db_with_select(rows: list[dict]) -> MagicMock:
    db = MagicMock()
    chain = MagicMock()
    for m in ("select", "eq", "order", "update", "delete"):
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(data=rows)
    db.table.return_value = chain
    db.storage = MagicMock()
    return db


def _override_auth(role: str = "analyst"):
    auth = _make_auth(role)

    async def _dep():
        return auth

    app.dependency_overrides[require_auth] = _dep
    return _dep


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ─── Upload File ────────────────────────────────────────────────


@pytest.mark.asyncio
class TestUploadFileSource:
    async def test_upload_pdf_returns_202(self, client):
        """POST / with a file returns 202 with source data and job_id."""
        source = _make_source()
        job = {"id": "job-upload-1"}
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            with patch(
                "apps.api.app.routers.sources.upload_file_source",
                new_callable=AsyncMock,
                return_value=(source, job),
            ):
                r = await client.post(
                    f"{BASE}/",
                    files={"file": ("test.pdf", b"PDF content", "application/pdf")},
                )
            assert r.status_code == 202
            body = r.json()
            assert body["data"]["id"] == SOURCE_ID
            assert body["meta"]["job_id"] == "job-upload-1"
        finally:
            app.dependency_overrides.clear()

    async def test_upload_unsupported_type(self, client):
        """POST / returns 400 when file type is not supported."""
        from fastapi import HTTPException

        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            with patch(
                "apps.api.app.routers.sources.upload_file_source",
                new_callable=AsyncMock,
                side_effect=HTTPException(
                    status_code=400, detail="Unsupported file type"
                ),
            ):
                r = await client.post(
                    f"{BASE}/",
                    files={"file": ("test.exe", b"bad", "application/octet-stream")},
                )
            assert r.status_code == 400
        finally:
            app.dependency_overrides.clear()

    async def test_upload_too_large(self, client):
        """POST / returns 400 when file exceeds size limit."""
        from fastapi import HTTPException

        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            with patch(
                "apps.api.app.routers.sources.upload_file_source",
                new_callable=AsyncMock,
                side_effect=HTTPException(status_code=400, detail="File too large"),
            ):
                r = await client.post(
                    f"{BASE}/",
                    files={"file": ("big.pdf", b"x" * 100, "application/pdf")},
                )
            assert r.status_code == 400
        finally:
            app.dependency_overrides.clear()


# ─── Add Text ───────────────────────────────────────────────────


@pytest.mark.asyncio
class TestAddTextSource:
    async def test_add_text_returns_202(self, client):
        """POST /text with valid body returns 202."""
        source = _make_source(name="Notes", type="txt")
        job = {"id": "job-text-1"}
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            with patch(
                "apps.api.app.routers.sources.add_text_source",
                new_callable=AsyncMock,
                return_value=(source, job),
            ):
                r = await client.post(
                    f"{BASE}/text",
                    json={"name": "Notes", "content": "Important notes here"},
                )
            assert r.status_code == 202
            assert r.json()["meta"]["job_id"] == "job-text-1"
        finally:
            app.dependency_overrides.clear()

    async def test_add_text_empty_content(self, client):
        """POST /text with empty content returns 422."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.post(f"{BASE}/text", json={"name": "Notes", "content": ""})
            assert r.status_code == 422
        finally:
            app.dependency_overrides.clear()


# ─── List Sources ───────────────────────────────────────────────


@pytest.mark.asyncio
class TestListSources:
    async def test_list_empty(self, client):
        """GET / returns 200 with empty list."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get(f"{BASE}/")
            assert r.status_code == 200
            assert r.json()["data"] == []
        finally:
            app.dependency_overrides.clear()

    async def test_list_with_sources(self, client):
        """GET / returns sources with all fields."""
        db = _db_with_select([_make_source()])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get(f"{BASE}/")
            assert r.status_code == 200
            assert r.json()["data"][0]["id"] == SOURCE_ID
        finally:
            app.dependency_overrides.clear()


# ─── Get Source ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestGetSource:
    async def test_get_success(self, client):
        """GET /{source_id} returns 200."""
        db = _db_with_select([_make_source()])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get(f"{BASE}/{SOURCE_ID}")
            assert r.status_code == 200
            assert r.json()["data"]["id"] == SOURCE_ID
        finally:
            app.dependency_overrides.clear()

    async def test_get_not_found(self, client):
        """GET /{source_id} returns 404 for unknown ID."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get(f"{BASE}/{uuid.uuid4()}")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ─── Reprocess ──────────────────────────────────────────────────


@pytest.mark.asyncio
class TestReprocessSource:
    async def test_reprocess_returns_202(self, client):
        """POST /{source_id}/reprocess returns 202 with job_id."""
        db = _db_with_select([_make_source()])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            with patch(
                "apps.api.app.routers.sources.create_job",
                new_callable=AsyncMock,
                return_value={"id": "job-reprocess-1"},
            ):
                r = await client.post(f"{BASE}/{SOURCE_ID}/reprocess")
            assert r.status_code == 202
            assert r.json()["job_id"] == "job-reprocess-1"
        finally:
            app.dependency_overrides.clear()

    async def test_reprocess_not_found(self, client):
        """POST /{source_id}/reprocess returns 404 for unknown source."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.post(f"{BASE}/{uuid.uuid4()}/reprocess")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ─── Delete ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDeleteSource:
    async def test_delete_success(self, client):
        """DELETE /{source_id} returns 204."""
        db = _db_with_select([_make_source(file_path=None)])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.delete(f"{BASE}/{SOURCE_ID}")
            assert r.status_code == 204
        finally:
            app.dependency_overrides.clear()

    async def test_delete_not_found(self, client):
        """DELETE /{source_id} returns 404 for unknown source."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.delete(f"{BASE}/{uuid.uuid4()}")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_delete_with_file_path(self, client):
        """DELETE /{source_id} calls storage.remove when file_path is set."""
        source = _make_source(file_path="sources/org/file.pdf")
        db = _db_with_select([source])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.delete(f"{BASE}/{SOURCE_ID}")
            assert r.status_code == 204
            db.storage.from_.assert_called_once_with("sources")
            db.storage.from_.return_value.remove.assert_called_once_with(
                ["sources/org/file.pdf"]
            )
        finally:
            app.dependency_overrides.clear()
