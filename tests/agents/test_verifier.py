"""
Tests for the Verifier Agent (apps/worker/app/agents/verifier.py)
and its helpers (apps/worker/app/agents/verifier_helpers.py).

Pyramide des tests :
  Couche 1 — Unitaires (fonctions pures) :
    - build_verification_prompt  : 6 cas
    - parse_verification_response : 6 cas
    - VERDICT_TO_STATUS mapping   : 1 cas
  Couche 1 — Unitaires (avec mock DB) :
    - update_insight_verification : 4 cas
  Couche 2 — Intégration (orchestration run_verification avec mocks) :
    - run_verification            : 5 cas

LLM toujours mocké avec des réponses fixtures — aucun appel API réel.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.worker.app.agents.verifier import run_verification
from apps.worker.app.agents.verifier_helpers import (
    VALID_VERDICTS,
    VERDICT_TO_STATUS,
    build_verification_prompt,
    parse_verification_response,
    update_insight_verification,
)
from tests.conftest import make_llm_response, make_source

# ─── Fixtures ───────────────────────────────────────────────────


def make_insight(**overrides) -> dict:
    """Minimal valid insight dict as returned by the DB."""
    base = {
        "id": "insight-001",
        "title": "Incohérence valorisation",
        "description": "La valorisation dans le mémo diffère du term sheet.",
        "type": "red_flag",
        "severity": "high",
        "confidence_score": 85,
        "source_id": "src-001",
        "source_page": 3,
        "source_section": "Valorisation",
        "source_quote": "Valorisation pré-money : 50M€",
    }
    return {**base, **overrides}


VERIFIER_FIXTURE_RESPONSE = {
    "verdict": "confirmed",
    "evidence": [
        {
            "source_id": "src-001",
            "page": 3,
            "quote": "Valorisation pré-money : 50M€ (mémo) vs 42M€ (term sheet)",
            "supports_insight": True,
        },
        {
            "source_id": "src-002",
            "page": 15,
            "quote": "La valorisation retenue pour ce tour est de 42M€.",
            "supports_insight": True,
        },
    ],
    "explanation": "Deux documents indépendants confirment l'écart de valorisation. Le mémo mentionne 50M€ tandis que le term sheet officiel retient 42M€.",
}


# ═══════════════════════════════════════════════════════════════
# Couche 1 — build_verification_prompt (pure function)
# ═══════════════════════════════════════════════════════════════


class TestBuildVerificationPrompt:
    """build_verification_prompt assembles insight + all source texts."""

    def test_includes_insight_title(self):
        insight = make_insight(title="Test Insight Title")
        prompt = build_verification_prompt(insight, [])
        assert "Test Insight Title" in prompt

    def test_includes_insight_description(self):
        insight = make_insight(description="Description précise du problème.")
        prompt = build_verification_prompt(insight, [])
        assert "Description précise du problème." in prompt

    def test_includes_source_id_and_name(self):
        sources = [make_source("src-abc", "Memo.pdf", extracted_text="Contenu.")]
        prompt = build_verification_prompt(make_insight(), sources)
        assert "SOURCE_ID: src-abc" in prompt
        assert "DOCUMENT: Memo.pdf" in prompt

    def test_includes_source_quote_when_present(self):
        insight = make_insight(source_quote="Extrait crucial du document.")
        prompt = build_verification_prompt(insight, [])
        assert "Extrait crucial du document." in prompt

    def test_no_source_quote_when_none(self):
        insight = make_insight(source_quote=None)
        prompt = build_verification_prompt(insight, [])
        # Should not raise and should still include insight title
        assert "Incohérence valorisation" in prompt

    def test_truncates_oversized_source(self):
        huge_text = "x" * 500_000
        sources = [make_source(extracted_text=huge_text)]
        prompt = build_verification_prompt(make_insight(), sources)
        assert "[... document tronqué ...]" in prompt

    def test_omits_source_when_budget_exhausted(self):
        big_text = "x" * 500_000
        sources = [
            make_source("s1", "Big.pdf", extracted_text=big_text),
            make_source("s2", "Overflow.pdf", extracted_text="Ce texte ne doit pas apparaître."),
        ]
        prompt = build_verification_prompt(make_insight(), sources)
        assert "limite de contexte atteinte" in prompt
        assert "Ce texte ne doit pas apparaître." not in prompt

    def test_insight_section_appears_before_documents(self):
        sources = [make_source(extracted_text="Texte de la source.")]
        prompt = build_verification_prompt(make_insight(), sources)
        finding_pos = prompt.find("INSIGHT À VÉRIFIER")
        docs_pos = prompt.find("DOCUMENTS DU DOSSIER")
        assert finding_pos < docs_pos


# ═══════════════════════════════════════════════════════════════
# Couche 1 — parse_verification_response (pure function)
# ═══════════════════════════════════════════════════════════════


class TestParseVerificationResponse:
    """parse_verification_response parses LLM JSON output with fallbacks."""

    def test_valid_response_returns_all_fields(self):
        result = parse_verification_response(json.dumps(VERIFIER_FIXTURE_RESPONSE))
        assert result["verdict"] == "confirmed"
        assert len(result["evidence"]) == 2
        assert "confirment l'écart" in result["explanation"]

    def test_all_valid_verdicts_accepted(self):
        for verdict in VALID_VERDICTS:
            data = {"verdict": verdict, "evidence": [], "explanation": "OK."}
            result = parse_verification_response(json.dumps(data))
            assert result["verdict"] == verdict

    def test_invalid_verdict_falls_back_to_inconclusive(self):
        data = {"verdict": "maybe", "evidence": [], "explanation": "Incertain."}
        result = parse_verification_response(json.dumps(data))
        assert result["verdict"] == "inconclusive"

    def test_bad_json_returns_inconclusive_fallback(self):
        result = parse_verification_response("not valid json {{{")
        assert result["verdict"] == "inconclusive"
        assert result["evidence"] == []
        assert isinstance(result["explanation"], str)

    def test_evidence_without_source_id_is_filtered(self):
        data = {
            "verdict": "confirmed",
            "evidence": [
                {"source_id": None, "quote": "Extrait valide.", "supports_insight": True},
                {"source_id": "src-1", "quote": "Autre extrait.", "supports_insight": False},
            ],
            "explanation": "Test.",
        }
        result = parse_verification_response(json.dumps(data))
        assert len(result["evidence"]) == 1
        assert result["evidence"][0]["source_id"] == "src-1"

    def test_evidence_without_quote_is_filtered(self):
        data = {
            "verdict": "nuanced",
            "evidence": [
                {"source_id": "src-1", "quote": "", "supports_insight": True},
                {"source_id": "src-2", "quote": "Extrait réel.", "supports_insight": True},
            ],
            "explanation": "Nuancé.",
        }
        result = parse_verification_response(json.dumps(data))
        assert len(result["evidence"]) == 1

    def test_quote_is_truncated_to_300_chars(self):
        long_quote = "A" * 500
        data = {
            "verdict": "confirmed",
            "evidence": [{"source_id": "src-1", "quote": long_quote, "supports_insight": True}],
            "explanation": "OK.",
        }
        result = parse_verification_response(json.dumps(data))
        assert len(result["evidence"][0]["quote"]) == 300


# ═══════════════════════════════════════════════════════════════
# Couche 1 — VERDICT_TO_STATUS mapping
# ═══════════════════════════════════════════════════════════════


class TestVerdictToStatusMapping:
    """Each verdict must map to the correct insight status."""

    def test_all_verdict_mappings(self):
        assert VERDICT_TO_STATUS["confirmed"] == "confirmed"
        assert VERDICT_TO_STATUS["contradicted"] == "rejected"
        assert VERDICT_TO_STATUS["inconclusive"] == "pending"
        assert VERDICT_TO_STATUS["nuanced"] == "pending"

    def test_all_valid_verdicts_have_a_mapping(self):
        for verdict in VALID_VERDICTS:
            assert verdict in VERDICT_TO_STATUS, f"Missing mapping for verdict '{verdict}'"


# ═══════════════════════════════════════════════════════════════
# Couche 1 — update_insight_verification (with mock DB)
# ═══════════════════════════════════════════════════════════════


class TestUpdateInsightVerification:
    """update_insight_verification writes verification JSONB and updates status."""

    async def test_updates_insight_status_confirmed(self, mock_supabase):
        verification = {"verdict": "confirmed", "evidence": [], "explanation": "OK."}
        await update_insight_verification(
            mock_supabase,
            insight_id="insight-1",
            verification=verification,
        )
        update_data = mock_supabase.table.return_value.update.call_args.args[0]
        assert update_data["status"] == "confirmed"

    async def test_updates_insight_status_rejected_for_contradicted(self, mock_supabase):
        verification = {"verdict": "contradicted", "evidence": [], "explanation": "Contradictoire."}
        await update_insight_verification(
            mock_supabase,
            insight_id="insight-1",
            verification=verification,
        )
        update_data = mock_supabase.table.return_value.update.call_args.args[0]
        assert update_data["status"] == "rejected"

    async def test_updates_insight_status_pending_for_inconclusive(self, mock_supabase):
        verification = {"verdict": "inconclusive", "evidence": [], "explanation": "Pas clair."}
        await update_insight_verification(
            mock_supabase,
            insight_id="insight-1",
            verification=verification,
        )
        update_data = mock_supabase.table.return_value.update.call_args.args[0]
        assert update_data["status"] == "pending"

    async def test_agent_trace_id_included_in_verification_jsonb(self, mock_supabase):
        verification = {"verdict": "nuanced", "evidence": [], "explanation": "Nuancé."}
        await update_insight_verification(
            mock_supabase,
            insight_id="insight-1",
            verification=verification,
            agent_trace_id="trace-xyz",
        )
        update_data = mock_supabase.table.return_value.update.call_args.args[0]
        assert update_data["verification"]["agent_trace_id"] == "trace-xyz"


# ═══════════════════════════════════════════════════════════════
# Couche 2 — run_verification (orchestration avec mocks)
# ═══════════════════════════════════════════════════════════════


class TestRunVerification:
    """run_verification orchestrates the full verification pipeline.

    DB and LLM are mocked. update_insight_verification is also patched
    to isolate orchestration from DB update details (tested above).
    """

    @pytest.fixture
    def supabase_with_data(self, two_sources):
        """Supabase mock that returns a insight + two sources."""
        db = MagicMock()
        insight = make_insight()

        # insight lookup
        (
            db.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .execute.return_value
        ) = MagicMock(data=[insight])

        db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trace-99"}])
        return db

    @pytest.fixture
    def supabase_no_finding(self):
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

    async def test_insight_not_found_raises_value_error(self, supabase_no_finding):
        with patch("apps.worker.app.agents.verifier.safe_get_one", return_value=None):
            with pytest.raises(ValueError, match="not found"):
                await run_verification(
                    supabase_no_finding,
                    {"insight_id": "missing", "workspace_id": "workspace-1", "organization_id": "org-1"},
                )

    async def test_no_sources_returns_inconclusive(self, supabase_with_data):
        insight = make_insight()
        with (
            patch("apps.worker.app.agents.verifier.safe_get_one", return_value=insight),
            patch("apps.worker.app.agents.verifier.safe_get_list", return_value=[]),
            patch("apps.worker.app.agents.verifier.update_insight_verification", new=AsyncMock()) as mock_update,
        ):
            result = await run_verification(
                supabase_with_data,
                {"insight_id": "insight-001", "workspace_id": "workspace-1", "organization_id": "org-1"},
            )

        assert result["verdict"] == "inconclusive"
        assert result["reason"] == "no_ready_sources"

        mock_update.assert_awaited_once()
        call_kwargs = mock_update.call_args.kwargs
        assert call_kwargs["verification"]["verdict"] == "inconclusive"

    async def test_happy_path_returns_stats(self, supabase_with_data, two_sources):
        insight = make_insight()
        fixture_json = json.dumps(VERIFIER_FIXTURE_RESPONSE)
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = make_llm_response(fixture_json)

        with (
            patch("apps.worker.app.agents.verifier.safe_get_one", return_value=insight),
            patch("apps.worker.app.agents.verifier.safe_get_list", return_value=two_sources),
            patch("apps.worker.app.agents.verifier.get_llm", return_value=mock_llm),
            patch("apps.worker.app.agents.verifier.update_insight_verification", new=AsyncMock()),
        ):
            result = await run_verification(
                supabase_with_data,
                {"insight_id": "insight-001", "workspace_id": "workspace-1", "organization_id": "org-1"},
            )

        assert result["insight_id"] == "insight-001"
        assert result["verdict"] == "confirmed"
        assert result["evidence_count"] == 2
        assert result["new_status"] == "confirmed"
        assert result["input_tokens"] == 500
        assert result["output_tokens"] == 300
        assert "cost_usd" in result
        assert "duration_ms" in result

        call_kwargs = mock_llm.generate.call_args.kwargs
        assert call_kwargs["json_mode"] is True
        assert call_kwargs["temperature"] == 0.1
        assert call_kwargs["max_tokens"] == 4096

    async def test_llm_exception_propagates(self, supabase_with_data, two_sources):
        insight = make_insight()
        failing_llm = AsyncMock()
        failing_llm.generate.side_effect = RuntimeError("LLM rate limit")

        with (
            patch("apps.worker.app.agents.verifier.safe_get_one", return_value=insight),
            patch("apps.worker.app.agents.verifier.safe_get_list", return_value=two_sources),
            patch("apps.worker.app.agents.verifier.get_llm", return_value=failing_llm),
        ):
            with pytest.raises(RuntimeError, match="LLM rate limit"):
                await run_verification(
                    supabase_with_data,
                    {"insight_id": "insight-001", "workspace_id": "workspace-1", "organization_id": "org-1"},
                )

    async def test_agent_trace_inserted_with_correct_type(self, supabase_with_data, two_sources):
        insight = make_insight()
        fixture_json = json.dumps(VERIFIER_FIXTURE_RESPONSE)
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = make_llm_response(fixture_json)

        with (
            patch("apps.worker.app.agents.verifier.safe_get_one", return_value=insight),
            patch("apps.worker.app.agents.verifier.safe_get_list", return_value=two_sources),
            patch("apps.worker.app.agents.verifier.get_llm", return_value=mock_llm),
            patch("apps.worker.app.agents.verifier.update_insight_verification", new=AsyncMock()),
        ):
            await run_verification(
                supabase_with_data,
                {"insight_id": "insight-001", "workspace_id": "workspace-1", "organization_id": "org-1"},
            )

        insert_calls = supabase_with_data.table.return_value.insert.call_args_list
        trace_call = next(
            (c for c in insert_calls if "agent_type" in str(c)),
            None,
        )
        assert trace_call is not None, "Expected agent_traces insert call"
        trace_data = trace_call.args[0]
        assert trace_data["agent_type"] == "verifier"
        assert trace_data["workspace_id"] == "workspace-1"
