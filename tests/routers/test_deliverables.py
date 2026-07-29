"""
Tests pour apps/api/app/routers/deliverables.py

Toutes les dépendances externes sont mockées :
  - Supabase DB via dependency override
  - Auth via dependency override (bypasse JWT)
  - create_job et check_analysis_limit via patch
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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
DELIVERABLE_ID = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()


# ─── Helpers ───────────────────────────────────────────────────


def _make_deliverable(**overrides) -> dict:
    base = {
        "id": DELIVERABLE_ID,
        "workspace_id": DEAL_ID,
        "organization_id": ORG_ID,
        "generated_by": USER_ID,
        "type": "executive_summary",
        "name": "Résumé Acme",
        "status": "completed",
        "content_markdown": None,
        "file_path": "deliverables/acme.docx",
        "file_size_bytes": 12345,
        "options": {},
        "current_step": None,
        "progress_percent": 100,
        "error_message": None,
        "created_at": NOW,
        "completed_at": NOW,
    }
    return {**base, **overrides}


def _make_auth(role: str = "analyst") -> AuthContext:
    return AuthContext(
        user_id=USER_ID, organization_id=ORG_ID, role=role, auth_method="jwt"
    )


def _override_auth(role: str = "analyst"):
    auth = _make_auth(role)
    dep = lambda: auth  # noqa: E731
    app.dependency_overrides[require_auth] = dep
    return dep


def _db_with_table_dispatch(table_rows: dict[str, list]) -> MagicMock:
    """Mock DB retournant différentes données selon la table."""
    db = MagicMock()

    def make_chain(rows: list) -> MagicMock:
        chain = MagicMock()
        for m in ("select", "eq", "order", "insert", "limit"):
            getattr(chain, m).return_value = chain
        result = MagicMock(data=rows)
        result.count = len(rows)
        chain.execute.return_value = result
        return chain

    def side_effect(name: str) -> MagicMock:
        rows = table_rows.get(name, [])
        return make_chain(rows)

    db.table.side_effect = side_effect
    return db


def _db_for_list(deal_row: dict, deliverables: list[dict]) -> MagicMock:
    """Mock DB pour list_deliverables : workspaces → 1 row, deliverables → N rows."""
    return _db_with_table_dispatch(
        {
            "workspaces": [deal_row],
            "deliverables": deliverables,
        }
    )


def _db_for_download(deliverable: dict) -> MagicMock:
    """Mock DB pour download : retourne le deliverable + mock storage."""
    db = _db_with_table_dispatch({"deliverables": [deliverable]})
    storage_bucket = MagicMock()
    storage_bucket.download.return_value = b"fake-docx-content"
    db.storage.from_.return_value = storage_bucket
    return db


# ─── GET /workspaces/{id}/deliverables ──────────────────────────────


@pytest.mark.asyncio
class TestListDeliverables:
    async def test_list_success(self):
        """Liste les deliverables d'un workspace existant."""
        deliverables = [_make_deliverable(), _make_deliverable(id=str(uuid.uuid4()))]
        db = _db_for_list({"id": DEAL_ID}, deliverables)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                r = await ac.get(f"/api/v2/workspaces/{DEAL_ID}/deliverables/")
            assert r.status_code == 200
            data = r.json()["data"]
            assert len(data) == 2
            assert data[0]["type"] == "executive_summary"
        finally:
            app.dependency_overrides.clear()

    async def test_list_empty(self):
        """Retourne une liste vide si aucun deliverable."""
        db = _db_for_list({"id": DEAL_ID}, [])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                r = await ac.get(f"/api/v2/workspaces/{DEAL_ID}/deliverables/")
            assert r.status_code == 200
            assert r.json()["data"] == []
        finally:
            app.dependency_overrides.clear()

    async def test_list_deal_not_found(self):
        """404 si le workspace n'existe pas."""
        db = _db_with_table_dispatch({"workspaces": [], "deliverables": []})
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                r = await ac.get(f"/api/v2/workspaces/{DEAL_ID}/deliverables/")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ─── POST /workspaces/{id}/deliverables ─────────────────────────────


