"""
Tests for apps/api/app/services/chat_session.py

DB fully mocked. Covers get_or_create_session and persist_messages.
"""

import uuid
from unittest.mock import MagicMock

import pytest

from apps.api.app.services.chat_session import get_or_create_session, persist_messages
from packages.llm.types import LLMUsage

DEAL_ID = str(uuid.uuid4())
ORG_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
SESSION_ID = str(uuid.uuid4())
NOW = "2026-03-17T00:00:00+00:00"


def _db_chain(rows: list[dict]) -> MagicMock:
    """Fluent Supabase chain mock returning given rows on execute()."""
    db = MagicMock()
    chain = MagicMock()
    for m in ("select", "insert", "update", "eq", "order", "limit"):
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(data=rows)
    db.table.return_value = chain
    return db


def _db_sequence(*row_lists) -> MagicMock:
    """DB mock returning successive row lists on successive execute() calls."""
    db = MagicMock()
    chain = MagicMock()
    for m in ("select", "insert", "update", "eq", "order", "limit"):
        getattr(chain, m).return_value = chain
    call_n = [0]

    def _execute():
        idx = min(call_n[0], len(row_lists) - 1)
        call_n[0] += 1
        return MagicMock(data=list(row_lists[idx]))

    chain.execute.side_effect = _execute
    db.table.return_value = chain
    return db


# ─── get_or_create_session ──────────────────────────────────────


@pytest.mark.asyncio
class TestGetOrCreateSession:
    async def test_existing_session_returned(self):
        """When session_id provided and found in DB, same id is returned."""
        db = _db_chain([{"id": SESSION_ID}])
        result = await get_or_create_session(
            db,
            session_id=SESSION_ID,
            workspace_id=DEAL_ID,
            organization_id=ORG_ID,
            user_id=USER_ID,
            first_message="Analyse le dossier",
        )
        assert result == SESSION_ID

    async def test_session_not_found_raises_404(self):
        """session_id provided but not in DB raises HTTPException 404."""
        from fastapi import HTTPException

        db = _db_chain([])
        with pytest.raises(HTTPException) as exc_info:
            await get_or_create_session(
                db,
                session_id=str(uuid.uuid4()),
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
                user_id=USER_ID,
                first_message="Hello",
            )
        assert exc_info.value.status_code == 404

    async def test_new_session_created_without_id(self):
        """When session_id is None, a new session is created and its id returned."""
        new_id = str(uuid.uuid4())
        db = _db_chain([{"id": new_id}])
        result = await get_or_create_session(
            db,
            session_id=None,
            workspace_id=DEAL_ID,
            organization_id=ORG_ID,
            user_id=USER_ID,
            first_message="Analyse le dossier",
        )
        assert result == new_id

    async def test_title_truncated_at_80_chars(self):
        """Messages longer than 80 chars get truncated title with '...'."""
        long_msg = "a" * 100
        new_id = str(uuid.uuid4())
        db = MagicMock()
        chain = MagicMock()
        for m in ("select", "update", "eq", "order", "limit"):
            getattr(chain, m).return_value = chain

        inserted_data = [None]

        def _insert(row):
            inserted_data[0] = row
            mock_chain = MagicMock()
            mock_chain.execute.return_value = MagicMock(data=[{"id": new_id, **row}])
            return mock_chain

        chain.insert.side_effect = _insert
        db.table.return_value = chain

        await get_or_create_session(
            db,
            session_id=None,
            workspace_id=DEAL_ID,
            organization_id=ORG_ID,
            user_id=USER_ID,
            first_message=long_msg,
        )
        title = inserted_data[0]["title"]
        assert title.endswith("...")
        assert len(title) == 83  # 80 chars + "..."

    async def test_title_not_truncated_when_short(self):
        """Short messages (<=80 chars) used as-is for title."""
        short_msg = "Analyse le dossier"
        new_id = str(uuid.uuid4())
        db = MagicMock()
        chain = MagicMock()
        for m in ("select", "update", "eq", "order", "limit"):
            getattr(chain, m).return_value = chain

        inserted_data = [None]

        def _insert(row):
            inserted_data[0] = row
            mock_chain = MagicMock()
            mock_chain.execute.return_value = MagicMock(data=[{"id": new_id, **row}])
            return mock_chain

        chain.insert.side_effect = _insert
        db.table.return_value = chain

        await get_or_create_session(
            db,
            session_id=None,
            workspace_id=DEAL_ID,
            organization_id=ORG_ID,
            user_id=USER_ID,
            first_message=short_msg,
        )
        assert inserted_data[0]["title"] == short_msg


# ─── persist_messages ───────────────────────────────────────────


