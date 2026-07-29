"""
Tests for the Writer Agent (apps/worker/app/agents/writer.py)
and its helpers (apps/worker/app/agents/writer_helpers.py).

Pyramide des tests :
  Couche 1 — Unitaires :
    - build_writer_prompt        : 4 cas
    - SEVERITY_ORDER / limits    : 2 cas
  Couche 1 — Avec mock DB :
    - load_workspace_context          : 3 cas
    - update_progress            : 1 cas
    - upload_docx                : 2 cas
  Couche 2 — Intégration :
    - run_generation             : 4 cas
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.worker.app.agents.writer import run_generation
from apps.worker.app.agents.writer_helpers import (
    INVESTIGATION_MAX_CHARS,
    MAX_TOKENS,
    SEVERITY_ORDER,
    DealContext,
    build_writer_prompt,
    load_workspace_context,
    update_progress,
    upload_docx,
)
from tests.conftest import make_llm_response

# ─── Fixtures ────────────────────────────────────────────────


def make_deal(**overrides) -> dict:
    base = {
        "id": "workspace-001",
        "name": "Acme Series B",
        "target_company": "Acme SAS",
        "sector": "SaaS",
        "deal_type": "Series B",
        "scan_summary": {
            "total_insights": 3,
            "critical_count": 0,
            "high_count": 1,
            "medium_count": 2,
            "deal_risk_score": 35,
            "key_observation": "Dossier solide.",
        },
    }
    return {**base, **overrides}


def make_finding(idx: int = 1, severity: str = "high", **overrides) -> dict:
    base = {
        "id": f"insight-{idx:03d}",
        "title": f"Insight {idx}",
        "description": f"Description du insight {idx}.",
        "severity": severity,
        "type": "red_flag",
        "source_quote": "Extrait source.",
        "verification": {"verdict": "confirmed", "explanation": "Corroboré."},
    }
    return {**base, **overrides}


def make_investigation(idx: int = 1, report: str = "Rapport court.", **overrides) -> dict:
    base = {
        "id": f"inv-{idx:03d}",
        "question": f"Question d'investigation {idx}?",
        "report": report,
        "status": "completed",
    }
    return {**base, **overrides}


def make_context(**overrides) -> DealContext:
    defaults = {
        "workspace": make_deal(),
        "sources": [],
        "insights": [make_finding(1, "high"), make_finding(2, "medium")],
        "investigations": [make_investigation(1)],
        "total_sources": 0,
        "total_insights": 2,
        "total_investigations": 1,
    }
    defaults.update(overrides)
    return DealContext(**defaults)


FAKE_REPORT = "# Executive Summary — Acme SAS\n## Synthèse\nDossier solide.\n## Métriques\n| KPI | Valeur |\n|-----|--------|\n| ARR | 8M€ |"


# ═══════════════════════════════════════════════════════════════
# Couche 1 — Constants and limits
# ═══════════════════════════════════════════════════════════════


class TestConstants:
    def test_severity_order_is_correct(self):
        assert SEVERITY_ORDER["critical"] < SEVERITY_ORDER["high"]
        assert SEVERITY_ORDER["high"] < SEVERITY_ORDER["medium"]
        assert SEVERITY_ORDER["medium"] < SEVERITY_ORDER["low"]

    def test_max_tokens_defined_for_all_types(self):
        for t in ("executive_summary", "investment_memo", "dd_report"):
            assert t in MAX_TOKENS
            assert MAX_TOKENS[t] > 0


# ═══════════════════════════════════════════════════════════════
# Couche 1 — build_writer_prompt (pure function)
# ═══════════════════════════════════════════════════════════════


class TestBuildWriterPrompt:
    def test_executive_summary_contains_deal_name(self):
        ctx = make_context()
        prompt = build_writer_prompt(ctx, "executive_summary")
        assert "Acme Series B" in prompt

    def test_executive_summary_truncates_to_10_findings(self):
        insights = [make_finding(i, "medium") for i in range(15)]
        ctx = make_context(insights=insights, total_insights=15)
        prompt = build_writer_prompt(ctx, "executive_summary")
        assert "10 sur 15 affichés" in prompt

    def test_dd_report_includes_all_findings(self):
        insights = [make_finding(i, "medium") for i in range(15)]
        ctx = make_context(insights=insights, total_insights=15)
        prompt = build_writer_prompt(ctx, "dd_report")
        assert "10 sur 15 affichés" not in prompt

    def test_investigation_report_truncated_for_executive_summary(self):
        long_report = "R" * 1000
        inv = make_investigation(1, report=long_report)
        ctx = make_context(investigations=[inv], total_investigations=1)
        prompt = build_writer_prompt(ctx, "executive_summary")
        INVESTIGATION_MAX_CHARS["executive_summary"]
        assert "[... tronqué ...]" in prompt
        # The report itself is truncated in the prompt
        assert long_report not in prompt

    def test_scan_summary_included(self):
        ctx = make_context()
        prompt = build_writer_prompt(ctx, "investment_memo")
        assert "Dossier solide." in prompt

    def test_finding_verification_included(self):
        insight = make_finding(1, verification={"verdict": "confirmed", "explanation": "Preuve trouvée."})
        ctx = make_context(insights=[insight])
        prompt = build_writer_prompt(ctx, "investment_memo")
        assert "Preuve trouvée." in prompt


# ═══════════════════════════════════════════════════════════════
# Couche 1 — load_workspace_context (avec mock DB)
# ═══════════════════════════════════════════════════════════════


class TestLoadDealContext:
    def _make_supabase(self, workspace, sources, insights, investigations):
        db = MagicMock()
        responses = iter([
            MagicMock(data=[workspace] if workspace else []),
            MagicMock(data=sources),
            MagicMock(data=insights),
            MagicMock(data=investigations),
        ])
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.side_effect = (
            lambda: next(responses)
        )
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.side_effect = (
            lambda: next(responses)
        )
        db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.execute.side_effect = (
            lambda: next(responses)
        )
        return db

    async def test_deal_not_found_raises(self):
        with patch("apps.worker.app.agents.writer_helpers.safe_get_one", return_value=None):
            with patch("apps.worker.app.agents.writer_helpers.safe_get_list", return_value=[]):
                with pytest.raises(ValueError, match="not found"):
                    await load_workspace_context(MagicMock(), "bad-id", "org-1")

    async def test_findings_sorted_by_severity(self):
        insights = [
            make_finding(1, severity="low"),
            make_finding(2, severity="critical"),
            make_finding(3, severity="high"),
        ]
        with (
            patch("apps.worker.app.agents.writer_helpers.safe_get_one", return_value=make_deal()),
            patch("apps.worker.app.agents.writer_helpers.safe_get_list", side_effect=[[], insights, []]),
        ):
            ctx = await load_workspace_context(MagicMock(), "workspace-1", "org-1")

        assert ctx.insights[0]["severity"] == "critical"
        assert ctx.insights[1]["severity"] == "high"
        assert ctx.insights[2]["severity"] == "low"

    async def test_empty_deal_returns_empty_lists(self):
        with (
            patch("apps.worker.app.agents.writer_helpers.safe_get_one", return_value=make_deal()),
            patch("apps.worker.app.agents.writer_helpers.safe_get_list", return_value=[]),
        ):
            ctx = await load_workspace_context(MagicMock(), "workspace-1", "org-1")

        assert ctx.total_insights == 0
        assert ctx.total_sources == 0
        assert ctx.total_investigations == 0


# ═══════════════════════════════════════════════════════════════
# Couche 1 — update_progress + upload_docx
# ═══════════════════════════════════════════════════════════════


class TestUpdateProgress:
    async def test_calls_db_with_correct_fields(self, mock_supabase):
        await update_progress(mock_supabase, "del-1", "building_docx", 70)
        update_data = mock_supabase.table.return_value.update.call_args.args[0]
        assert update_data["current_step"] == "building_docx"
        assert update_data["progress_percent"] == 70


class TestUploadDocx:
    async def test_uploads_to_correct_path(self):
        db = MagicMock()
        db.storage.from_.return_value.upload.return_value = MagicMock()

        path, size = await upload_docx(db, b"fakebytes", "workspace-1", "abc12345xyz", "executive_summary")
        assert path == "workspace-1/executive_summary_abc12345.docx"
        assert size == len(b"fakebytes")

    async def test_content_type_is_docx(self):
        db = MagicMock()
        db.storage.from_.return_value.upload.return_value = MagicMock()

        await upload_docx(db, b"data", "workspace-1", "del-001", "dd_report")
        call_kwargs = db.storage.from_.return_value.upload.call_args.kwargs
        assert "application/vnd.openxmlformats" in call_kwargs["file_options"]["content-type"]


# ═══════════════════════════════════════════════════════════════
# Couche 2 — run_generation (orchestration avec mocks)
# ═══════════════════════════════════════════════════════════════


class TestRunGeneration:
    @pytest.fixture
    def supabase_with_deliverable(self):
        db = MagicMock()
        deliverable = {"id": "del-001", "type": "executive_summary", "title": "Test"}
        (
            db.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .execute.return_value
        ) = MagicMock(data=[deliverable])
        db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trace-1"}])
        db.storage.from_.return_value.upload.return_value = MagicMock()
        return db

    @pytest.fixture
    def supabase_not_found(self):
        db = MagicMock()
        (
            db.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .execute.return_value
        ) = MagicMock(data=[])
        db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        return db

    async def test_deliverable_not_found_raises(self, supabase_not_found):
        with patch("apps.worker.app.agents.writer.safe_get_one", return_value=None):
            with pytest.raises(ValueError, match="not found"):
                await run_generation(
                    supabase_not_found,
                    {"deliverable_id": "bad", "workspace_id": "d1", "organization_id": "o1", "type": "executive_summary"},
                )

    async def test_happy_path_returns_stats(self, supabase_with_deliverable):
        deliverable = {"id": "del-001", "type": "executive_summary", "title": "Test"}
        ctx = make_context()
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = make_llm_response(FAKE_REPORT)

        with (
            patch("apps.worker.app.agents.writer.safe_get_one", return_value=deliverable),
            patch("apps.worker.app.agents.writer.load_workspace_context", new=AsyncMock(return_value=ctx)),
            patch("apps.worker.app.agents.writer.get_llm", return_value=mock_llm),
            patch("apps.worker.app.agents.writer.upload_docx", new=AsyncMock(return_value=("workspace-1/file.docx", 50000))),
        ):
            result = await run_generation(
                supabase_with_deliverable,
                {"deliverable_id": "del-001", "workspace_id": "workspace-1", "organization_id": "org-1", "type": "executive_summary"},
            )

        assert result["deliverable_id"] == "del-001"
        assert result["file_path"] == "workspace-1/file.docx"
        assert result["file_size_bytes"] == 50000
        assert "duration_ms" in result
        assert result["input_tokens"] == 500

    async def test_llm_failure_sets_status_failed(self, supabase_with_deliverable):
        deliverable = {"id": "del-001", "type": "executive_summary", "title": "Test"}
        ctx = make_context()
        failing_llm = AsyncMock()
        failing_llm.generate.side_effect = RuntimeError("API down")

        with (
            patch("apps.worker.app.agents.writer.safe_get_one", return_value=deliverable),
            patch("apps.worker.app.agents.writer.load_workspace_context", new=AsyncMock(return_value=ctx)),
            patch("apps.worker.app.agents.writer.get_llm", return_value=failing_llm),
        ):
            with pytest.raises(RuntimeError, match="API down"):
                await run_generation(
                    supabase_with_deliverable,
                    {"deliverable_id": "del-001", "workspace_id": "d1", "organization_id": "o1", "type": "executive_summary"},
                )

        update_calls = supabase_with_deliverable.table.return_value.update.call_args_list
        assert any(
            c.args and c.args[0].get("status") == "failed"
            for c in update_calls
        )

    async def test_llm_called_with_correct_max_tokens(self, supabase_with_deliverable):
        deliverable = {"id": "del-001", "type": "dd_report", "title": "Test"}
        ctx = make_context()
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = make_llm_response(FAKE_REPORT)

        with (
            patch("apps.worker.app.agents.writer.safe_get_one", return_value=deliverable),
            patch("apps.worker.app.agents.writer.load_workspace_context", new=AsyncMock(return_value=ctx)),
            patch("apps.worker.app.agents.writer.get_llm", return_value=mock_llm),
            patch("apps.worker.app.agents.writer.upload_docx", new=AsyncMock(return_value=("p", 1000))),
        ):
            await run_generation(
                supabase_with_deliverable,
                {"deliverable_id": "del-001", "workspace_id": "d1", "organization_id": "o1", "type": "dd_report"},
            )

        call_kwargs = mock_llm.generate.call_args.kwargs
        assert call_kwargs["max_tokens"] == MAX_TOKENS["dd_report"]
        assert call_kwargs["temperature"] == 0.2
