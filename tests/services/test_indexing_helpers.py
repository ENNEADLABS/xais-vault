"""
Tests for apps/worker/app/services/indexing_helpers.py.

All external dependencies (Supabase Storage, LLM, embedder, job queue) are mocked.
"""

import json
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.worker.app.services.chunking import Chunk
from apps.worker.app.services.indexing_helpers import (
    EMBEDDING_BATCH_SIZE,
    _format_retry_feedback,
    _validate_summary,
    download_file,
    embed_chunks,
    generate_summary,
    maybe_trigger_scan,
    store_chunks,
)

DEAL_ID = str(uuid.uuid4())
ORG_ID = str(uuid.uuid4())
SOURCE_ID = str(uuid.uuid4())


# ─── Helpers ──────────────────────────────────────────────────


def _make_chunks(n: int) -> list[Chunk]:
    return [
        Chunk(content=f"chunk {i}", chunk_index=i, token_count=100) for i in range(n)
    ]


def _make_embeddings(n: int) -> list[list[float]]:
    return [[0.1] * 1536 for _ in range(n)]


# ─── download_file ─────────────────────────────────────────────


class TestDownloadFile:
    @pytest.mark.asyncio
    async def test_downloads_to_temp_file_with_correct_extension(self):
        """Returns a path ending in .pdf when storage_path ends in .pdf."""
        supabase = MagicMock()
        supabase.storage.from_.return_value.download.return_value = b"pdf content"

        path = await download_file(supabase, "org/workspace/src/file.pdf")

        assert path.endswith(".pdf")
        assert os.path.exists(path)
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_temp_file_contains_storage_content(self):
        """The temp file written to disk contains the bytes from storage."""
        content = b"binary PDF content \x00\x01\x02"
        supabase = MagicMock()
        supabase.storage.from_.return_value.download.return_value = content

        path = await download_file(supabase, "org/workspace/src/report.pdf")

        with open(path, "rb") as f:
            assert f.read() == content
        os.unlink(path)


# ─── embed_chunks ──────────────────────────────────────────────


class TestEmbedChunks:
    @pytest.mark.asyncio
    @patch("apps.worker.app.services.indexing_helpers.get_embedder")
    async def test_returns_embeddings_matching_chunk_count(self, mock_get_embedder):
        """Returns exactly one embedding per chunk."""
        n = 5
        chunks = _make_chunks(n)
        embedder = AsyncMock()
        embedder.embed.return_value = MagicMock(
            embeddings=[[0.1] * 1536] * n,
            usage=MagicMock(cost_usd=0.001),
        )
        mock_get_embedder.return_value = embedder

        embeddings, cost = await embed_chunks(chunks)

        assert len(embeddings) == n
        assert cost == pytest.approx(0.001)

    @pytest.mark.asyncio
    @patch("apps.worker.app.services.indexing_helpers.get_embedder")
    async def test_batches_at_50_chunks(self, mock_get_embedder):
        """75 chunks → 2 embed() calls (50 + 25)."""
        chunks = _make_chunks(75)
        embedder = AsyncMock()

        def _embed(texts, **kwargs):
            n = len(texts)
            return MagicMock(
                embeddings=[[0.1] * 1536] * n,
                usage=MagicMock(cost_usd=0.001),
            )

        embedder.embed.side_effect = _embed
        mock_get_embedder.return_value = embedder

        await embed_chunks(chunks)

        assert embedder.embed.call_count == 2
        first_batch_size = len(embedder.embed.call_args_list[0].args[0])
        second_batch_size = len(embedder.embed.call_args_list[1].args[0])
        assert first_batch_size == EMBEDDING_BATCH_SIZE
        assert second_batch_size == 75 - EMBEDDING_BATCH_SIZE

    @pytest.mark.asyncio
    @patch("apps.worker.app.services.indexing_helpers.get_embedder")
    async def test_accumulates_cost_across_batches(self, mock_get_embedder):
        """Total cost is the sum of costs from each batch."""
        chunks = _make_chunks(75)
        embedder = AsyncMock()

        def _embed(texts, **kwargs):
            n = len(texts)
            return MagicMock(
                embeddings=[[0.1] * 1536] * n,
                usage=MagicMock(cost_usd=0.01),
            )

        embedder.embed.side_effect = _embed
        mock_get_embedder.return_value = embedder

        _, total_cost = await embed_chunks(chunks)

        assert total_cost == pytest.approx(0.02)  # 2 batches × 0.01


