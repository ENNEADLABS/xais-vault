"""
Tests for the Notes router (apps/api/app/routers/notes.py).

All external dependencies are mocked:
  - Supabase DB via dependency override
  - Auth via dependency override (bypasses JWT)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

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

# ─── Fixtures ──────────────────────────────────────────────────

ORG_ID = str(uuid.uuid4())
DEAL_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
NOTE_ID = str(uuid.uuid4())

NOW = datetime.now(timezone.utc).isoformat()


def _make_auth() -> AuthContext:
    return AuthContext(
        user_id=USER_ID,
        organization_id=ORG_ID,
        role="analyst",
    )


def _make_note(**overrides) -> dict:
    base = {
        "id": NOTE_ID,
        "workspace_id": DEAL_ID,
        "organization_id": ORG_ID,
        "user_id": USER_ID,
        "title": None,
        "content": "Test note content",
        "tags": [],
        "is_pinned": False,
        "checklist_items": None,
        "linked_source_id": None,
        "linked_insight_id": None,
        "linked_message_id": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    return {**base, **overrides}


def _make_db(
    *,
    deal_exists: bool = True,
    note_exists: bool = True,
    notes: list[dict] | None = None,
    created_note: dict | None = None,
    updated_note: dict | None = None,
) -> MagicMock:
    """Build a minimal Supabase mock for notes tests."""
    db = MagicMock()
    note = created_note or updated_note or _make_note()

    # Default: all chained calls return self until execute()
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.contains.return_value = chain
    chain.order.return_value = chain
    chain.update.return_value = chain
    chain.insert.return_value = chain
    chain.delete.return_value = chain

    def _execute():
        return chain._execute_result

    chain.execute.side_effect = _execute
    db.table.return_value = chain

    # Track call sequence for multi-execute tests
    call_count = [0]

    def _get_result():
        idx = call_count[0]
        call_count[0] += 1

        if idx == 0:
            # First call = workspace existence check
            return MagicMock(data=[{"id": DEAL_ID}] if deal_exists else [])
        if idx == 1:
            # Second call = note existence check (for PATCH/DELETE)
            if note_exists:
                return MagicMock(data=[_make_note()])
            return MagicMock(data=[])
        # Subsequent calls = insert/update result
        return MagicMock(data=[note])

    # For list_notes: first call = workspace check, second = note list
    def _get_list_result():
        idx = call_count[0]
        call_count[0] += 1
        if idx == 0:
            return MagicMock(data=[{"id": DEAL_ID}] if deal_exists else [])
        return MagicMock(data=notes or [])

    chain._execute_result = MagicMock(data=[])
    chain.execute.side_effect = _get_result

    return db, chain, _get_list_result, _get_result


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


def override_auth(role: str = "analyst"):
    auth = _make_auth()
    auth.role = role

    async def _dep():
        return auth

    app.dependency_overrides[require_auth] = _dep
    return _dep


# ─── Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestListNotes:
    async def test_list_notes_empty(self, client):
        """GET /notes returns [] when no notes exist."""
        db = MagicMock()
        call_n = [0]

        def execute():
            n = call_n[0]
            call_n[0] += 1
            return MagicMock(data=[{"id": DEAL_ID}] if n == 0 else [])

        chain = MagicMock()
        for m in ("select", "eq", "contains", "order"):
            getattr(chain, m).return_value = chain
        chain.execute.side_effect = execute
        db.table.return_value = chain

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = override_auth()
        try:
            r = await client.get(f"/api/v2/workspaces/{DEAL_ID}/notes/")
            assert r.status_code == 200
            assert r.json()["data"] == []
        finally:
            app.dependency_overrides.clear()

    async def test_list_notes_with_results(self, client):
        """GET /notes returns existing notes."""
        notes = [
            _make_note(title="Note A"),
            _make_note(id=str(uuid.uuid4()), title="Note B"),
        ]
        db = MagicMock()
        call_n = [0]

        def execute():
            n = call_n[0]
            call_n[0] += 1
            return MagicMock(data=[{"id": DEAL_ID}] if n == 0 else notes)

        chain = MagicMock()
        for m in ("select", "eq", "contains", "order"):
            getattr(chain, m).return_value = chain
        chain.execute.side_effect = execute
        db.table.return_value = chain

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = override_auth()
        try:
            r = await client.get(f"/api/v2/workspaces/{DEAL_ID}/notes/")
            assert r.status_code == 200
            assert len(r.json()["data"]) == 2
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestCreateNote:
    async def test_create_note_minimal(self, client):
        """POST with content only returns 201."""
        created = _make_note(content="Minimal note")
        db = MagicMock()
        call_n = [0]

        def execute():
            n = call_n[0]
            call_n[0] += 1
            return MagicMock(data=[{"id": DEAL_ID}] if n == 0 else [created])

        chain = MagicMock()
        for m in ("select", "eq", "insert"):
            getattr(chain, m).return_value = chain
        chain.execute.side_effect = execute
        db.table.return_value = chain

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_auth()
        try:
            r = await client.post(
                f"/api/v2/workspaces/{DEAL_ID}/notes/",
                json={"content": "Minimal note"},
            )
            assert r.status_code == 201
            assert r.json()["data"]["content"] == "Minimal note"
        finally:
            app.dependency_overrides.clear()

    async def test_create_note_full(self, client):
        """POST with all fields returns 201."""
        note_id = str(uuid.uuid4())
        created = _make_note(
            id=note_id,
            title="Full note",
            content="Rich content",
            tags=["finance", "risk"],
            is_pinned=True,
        )
        db = MagicMock()
        call_n = [0]

        def execute():
            n = call_n[0]
            call_n[0] += 1
            return MagicMock(data=[{"id": DEAL_ID}] if n == 0 else [created])

        chain = MagicMock()
        for m in ("select", "eq", "insert"):
            getattr(chain, m).return_value = chain
        chain.execute.side_effect = execute
        db.table.return_value = chain

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_auth()
        try:
            r = await client.post(
                f"/api/v2/workspaces/{DEAL_ID}/notes/",
                json={
                    "title": "Full note",
                    "content": "Rich content",
                    "tags": ["finance", "risk"],
                    "is_pinned": True,
                },
            )
            assert r.status_code == 201
            assert r.json()["data"]["tags"] == ["finance", "risk"]
            assert r.json()["data"]["is_pinned"] is True
        finally:
            app.dependency_overrides.clear()

    async def test_create_note_with_checklist(self, client):
        """POST with checklist_items persists JSONB structure."""
        items = [
            {"text": "Step 1", "checked": False},
            {"text": "Step 2", "checked": True},
        ]
        created = _make_note(checklist_items=items)
        db = MagicMock()
        call_n = [0]

        def execute():
            n = call_n[0]
            call_n[0] += 1
            return MagicMock(data=[{"id": DEAL_ID}] if n == 0 else [created])

        chain = MagicMock()
        for m in ("select", "eq", "insert"):
            getattr(chain, m).return_value = chain
        chain.execute.side_effect = execute
        db.table.return_value = chain

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_auth()
        try:
            r = await client.post(
                f"/api/v2/workspaces/{DEAL_ID}/notes/",
                json={"content": "Checklist note", "checklist_items": items},
            )
            assert r.status_code == 201
            assert len(r.json()["data"]["checklist_items"]) == 2
        finally:
            app.dependency_overrides.clear()

    async def test_create_note_empty_content_rejected(self, client):
        """POST with empty content returns 422."""
        db = MagicMock()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_auth()
        try:
            r = await client.post(
                f"/api/v2/workspaces/{DEAL_ID}/notes/",
                json={"content": ""},
            )
            assert r.status_code == 422
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestUpdateNote:
    async def test_update_note_partial(self, client):
        """PATCH with is_pinned=True updates only that field."""
        updated = _make_note(is_pinned=True)
        db = MagicMock()
        call_n = [0]

        def execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                return MagicMock(data=[_make_note()])  # note exists check
            return MagicMock(data=[updated])  # update result

        chain = MagicMock()
        for m in ("select", "eq", "update"):
            getattr(chain, m).return_value = chain
        chain.execute.side_effect = execute
        db.table.return_value = chain

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_auth()
        try:
            r = await client.patch(
                f"/api/v2/workspaces/{DEAL_ID}/notes/{NOTE_ID}",
                json={"is_pinned": True},
            )
            assert r.status_code == 200
            assert r.json()["data"]["is_pinned"] is True
        finally:
            app.dependency_overrides.clear()

    async def test_update_note_checklist_toggle(self, client):
        """PATCH checklist_items replaces the whole array."""
        items = [{"text": "Step 1", "checked": True}]
        updated = _make_note(checklist_items=items)
        db = MagicMock()
        call_n = [0]

        def execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                return MagicMock(data=[_make_note()])
            return MagicMock(data=[updated])

        chain = MagicMock()
        for m in ("select", "eq", "update"):
            getattr(chain, m).return_value = chain
        chain.execute.side_effect = execute
        db.table.return_value = chain

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_auth()
        try:
            r = await client.patch(
                f"/api/v2/workspaces/{DEAL_ID}/notes/{NOTE_ID}",
                json={"checklist_items": items},
            )
            assert r.status_code == 200
            assert r.json()["data"]["checklist_items"][0]["checked"] is True
        finally:
            app.dependency_overrides.clear()

    async def test_update_note_not_found(self, client):
        """PATCH on unknown note returns 404."""
        db = MagicMock()
        chain = MagicMock()
        for m in ("select", "eq", "update"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        db.table.return_value = chain

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_auth()
        try:
            r = await client.patch(
                f"/api/v2/workspaces/{DEAL_ID}/notes/{str(uuid.uuid4())}",
                json={"is_pinned": True},
            )
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestDeleteNote:
    async def test_delete_note(self, client):
        """DELETE returns 204."""
        db = MagicMock()
        call_n = [0]

        def execute():
            n = call_n[0]
            call_n[0] += 1
            return MagicMock(data=[_make_note()] if n == 0 else [])

        chain = MagicMock()
        for m in ("select", "eq", "delete"):
            getattr(chain, m).return_value = chain
        chain.execute.side_effect = execute
        db.table.return_value = chain

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_auth()
        try:
            r = await client.delete(f"/api/v2/workspaces/{DEAL_ID}/notes/{NOTE_ID}")
            assert r.status_code == 204
        finally:
            app.dependency_overrides.clear()

    async def test_delete_note_not_found(self, client):
        """DELETE on unknown note returns 404."""
        db = MagicMock()
        chain = MagicMock()
        for m in ("select", "eq", "delete"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        db.table.return_value = chain

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_auth()
        try:
            r = await client.delete(
                f"/api/v2/workspaces/{DEAL_ID}/notes/{str(uuid.uuid4())}"
            )
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_delete_note_wrong_deal(self, client):
        """DELETE with mismatched workspace_id returns 404."""
        other_deal = str(uuid.uuid4())
        db = MagicMock()
        chain = MagicMock()
        for m in ("select", "eq", "delete"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        db.table.return_value = chain

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = override_auth()
        try:
            r = await client.delete(f"/api/v2/workspaces/{other_deal}/notes/{NOTE_ID}")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()
