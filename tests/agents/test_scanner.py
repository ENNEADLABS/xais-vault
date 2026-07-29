"""
Tests for the Scanner Agent (apps/worker/app/agents/scanner.py)
and its helpers (apps/worker/app/agents/scanner_helpers.py).

Pyramide des tests :
  Couche 1 — Unitaires (fonctions pures) :
    - build_scan_prompt    : 8 cas
    - parse_scan_response  : 5 cas
  Couche 1 — Unitaires (avec mock DB) :
    - store_insights       : 14 cas
  Couche 2 — Intégration (orchestration run_scan avec mocks) :
    - run_scan             : 4 cas

LLM toujours mocké avec des réponses fixtures — aucun appel API réel.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.worker.app.agents.scanner import run_scan
from apps.worker.app.agents.scanner_helpers import (
    VALID_SEVERITIES,
    VALID_TYPES,
    build_scan_prompt,
    parse_scan_response,
    store_insights,
)
from tests.conftest import (
    make_llm_response,
    make_source,
)

# ═══════════════════════════════════════════════════════════════
# Couche 1 — build_scan_prompt (pure function)
# ═══════════════════════════════════════════════════════════════


class TestBuildScanPrompt:
    """build_scan_prompt assembles a full-context prompt from source dicts."""

    def test_includes_source_id_and_name(self):
        sources = [make_source("src-abc", "Memo.pdf", extracted_text="Contenu du mémo.")]
        prompt = build_scan_prompt(sources)
        assert "SOURCE_ID: src-abc" in prompt
        assert "DOCUMENT: Memo.pdf" in prompt

    def test_includes_source_text(self):
        sources = [make_source(extracted_text="Passage financier clé.")]
        prompt = build_scan_prompt(sources)
        assert "Passage financier clé." in prompt

    def test_skips_source_with_none_text(self):
        sources = [make_source(source_id="skip-none", extracted_text=None)]
        prompt = build_scan_prompt(sources)
        assert "skip-none" not in prompt

    def test_skips_source_with_whitespace_only_text(self):
        sources = [make_source(source_id="skip-ws", extracted_text="   \n\n  ")]
        prompt = build_scan_prompt(sources)
        assert "skip-ws" not in prompt

    def test_includes_multiple_sources(self):
        sources = [
            make_source("s1", "Doc A.pdf", extracted_text="Texte A"),
            make_source("s2", "Doc B.pdf", extracted_text="Texte B"),
        ]
        prompt = build_scan_prompt(sources)
        assert "SOURCE_ID: s1" in prompt
        assert "SOURCE_ID: s2" in prompt
        assert "Texte A" in prompt
        assert "Texte B" in prompt

    def test_truncates_oversized_source(self):
        """A single source exceeding the budget is truncated with a marker."""
        huge_text = "x" * 500_000
        sources = [make_source(extracted_text=huge_text)]
        prompt = build_scan_prompt(sources)
        assert "[... document tronqué ...]" in prompt

    def test_omits_source_when_budget_exhausted(self):
        """Second source is marked as omitted when total chars already at limit."""
        big_text = "x" * 500_000
        sources = [
            make_source("s1", "Big.pdf", extracted_text=big_text),
            make_source("s2", "Overflow.pdf", extracted_text="Ce document ne devrait pas apparaître."),
        ]
        prompt = build_scan_prompt(sources)
        assert "limite de contexte atteinte" in prompt
        assert "Ce document ne devrait pas apparaître." not in prompt

    def test_empty_sources_returns_valid_prompt(self):
        """Empty list still produces a well-formed prompt with header/footer."""
        prompt = build_scan_prompt([])
        assert "FIN DES DOCUMENTS" in prompt
        assert isinstance(prompt, str)
        assert len(prompt) > 50


# ═══════════════════════════════════════════════════════════════
# Couche 1 — parse_scan_response (pure function)
# ═══════════════════════════════════════════════════════════════


class TestParseScanResponse:
    """parse_scan_response parses the LLM JSON output with graceful fallbacks."""

    def test_valid_json_returns_findings(self):
        payload = {
            "insights": [{
                "title": "Test",
                "description": "Description du test.",
                "type": "red_flag",
                "severity": "high",
                "confidence_score": 80,
            }],
            "summary": {"deal_risk_score": 50},
        }
        result = parse_scan_response(json.dumps(payload))
        assert len(result["insights"]) == 1
        assert result["insights"][0]["title"] == "Test"
        assert result["summary"]["deal_risk_score"] == 50

    def test_missing_findings_key_uses_default(self):
        """Clé 'insights' absente → Pydantic utilise [] par défaut (pas de fallback)."""
        payload = {"summary": {"total_insights": 0}}
        result = parse_scan_response(json.dumps(payload))
        assert result["insights"] == []
        assert "deal_risk_score" in result["summary"]

    def test_invalid_json_returns_fallback(self):
        result = parse_scan_response("ceci n'est pas du JSON {{{")
        assert result["insights"] == []
        assert "deal_risk_score" in result["summary"]

    def test_empty_string_returns_fallback(self):
        result = parse_scan_response("")
        assert result["insights"] == []

    def test_empty_findings_array_is_valid(self):
        payload = {"insights": [], "summary": {"total_insights": 0}}
        result = parse_scan_response(json.dumps(payload))
        assert result["insights"] == []
        assert result["summary"]["total_insights"] == 0


# ═══════════════════════════════════════════════════════════════
# Couche 1 — store_insights (with mock DB)
# ═══════════════════════════════════════════════════════════════


def _make_insight(**overrides) -> dict:
    """Build a minimal valid insight dict for testing."""
    base = {
        "type": "red_flag",
        "severity": "high",
        "confidence_score": 80,
        "title": "Test Insight",
        "description": "Description détaillée du insight.",
        "source_id": "src-001",
        "source_page": 3,
        "source_section": "Financials",
        "source_quote": "Extrait exact.",
    }
    return {**base, **overrides}


class TestStoreInsights:
    """store_insights validates, normalizes, and batch-inserts insights into DB."""

    async def test_valid_insight_is_inserted(self, capturing_supabase):
        count = await store_insights(
            capturing_supabase,
            insights=[_make_insight()],
            workspace_id="workspace-1",
            organization_id="org-1",
        )
        assert count == 1
        assert len(capturing_supabase.captured_inserts) == 1
        inserted_row = capturing_supabase.captured_inserts[0][0]
        assert inserted_row["title"] == "Test Insight"
        assert inserted_row["workspace_id"] == "workspace-1"
        assert inserted_row["organization_id"] == "org-1"
        assert inserted_row["status"] == "pending"

    async def test_insight_without_title_is_skipped(self, capturing_supabase):
        count = await store_insights(
            capturing_supabase,
            insights=[_make_insight(title=None)],
            workspace_id="workspace-1",
            organization_id="org-1",
        )
        assert count == 0
        assert len(capturing_supabase.captured_inserts) == 0

    async def test_insight_without_description_is_skipped(self, capturing_supabase):
        count = await store_insights(
            capturing_supabase,
            insights=[_make_insight(description=None)],
            workspace_id="workspace-1",
            organization_id="org-1",
        )
        assert count == 0

    async def test_empty_insights_list_returns_0_without_db_call(self, capturing_supabase):
        count = await store_insights(
            capturing_supabase,
            insights=[],
            workspace_id="workspace-1",
            organization_id="org-1",
        )
        assert count == 0
        assert len(capturing_supabase.captured_inserts) == 0

    async def test_title_is_truncated_to_500_chars(self, capturing_supabase):
        long_title = "T" * 600
        await store_insights(
            capturing_supabase,
            insights=[_make_insight(title=long_title)],
            workspace_id="workspace-1",
            organization_id="org-1",
        )
        inserted_row = capturing_supabase.captured_inserts[0][0]
        assert len(inserted_row["title"]) == 500

    async def test_empty_source_quote_stored_as_none(self, capturing_supabase):
        await store_insights(
            capturing_supabase,
            insights=[_make_insight(source_quote="")],
            workspace_id="workspace-1",
            organization_id="org-1",
        )
        inserted_row = capturing_supabase.captured_inserts[0][0]
        assert inserted_row["source_quote"] is None

    async def test_55_insights_split_into_two_batches(self, capturing_supabase):
        insights = [_make_insight(title=f"Insight {i}") for i in range(55)]
        count = await store_insights(
            capturing_supabase,
            insights=insights,
            workspace_id="workspace-1",
            organization_id="org-1",
        )
        assert count == 55
        assert len(capturing_supabase.captured_inserts) == 2
        assert len(capturing_supabase.captured_inserts[0]) == 50
        assert len(capturing_supabase.captured_inserts[1]) == 5

    async def test_all_valid_types_accepted(self, capturing_supabase):
        for ftype in VALID_TYPES:
            insights = [_make_insight(title=f"Insight {ftype}", type=ftype)]
            count = await store_insights(
                capturing_supabase,
                insights=insights,
                workspace_id="workspace-1",
                organization_id="org-1",
            )
            assert count == 1
            row = capturing_supabase.captured_inserts[-1][0]
            assert row["type"] == ftype

    async def test_all_valid_severities_accepted(self, capturing_supabase):
        for severity in VALID_SEVERITIES:
            insights = [_make_insight(title=f"Insight {severity}", severity=severity)]
            count = await store_insights(
                capturing_supabase,
                insights=insights,
                workspace_id="workspace-1",
                organization_id="org-1",
            )
            assert count == 1
            row = capturing_supabase.captured_inserts[-1][0]
            assert row["severity"] == severity


# ═══════════════════════════════════════════════════════════════
# Couche 2 — run_scan (orchestration avec mocks)
# ═══════════════════════════════════════════════════════════════


class TestRunScan:
    """run_scan orchestrates the full scanning pipeline.

    DB and LLM are mocked. store_insights is also patched to isolate
    orchestration logic from DB insertion details (tested separately above).
    """

    @pytest.fixture
    def supabase_with_sources(self, two_sources):
        db = MagicMock()
        sources_result = MagicMock(data=two_sources)
        (
            db.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .eq.return_value
            .order.return_value
            .execute.return_value
        ) = sources_result
        db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trace-1"}])
        return db

    @pytest.fixture
    def supabase_no_sources(self):
        db = MagicMock()
        (
            db.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .eq.return_value
            .order.return_value
            .execute.return_value
        ) = MagicMock(data=[])
        db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        return db

    async def test_no_sources_returns_skipped(self, supabase_no_sources):
        with patch("apps.worker.app.agents.scanner.safe_get_list", return_value=[]):
            result = await run_scan(
                supabase_no_sources,
                {"workspace_id": "workspace-1", "organization_id": "org-1"},
            )
        assert result["status"] == "skipped"
        assert result["reason"] == "no_ready_sources"

    async def test_happy_path_returns_stats(self, supabase_with_sources, scanner_llm_response_json, two_sources):
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = make_llm_response(scanner_llm_response_json)

        with (
            patch("apps.worker.app.agents.scanner.safe_get_list", return_value=two_sources),
            patch("apps.worker.app.agents.scanner.get_llm", return_value=mock_llm),
            patch("apps.worker.app.agents.scanner.store_insights", new=AsyncMock(return_value=3)) as mock_store,
        ):
            result = await run_scan(
                supabase_with_sources,
                {"workspace_id": "workspace-1", "organization_id": "org-1"},
            )

        assert result["workspace_id"] == "workspace-1"
        assert result["sources_scanned"] == 2
        assert result["insights_created"] == 3
        assert result["input_tokens"] == 500
        assert result["output_tokens"] == 300
        assert "cost_usd" in result
        assert "duration_ms" in result

        mock_llm.generate.assert_awaited_once()
        call_kwargs = mock_llm.generate.call_args.kwargs
        assert call_kwargs["json_mode"] is True
        assert call_kwargs["temperature"] == 0.1

        mock_store.assert_awaited_once()
        store_call = mock_store.call_args
        assert store_call.kwargs["workspace_id"] == "workspace-1"
        assert store_call.kwargs["organization_id"] == "org-1"
        assert len(store_call.kwargs["insights"]) == 3

    async def test_llm_exception_marks_deal_as_failed(self, supabase_with_sources, two_sources):
        failing_llm = AsyncMock()
        failing_llm.generate.side_effect = RuntimeError("API timeout")

        with (
            patch("apps.worker.app.agents.scanner.safe_get_list", return_value=two_sources),
            patch("apps.worker.app.agents.scanner.get_llm", return_value=failing_llm),
        ):
            with pytest.raises(RuntimeError, match="API timeout"):
                await run_scan(
                    supabase_with_sources,
                    {"workspace_id": "workspace-1", "organization_id": "org-1"},
                )

        update_calls = supabase_with_sources.table.return_value.update.call_args_list
        assert any(
            call.args and "scan_status" in str(call.args[0]) and "failed" in str(call.args[0])
            for call in update_calls
        ), "Expected workspace to be marked as scan_status='failed'"

    async def test_deal_status_set_to_scanning_at_start(self, supabase_with_sources, two_sources):
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = make_llm_response(
            json.dumps({"insights": [], "summary": {}})
        )

        update_order: list[str] = []
        original_update = supabase_with_sources.table.return_value.update

        def tracking_update(data):
            status = data.get("scan_status")
            if status:
                update_order.append(status)
            return original_update(data)

        supabase_with_sources.table.return_value.update = tracking_update

        with (
            patch("apps.worker.app.agents.scanner.safe_get_list", return_value=two_sources),
            patch("apps.worker.app.agents.scanner.get_llm", return_value=mock_llm),
            patch("apps.worker.app.agents.scanner.store_insights", new=AsyncMock(return_value=0)),
        ):
            await run_scan(
                supabase_with_sources,
                {"workspace_id": "workspace-1", "organization_id": "org-1"},
            )

        assert update_order[0] == "scanning"
        assert update_order[-1] == "scanned"