# ─── generate_summary ──────────────────────────────────────────


class TestGenerateSummary:
    @pytest.mark.asyncio
    @patch("apps.worker.app.services.indexing_helpers.get_llm")
    async def test_returns_summary_dict_on_valid_json(self, mock_get_llm):
        """Parses valid JSON response from LLM into a dict."""
        expected = {
            "summary": "A strong fintech company with solid revenue growth and expanding market share.",
            "topics": ["fintech", "payments"],
            "suggested_questions": ["What is the ARR?"],
        }
        llm = AsyncMock()
        llm.generate.return_value = MagicMock(
            content=json.dumps(expected),
            usage=MagicMock(cost_usd=0.005),
        )
        mock_get_llm.return_value = llm

        data, cost = await generate_summary("Some document text")

        assert data["summary"] == expected["summary"]
        assert data["topics"] == ["fintech", "payments"]
        assert cost == pytest.approx(0.005)

    @pytest.mark.asyncio
    @patch("apps.worker.app.services.indexing_helpers.get_llm")
    async def test_fallback_on_invalid_json(self, mock_get_llm):
        """Returns fallback dict when LLM returns non-JSON text."""
        llm = AsyncMock()
        llm.generate.return_value = MagicMock(
            content="Sorry, here is plain text, not JSON.",
            usage=MagicMock(cost_usd=0.003),
        )
        mock_get_llm.return_value = llm

        data, _ = await generate_summary("Some text")

        assert "summary" in data
        assert "topics" in data
        assert data["topics"] == []
        assert data["suggested_questions"] == []

    @pytest.mark.asyncio
    @patch("apps.worker.app.services.indexing_helpers.get_llm")
    async def test_retries_on_invalid_json_then_succeeds(self, mock_get_llm):
        """Retries with feedback when first attempt returns invalid JSON."""
        valid = {
            "summary": "A solid fintech company with strong revenue growth and market position.",
            "topics": ["fintech", "payments"],
            "suggested_questions": ["What is the ARR?"],
        }
        llm = AsyncMock()
        llm.generate.side_effect = [
            MagicMock(content="not json at all", usage=MagicMock(cost_usd=0.003)),
            MagicMock(content=json.dumps(valid), usage=MagicMock(cost_usd=0.005)),
        ]
        mock_get_llm.return_value = llm

        data, cost = await generate_summary("Some doc")

        assert data["summary"] == valid["summary"]
        assert data["topics"] == ["fintech", "payments"]
        assert llm.generate.call_count == 2
        assert cost == pytest.approx(0.008)
        # Le second prompt contient le feedback d'erreur
        second_prompt = llm.generate.call_args_list[1].args[0]
        assert "Erreurs de validation" in second_prompt

    @pytest.mark.asyncio
    @patch("apps.worker.app.services.indexing_helpers.get_llm")
    async def test_retries_on_missing_fields_then_succeeds(self, mock_get_llm):
        """Retries when JSON is valid but required fields are missing."""
        incomplete = {
            "summary": "Short"
        }  # topics et questions manquants, summary trop court
        valid = {
            "summary": "A solid fintech company with strong revenue growth and market position.",
            "topics": ["fintech"],
            "suggested_questions": ["What is ARR?"],
        }
        llm = AsyncMock()
        llm.generate.side_effect = [
            MagicMock(content=json.dumps(incomplete), usage=MagicMock(cost_usd=0.003)),
            MagicMock(content=json.dumps(valid), usage=MagicMock(cost_usd=0.005)),
        ]
        mock_get_llm.return_value = llm

        data, cost = await generate_summary("Some doc")

        assert data["topics"] == ["fintech"]
        assert llm.generate.call_count == 2

    @pytest.mark.asyncio
    @patch("apps.worker.app.services.indexing_helpers.get_llm")
    async def test_stops_retrying_on_same_error_repeated(self, mock_get_llm):
        """Stops retrying when the same error occurs twice in a row."""
        llm = AsyncMock()
        llm.generate.return_value = MagicMock(
            content="still not json",
            usage=MagicMock(cost_usd=0.003),
        )
        mock_get_llm.return_value = llm

        data, cost = await generate_summary("Some doc")

        # 2 tentatives seulement (pas 3) car même erreur répétée
        assert llm.generate.call_count == 2
        # Fallback retourne quand même un dict utilisable
        assert "summary" in data
        assert data["topics"] == []

    @pytest.mark.asyncio
    @patch("apps.worker.app.services.indexing_helpers.get_llm")
    async def test_fallback_extracts_partial_json(self, mock_get_llm):
        """Fallback extracts usable fields from partially valid JSON."""
        partial = {
            "summary": "A decent fintech company with moderate growth and reasonable position.",
            "topics": ["fintech"],
            # suggested_questions manquant
        }
        llm = AsyncMock()
        # Retourne toujours le même JSON partiel → même erreur → stop après 2
        llm.generate.return_value = MagicMock(
            content=json.dumps(partial),
            usage=MagicMock(cost_usd=0.003),
        )
        mock_get_llm.return_value = llm

        data, _ = await generate_summary("Some doc")

        # Le fallback extrait ce qu'il peut
        assert data["summary"] == partial["summary"]
        assert data["topics"] == ["fintech"]
        assert data["suggested_questions"] == []

    @pytest.mark.asyncio
    @patch("apps.worker.app.services.indexing_helpers.get_llm")
    async def test_accumulates_cost_across_retries(self, mock_get_llm):
        """Total cost includes all retry attempts."""
        valid = {
            "summary": "A solid fintech company with strong revenue growth and market position.",
            "topics": ["fintech"],
            "suggested_questions": ["What?"],
        }
        llm = AsyncMock()
        llm.generate.side_effect = [
            MagicMock(content="bad", usage=MagicMock(cost_usd=0.01)),
            MagicMock(content="bad", usage=MagicMock(cost_usd=0.01)),
        ]
        mock_get_llm.return_value = llm

        _, cost = await generate_summary("Some doc")

        assert cost == pytest.approx(0.02)

    @pytest.mark.asyncio
    @patch("apps.worker.app.services.indexing_helpers.get_llm")
    async def test_truncates_input_text_at_100k_chars(self, mock_get_llm):
        """Input text > 100k chars is truncated before being sent to LLM."""
        llm = AsyncMock()
        llm.generate.return_value = MagicMock(
            content=json.dumps(
                {
                    "summary": "A solid fintech company with strong revenue growth and market position.",
                    "topics": ["data"],
                    "suggested_questions": ["What?"],
                }
            ),
            usage=MagicMock(cost_usd=0.01),
        )
        mock_get_llm.return_value = llm

        long_text = "x" * 200_000
        await generate_summary(long_text)

        prompt_sent = llm.generate.call_args.args[0]
        # Prompt wraps the truncated text; total prompt length should be well under 200k
        assert len(prompt_sent) < 120_000