@pytest.mark.asyncio
class TestPersistMessages:
    async def test_both_messages_inserted(self):
        """Both user and assistant messages are inserted, session updated."""
        user_msg = {"id": str(uuid.uuid4()), "role": "user", "content": "Question"}
        assistant_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": "Réponse",
        }

        db = _db_sequence([user_msg], [assistant_msg], [])
        usage = LLMUsage(
            input_tokens=100, output_tokens=50, cost_usd=0.001, model="claude-test"
        )

        u_msg, a_msg = await persist_messages(
            db,
            session_id=SESSION_ID,
            organization_id=ORG_ID,
            user_content="Question",
            assistant_content="Réponse",
            citations=[],
            usage=usage,
        )
        assert u_msg == user_msg
        assert a_msg == assistant_msg

    async def test_usage_fields_included_when_provided(self):
        """Usage tokens and cost are written to assistant message."""
        assistant_row = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": "Réponse",
            "input_tokens": 100,
            "output_tokens": 50,
            "cost_usd": 0.001,
            "model_used": "claude-test",
        }

        db = MagicMock()
        chain = MagicMock()
        for m in ("update", "eq"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[])

        inserted_rows: list[dict] = []

        def _insert(row):
            inserted_rows.append(row)
            mock_c = MagicMock()
            mock_c.execute.return_value = MagicMock(
                data=[{**row, "id": str(uuid.uuid4())}]
            )
            return mock_c

        chain.insert.side_effect = _insert
        db.table.return_value = chain

        usage = LLMUsage(
            input_tokens=100, output_tokens=50, cost_usd=0.001, model="claude-test"
        )
        await persist_messages(
            db,
            session_id=SESSION_ID,
            organization_id=ORG_ID,
            user_content="Q",
            assistant_content="R",
            citations=[],
            usage=usage,
        )

        # Second insert is the assistant message
        assistant_insert = inserted_rows[1]
        assert assistant_insert["input_tokens"] == 100
        assert assistant_insert["output_tokens"] == 50
        assert assistant_insert["model_used"] == "claude-test"

    async def test_no_usage_skips_token_fields(self):
        """When usage is None, token fields are omitted from assistant message."""
        db = MagicMock()
        chain = MagicMock()
        for m in ("update", "eq"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[])

        inserted_rows: list[dict] = []

        def _insert(row):
            inserted_rows.append(row)
            mock_c = MagicMock()
            mock_c.execute.return_value = MagicMock(
                data=[{**row, "id": str(uuid.uuid4())}]
            )
            return mock_c

        chain.insert.side_effect = _insert
        db.table.return_value = chain

        await persist_messages(
            db,
            session_id=SESSION_ID,
            organization_id=ORG_ID,
            user_content="Q",
            assistant_content="R",
            citations=[],
            usage=None,
        )

        assistant_insert = inserted_rows[1]
        assert "input_tokens" not in assistant_insert
        assert "cost_usd" not in assistant_insert

    async def test_citations_stored_when_present(self):
        """Non-empty citations list is saved on assistant message."""
        db = MagicMock()
        chain = MagicMock()
        for m in ("update", "eq"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[])

        inserted_rows: list[dict] = []

        def _insert(row):
            inserted_rows.append(row)
            mock_c = MagicMock()
            mock_c.execute.return_value = MagicMock(
                data=[{**row, "id": str(uuid.uuid4())}]
            )
            return mock_c

        chain.insert.side_effect = _insert
        db.table.return_value = chain

        citations = [{"source_id": "src-001", "quote": "ARR 8M€"}]
        await persist_messages(
            db,
            session_id=SESSION_ID,
            organization_id=ORG_ID,
            user_content="Q",
            assistant_content="R",
            citations=citations,
            usage=None,
        )

        assistant_insert = inserted_rows[1]
        assert assistant_insert["citations"] == citations

    async def test_empty_citations_stored_as_none(self):
        """Empty citations list is stored as None."""
        db = MagicMock()
        chain = MagicMock()
        for m in ("update", "eq"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[])

        inserted_rows: list[dict] = []

        def _insert(row):
            inserted_rows.append(row)
            mock_c = MagicMock()
            mock_c.execute.return_value = MagicMock(
                data=[{**row, "id": str(uuid.uuid4())}]
            )
            return mock_c

        chain.insert.side_effect = _insert
        db.table.return_value = chain

        await persist_messages(
            db,
            session_id=SESSION_ID,
            organization_id=ORG_ID,
            user_content="Q",
            assistant_content="R",
            citations=[],
            usage=None,
        )
        assert inserted_rows[1]["citations"] is None