@pytest.mark.asyncio
class TestCreateDeliverable:
    async def test_create_success(self):
        """POST crée un deliverable et retourne 202 avec job_id."""
        deliverable = _make_deliverable(status="pending")
        job = {
            "id": str(uuid.uuid4()),
            "type": "generate_deliverable",
            "status": "pending",
        }
        db = _db_with_table_dispatch(
            {
                "workspaces": [{"id": DEAL_ID}],
                "deliverables": [deliverable],
            }
        )
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth("analyst")
        try:
            with (
                patch(
                    "apps.api.app.routers.deliverables.check_analysis_limit",
                    new_callable=AsyncMock,
                ),
                patch(
                    "apps.api.app.routers.deliverables.create_job",
                    new_callable=AsyncMock,
                    return_value=job,
                ),
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as ac:
                    r = await ac.post(
                        f"/api/v2/workspaces/{DEAL_ID}/deliverables/",
                        json={"type": "executive_summary", "name": "Mon résumé"},
                    )
            assert r.status_code == 202
            body = r.json()
            assert body["data"]["type"] == "executive_summary"
            assert body["meta"]["job_id"] == job["id"]
        finally:
            app.dependency_overrides.clear()

    async def test_create_deal_not_found(self):
        """404 si le workspace n'existe pas."""
        db = _db_with_table_dispatch({"workspaces": [], "deliverables": []})
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth("analyst")
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                r = await ac.post(
                    f"/api/v2/workspaces/{DEAL_ID}/deliverables/",
                    json={"type": "dd_report", "name": "DD"},
                )
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_create_invalid_type(self):
        """422 si le type est invalide."""
        db = MagicMock()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth("analyst")
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                r = await ac.post(
                    f"/api/v2/workspaces/{DEAL_ID}/deliverables/",
                    json={"type": "invalid_type", "name": "Test"},
                )
            assert r.status_code == 422
        finally:
            app.dependency_overrides.clear()


# ─── GET /workspaces/{id}/deliverables/{deliverable_id} ─────────────


@pytest.mark.asyncio
class TestGetDeliverable:
    async def test_get_success(self):
        """Retourne un deliverable par ID."""
        deliverable = _make_deliverable()
        db = _db_with_table_dispatch({"deliverables": [deliverable]})
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                r = await ac.get(
                    f"/api/v2/workspaces/{DEAL_ID}/deliverables/{DELIVERABLE_ID}"
                )
            assert r.status_code == 200
            assert r.json()["data"]["id"] == DELIVERABLE_ID
        finally:
            app.dependency_overrides.clear()

    async def test_get_not_found(self):
        """404 si le deliverable n'existe pas."""
        db = _db_with_table_dispatch({"deliverables": []})
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                r = await ac.get(
                    f"/api/v2/workspaces/{DEAL_ID}/deliverables/{str(uuid.uuid4())}"
                )
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ─── GET /workspaces/{id}/deliverables/{id}/download ────────────────


@pytest.mark.asyncio
class TestDownloadDeliverable:
    async def test_download_success(self):
        """Télécharge un DOCX terminé."""
        deliverable = _make_deliverable(
            status="completed", file_path="path/to/file.docx"
        )
        db = _db_for_download(deliverable)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                r = await ac.get(
                    f"/api/v2/workspaces/{DEAL_ID}/deliverables/{DELIVERABLE_ID}/download"
                )
            assert r.status_code == 200
            assert "attachment" in r.headers["content-disposition"]
            assert r.content == b"fake-docx-content"
        finally:
            app.dependency_overrides.clear()

    async def test_download_not_ready(self):
        """400 si le deliverable n'est pas terminé."""
        deliverable = _make_deliverable(status="pending")
        db = _db_with_table_dispatch({"deliverables": [deliverable]})
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                r = await ac.get(
                    f"/api/v2/workspaces/{DEAL_ID}/deliverables/{DELIVERABLE_ID}/download"
                )
            assert r.status_code == 400
        finally:
            app.dependency_overrides.clear()

    async def test_download_no_file_path(self):
        """404 si file_path est None."""
        deliverable = _make_deliverable(status="completed", file_path=None)
        db = _db_with_table_dispatch({"deliverables": [deliverable]})
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                r = await ac.get(
                    f"/api/v2/workspaces/{DEAL_ID}/deliverables/{DELIVERABLE_ID}/download"
                )
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_download_storage_error(self):
        """500 si le storage échoue."""
        deliverable = _make_deliverable(
            status="completed", file_path="path/to/file.docx"
        )
        db = _db_with_table_dispatch({"deliverables": [deliverable]})
        storage_bucket = MagicMock()
        storage_bucket.download.side_effect = RuntimeError("Storage down")
        db.storage.from_.return_value = storage_bucket
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                r = await ac.get(
                    f"/api/v2/workspaces/{DEAL_ID}/deliverables/{DELIVERABLE_ID}/download"
                )
            assert r.status_code == 500
        finally:
            app.dependency_overrides.clear()

    async def test_download_sanitizes_filename(self):
        """Le nom de fichier est nettoyé pour Content-Disposition."""
        deliverable = _make_deliverable(
            status="completed",
            file_path="path/to/file.docx",
            name='Résumé "Acme" <Corp>',
        )
        db = _db_for_download(deliverable)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                r = await ac.get(
                    f"/api/v2/workspaces/{DEAL_ID}/deliverables/{DELIVERABLE_ID}/download"
                )
            assert r.status_code == 200
            # Pas de guillemets ni chevrons dans le nom
            disposition = r.headers["content-disposition"]
            assert "<" not in disposition
            assert ">" not in disposition
        finally:
            app.dependency_overrides.clear()

    async def test_download_not_found(self):
        """404 si le deliverable n'existe pas."""
        db = _db_with_table_dispatch({"deliverables": []})
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                r = await ac.get(
                    f"/api/v2/workspaces/{DEAL_ID}/deliverables/{str(uuid.uuid4())}/download"
                )
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()