# ─── _validate_summary ────────────────────────────────────────


class TestValidateSummary:
    def test_valid_json_returns_no_errors(self):
        """Complete valid JSON returns empty error list."""
        content = json.dumps(
            {
                "summary": "A solid fintech company with strong revenue growth and market position.",
                "topics": ["fintech", "payments"],
                "suggested_questions": ["What is the ARR?"],
            }
        )
        assert _validate_summary(content) == []

    def test_invalid_json_returns_parse_error(self):
        """Non-JSON string returns a JSON parse error."""
        errors = _validate_summary("not json")
        assert len(errors) == 1
        assert "JSON invalide" in errors[0]

    def test_missing_summary_returns_error(self):
        """Missing summary field is flagged."""
        content = json.dumps({"topics": ["a"], "suggested_questions": ["b"]})
        errors = _validate_summary(content)
        assert any("summary" in e for e in errors)

    def test_short_summary_returns_error(self):
        """Summary shorter than 50 chars is flagged."""
        content = json.dumps(
            {
                "summary": "Too short",
                "topics": ["a"],
                "suggested_questions": ["b"],
            }
        )
        errors = _validate_summary(content)
        assert any("trop court" in e for e in errors)

    def test_missing_topics_returns_error(self):
        """Missing topics field is flagged."""
        content = json.dumps(
            {
                "summary": "A solid fintech company with strong revenue growth and market position.",
                "suggested_questions": ["What?"],
            }
        )
        errors = _validate_summary(content)
        assert any("topics" in e for e in errors)

    def test_empty_topics_returns_error(self):
        """Empty topics list is flagged."""
        content = json.dumps(
            {
                "summary": "A solid fintech company with strong revenue growth and market position.",
                "topics": [],
                "suggested_questions": ["What?"],
            }
        )
        errors = _validate_summary(content)
        assert any("topics" in e and "vide" in e for e in errors)

    def test_missing_suggested_questions_returns_error(self):
        """Missing suggested_questions field is flagged."""
        content = json.dumps(
            {
                "summary": "A solid fintech company with strong revenue growth and market position.",
                "topics": ["fintech"],
            }
        )
        errors = _validate_summary(content)
        assert any("suggested_questions" in e for e in errors)

    def test_non_dict_returns_error(self):
        """JSON array instead of object is flagged."""
        errors = _validate_summary(json.dumps(["not", "a", "dict"]))
        assert any("objet JSON" in e for e in errors)

    def test_multiple_errors_returned_together(self):
        """Multiple validation failures are all reported."""
        content = json.dumps({"summary": "Short"})
        errors = _validate_summary(content)
        # Au moins 3 erreurs : summary trop court + topics manquant + questions manquantes
        assert len(errors) >= 3


