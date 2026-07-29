"""
Tests for apps/api/app/routers/chat.py

All external dependencies are mocked:
  - Supabase DB via dependency override
  - SSE stream patched to a simple fake generator
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
SESSION_ID = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()
CHAT_BASE = f"/api/v2/workspaces/{DEAL_ID}/chat"


# ─── Helpers ───────────────────────────────────────────────────


def _make_session(**overrides) -> dict:
    base = {
        "id": SESSION_ID,
        "workspace_id": DEAL_ID,
        "organization_id": ORG_ID,
        "user_id": USER_ID,
        "title": "Question test",
        "created_at": NOW,
        "updated_at": NOW,
    }
    return {**base, **overrides}


def _make_message(**overrides) -> dict:
    base = {
        "id": str(uuid.uuid4()),
        "session_id": SESSION_ID,
        "organization_id": ORG_ID,
        "role": "user",
        "content": "Bonjour",
        "citations": None,
        "input_tokens": None,
        "output_tokens": None,
        "cost_usd": None,
        "model_used": None,
        "created_at": NOW,
    }
    return {**base, **overrides}


def _make_auth(role: str = "analyst") -> AuthContext:
    return AuthContext(
        user_id=USER_ID, organization_id=ORG_ID, role=role, auth_method="jwt"
    )


def _db_with_table_dispatch(table_rows: dict[str, list]) -> MagicMock:
    db = MagicMock()

    def make_chain(rows: list) -> MagicMock:
        chain = MagicMock()
        for m in ("select", "eq", "order", "update", "delete", "insert", "limit"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=rows)
        return chain

    def side_effect(name: str) -> MagicMock:
        return make_chain(table_rows.get(name, []))

    db.table.side_effect = side_effect
    return db


def _db_with_select(rows: list[dict]) -> MagicMock:
    db = MagicMock()
    chain = MagicMock()
    for m in ("select", "eq", "order", "update", "delete"):
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(data=rows)
    db.table.return_value = chain
    return db


def _override_auth(role: str = "analyst"):
    auth = _make_auth(role)

    async def _dep():
        return auth

    app.dependency_overrides[require_auth] = _dep
    return _dep


async def _fake_stream(**kw):
    """Minimal SSE generator for router tests."""
    yield "event: done\ndata: {}\n\n"


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ─── Send Message ───────────────────────────────────────────────


@pytest.mark.asyncio
class TestSendMessage:
    async def test_send_returns_streaming_response(self, client):
        """POST / returns 200 with text/event-stream content type."""
        # Workspace exists, session is created or found
        db = _db_with_select([{"id": DEAL_ID}])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            with patch(
                "apps.api.app.routers.chat.get_or_create_session",
                new_callable=AsyncMock,
                return_value=SESSION_ID,
            ):
                with patch(
                    "apps.api.app.routers.chat.prepare_context",
                    new_callable=AsyncMock,
                    return_value=MagicMock(),
                ):
                    with patch(
                        "apps.api.app.routers.chat.build_chat_event_stream",
                        _fake_stream,
                    ):
                        r = await client.post(
                            f"{CHAT_BASE}/",
                            json={"content": "Bonjour"},
                        )
            assert r.status_code == 200
            assert "text/event-stream" in r.headers["content-type"]
        finally:
            app.dependency_overrides.clear()

    async def test_send_deal_not_found(self, client):
        """POST / returns 404 when workspace does not exist."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.post(f"{CHAT_BASE}/", json={"content": "Bonjour"})
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_send_empty_content(self, client):
        """POST / with empty content returns 422."""
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.post(f"{CHAT_BASE}/", json={"content": ""})
            assert r.status_code == 422
        finally:
            app.dependency_overrides.clear()


# ─── List Sessions ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestListSessions:
    async def test_list_sessions_empty(self, client):
        """GET /sessions returns 200 with empty list."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get(f"{CHAT_BASE}/sessions")
            assert r.status_code == 200
            assert r.json()["data"] == []
        finally:
            app.dependency_overrides.clear()

    async def test_list_sessions_with_data(self, client):
        """GET /sessions returns list of sessions."""
        db = _db_with_select([_make_session()])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get(f"{CHAT_BASE}/sessions")
            assert r.status_code == 200
            assert len(r.json()["data"]) == 1
            assert r.json()["data"][0]["id"] == SESSION_ID
        finally:
            app.dependency_overrides.clear()


# ─── Get Session ────────────────────────────────────────────────


@pytest.mark.asyncio
class TestGetSession:
    async def test_get_session_with_messages(self, client):
        """GET /sessions/{session_id} returns session and messages."""
        db = _db_with_table_dispatch(
            {
                "chat_sessions": [_make_session()],
                "chat_messages": [_make_message()],
            }
        )
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get(f"{CHAT_BASE}/sessions/{SESSION_ID}")
            assert r.status_code == 200
            body = r.json()["data"]
            assert body["session"]["id"] == SESSION_ID
            assert len(body["messages"]) == 1
        finally:
            app.dependency_overrides.clear()

    async def test_get_session_not_found(self, client):
        """GET /sessions/{session_id} returns 404 for unknown session."""
        db = _db_with_table_dispatch({"chat_sessions": [], "chat_messages": []})
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_viewer] = _override_auth("viewer")
        try:
            r = await client.get(f"{CHAT_BASE}/sessions/{uuid.uuid4()}")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ─── Rename Session ─────────────────────────────────────────────


@pytest.mark.asyncio
class TestRenameSession:
    async def test_rename_success(self, client):
        """PATCH /sessions/{session_id} renames session and returns 200."""
        updated = _make_session(title="New Title")
        # First call returns session (require_one check), second returns updated
        call_n = [0]
        db = MagicMock()
        chain = MagicMock()
        for m in ("select", "eq", "update"):
            getattr(chain, m).return_value = chain

        def execute():
            n = call_n[0]
            call_n[0] += 1
            if n == 0:
                return MagicMock(data=[_make_session()])
            return MagicMock(data=[updated])

        chain.execute.side_effect = execute
        db.table.return_value = chain

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.patch(
                f"{CHAT_BASE}/sessions/{SESSION_ID}",
                json={"title": "New Title"},
            )
            assert r.status_code == 200
            assert r.json()["data"]["title"] == "New Title"
        finally:
            app.dependency_overrides.clear()

    async def test_rename_not_found(self, client):
        """PATCH /sessions/{session_id} returns 404 for unknown session."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.patch(
                f"{CHAT_BASE}/sessions/{uuid.uuid4()}",
                json={"title": "New"},
            )
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ─── Delete Session ─────────────────────────────────────────────


@pytest.mark.asyncio
class TestDeleteSession:
    async def test_delete_success(self, client):
        """DELETE /sessions/{session_id} returns 204."""
        db = _db_with_select([{"id": SESSION_ID}])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.delete(f"{CHAT_BASE}/sessions/{SESSION_ID}")
            assert r.status_code == 204
        finally:
            app.dependency_overrides.clear()

    async def test_delete_not_found(self, client):
        """DELETE /sessions/{session_id} returns 404 for unknown session."""
        db = _db_with_select([])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_analyst] = _override_auth()
        try:
            r = await client.delete(f"{CHAT_BASE}/sessions/{uuid.uuid4()}")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()