# ─── _format_retry_feedback ───────────────────────────────────


class TestFormatRetryFeedback:
    def test_includes_error_details(self):
        """Feedback string includes the specific validation errors."""
        errors = [{"attempt": 1, "errors": ["Champ 'topics' manquant"]}]
        result = _format_retry_feedback(errors)
        assert "Champ 'topics' manquant" in result
        assert "Tentative 1" in result

    def test_includes_correction_instruction(self):
        """Feedback ends with instruction to output corrected JSON only."""
        errors = [{"attempt": 1, "errors": ["JSON invalide"]}]
        result = _format_retry_feedback(errors)
        assert "Corrige ces erreurs" in result
        assert "JSON corrigé" in result


# ─── store_chunks ──────────────────────────────────────────────


class TestStoreChunks:
    def _make_db(self):
        db = MagicMock()
        db.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock()
        inserted = []

        def capture_insert(batch):
            inserted.append(list(batch))
            return MagicMock(
                execute=MagicMock(return_value=MagicMock(data=list(batch)))
            )

        db.table.return_value.insert.side_effect = capture_insert
        db._inserted = inserted
        return db

    @pytest.mark.asyncio
    async def test_deletes_existing_chunks_before_insert(self):
        """DELETE is called before any INSERT."""
        db = self._make_db()
        chunks = _make_chunks(3)
        embeddings = _make_embeddings(3)

        await store_chunks(
            db,
            chunks=chunks,
            embeddings=embeddings,
            source_id=SOURCE_ID,
            workspace_id=DEAL_ID,
            organization_id=ORG_ID,
        )

        db.table.return_value.delete.assert_called()

    @pytest.mark.asyncio
    async def test_inserts_all_chunks_with_embeddings(self):
        """Total inserted rows equals chunk count."""
        n = 7
        db = self._make_db()
        chunks = _make_chunks(n)
        embeddings = _make_embeddings(n)

        await store_chunks(
            db,
            chunks=chunks,
            embeddings=embeddings,
            source_id=SOURCE_ID,
            workspace_id=DEAL_ID,
            organization_id=ORG_ID,
        )

        total = sum(len(batch) for batch in db._inserted)
        assert total == n

    @pytest.mark.asyncio
    async def test_batches_at_100_chunks(self):
        """150 chunks → exactly 2 insert batches (100 + 50)."""
        db = self._make_db()
        chunks = _make_chunks(150)
        embeddings = _make_embeddings(150)

        await store_chunks(
            db,
            chunks=chunks,
            embeddings=embeddings,
            source_id=SOURCE_ID,
            workspace_id=DEAL_ID,
            organization_id=ORG_ID,
        )

        assert len(db._inserted) == 2
        assert len(db._inserted[0]) == 100
        assert len(db._inserted[1]) == 50


# ─── maybe_trigger_scan ────────────────────────────────────────


@patch("apps.worker.app.services.indexing_helpers.AUTO_SCAN_ENABLED", True)
class TestMaybeTriggerScan:
    def _make_db(self, *, sources, workspace=None, existing_jobs=None):
        db = MagicMock()

        def table_side_effect(name):
            chain = MagicMock()
            for m in ("select", "eq", "in_"):
                getattr(chain, m).return_value = chain

            if name == "sources":
                chain.execute.return_value = MagicMock(data=sources)
            elif name == "workspaces":
                chain.execute.return_value = MagicMock(data=[workspace] if workspace else [])
            elif name == "jobs":
                chain.execute.return_value = MagicMock(data=existing_jobs or [])
            else:
                chain.execute.return_value = MagicMock(data=[])
            return chain

        db.table.side_effect = table_side_effect
        return db

    @pytest.mark.asyncio
    @patch("apps.worker.app.services.indexing_helpers.create_job")
    async def test_triggers_scan_when_all_sources_ready(self, mock_create_job):
        """Creates a scan_workspace job when every source has status='ready'."""
        mock_create_job.return_value = {"id": "job-1"}
        db = self._make_db(
            sources=[{"id": "s1", "status": "ready"}, {"id": "s2", "status": "ready"}],
            workspace={"scan_status": "pending"},
        )

        await maybe_trigger_scan(db, workspace_id=DEAL_ID, organization_id=ORG_ID)

        mock_create_job.assert_called_once()
        assert mock_create_job.call_args.kwargs["type"] == "scan_workspace"

    @pytest.mark.asyncio
    @patch("apps.worker.app.services.indexing_helpers.create_job")
    async def test_skips_when_sources_still_processing(self, mock_create_job):
        """Does not trigger scan when at least one source is still processing."""
        db = self._make_db(
            sources=[
                {"id": "s1", "status": "ready"},
                {"id": "s2", "status": "processing"},
            ],
            workspace={"scan_status": "pending"},
        )

        await maybe_trigger_scan(db, workspace_id=DEAL_ID, organization_id=ORG_ID)

        mock_create_job.assert_not_called()

    @pytest.mark.asyncio
    @patch("apps.worker.app.services.indexing_helpers.create_job")
    async def test_skips_when_scan_already_exists(self, mock_create_job):
        """Does not create a duplicate scan_workspace job."""
        db = self._make_db(
            sources=[{"id": "s1", "status": "ready"}],
            workspace={"scan_status": "pending"},
            existing_jobs=[{"id": "existing-job"}],
        )

        await maybe_trigger_scan(db, workspace_id=DEAL_ID, organization_id=ORG_ID)

        mock_create_job.assert_not_called()

    @pytest.mark.asyncio
    @patch("apps.worker.app.services.indexing_helpers.create_job")
    async def test_skips_when_deal_not_pending(self, mock_create_job):
        """Does not trigger scan when workspace scan_status is not 'pending'."""
        db = self._make_db(
            sources=[{"id": "s1", "status": "ready"}],
            workspace={"scan_status": "in_progress"},
        )

        await maybe_trigger_scan(db, workspace_id=DEAL_ID, organization_id=ORG_ID)

        mock_create_job.assert_not_called()


class TestAutoScanFeatureFlag:
    """Tests pour le feature flag AUTO_SCAN_ENABLED."""

    @pytest.mark.asyncio
    @patch("apps.worker.app.services.indexing_helpers.AUTO_SCAN_ENABLED", False)
    @patch("apps.worker.app.services.indexing_helpers.create_job")
    async def test_disabled_by_default_skips_scan(self, mock_create_job):
        """AUTO_SCAN_ENABLED=false → create_job jamais appelé."""
        db = MagicMock()
        await maybe_trigger_scan(db, workspace_id=DEAL_ID, organization_id=ORG_ID)
        mock_create_job.assert_not_called()
        db.table.assert_not_called()

    @pytest.mark.asyncio
    @patch("apps.worker.app.services.indexing_helpers.AUTO_SCAN_ENABLED", True)
    @patch("apps.worker.app.services.indexing_helpers.create_job")
    async def test_enabled_proceeds_normally(self, mock_create_job):
        """AUTO_SCAN_ENABLED=true → le scan se déclenche si conditions remplies."""
        mock_create_job.return_value = {"id": "job-1"}
        db = MagicMock()

        def table_side_effect(name):
            chain = MagicMock()
            for m in ("select", "eq", "in_"):
                getattr(chain, m).return_value = chain
            if name == "sources":
                chain.execute.return_value = MagicMock(
                    data=[{"id": "s1", "status": "ready"}]
                )
            elif name == "workspaces":
                chain.execute.return_value = MagicMock(
                    data=[{"scan_status": "pending"}]
                )
            elif name == "jobs":
                chain.execute.return_value = MagicMock(data=[])
            else:
                chain.execute.return_value = MagicMock(data=[])
            return chain

        db.table.side_effect = table_side_effect

        await maybe_trigger_scan(db, workspace_id=DEAL_ID, organization_id=ORG_ID)
        mock_create_job.assert_called_once()
