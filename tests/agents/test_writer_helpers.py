"""
Edge-case tests pour writer_helpers.py.

Complète test_writer.py avec les cas limites non couverts :
- workspace sans scan_summary
- source_quote du insight dans le prompt
- pas de truncation pour dd_report
- truncation investment_memo à 2000 chars
- insight sans source_quote → pas de ligne Citation
"""


from apps.worker.app.agents.writer_helpers import (
    INVESTIGATION_MAX_CHARS,
    DealContext,
    build_writer_prompt,
)


def _make_deal(**overrides) -> dict:
    base = {
        "id": "workspace-001",
        "name": "Acme Series B",
        "target_company": "Acme SAS",
        "sector": "SaaS",
        "deal_type": "Series B",
    }
    return {**base, **overrides}


def _make_finding(idx: int = 1, **overrides) -> dict:
    base = {
        "id": f"insight-{idx:03d}",
        "title": f"Insight {idx}",
        "description": f"Description {idx}.",
        "severity": "high",
        "type": "red_flag",
        "source_quote": f"Citation {idx}.",
        "verification": {"verdict": "confirmed", "explanation": "OK."},
    }
    return {**base, **overrides}


def _make_investigation(idx: int = 1, report: str = "Rapport court.", **overrides) -> dict:
    base = {
        "id": f"inv-{idx:03d}",
        "question": f"Question {idx}?",
        "report": report,
    }
    return {**base, **overrides}


def _make_context(**overrides) -> DealContext:
    defaults = {
        "workspace": _make_deal(),
        "sources": [],
        "insights": [],
        "investigations": [],
        "total_sources": 0,
        "total_insights": 0,
        "total_investigations": 0,
    }
    defaults.update(overrides)
    return DealContext(**defaults)


# ═══════════════════════════════════════════════════════════════
# build_writer_prompt — edge cases
# ═══════════════════════════════════════════════════════════════


class TestBuildWriterPromptEdgeCases:
    def test_no_scan_summary_section_absent(self):
        """Workspace sans scan_summary → la section RÉSUMÉ DU SCAN n'est pas injectée."""
        ctx = _make_context(workspace=_make_deal(scan_summary=None))
        prompt = build_writer_prompt(ctx, "investment_memo")
        assert "RÉSUMÉ DU SCAN" not in prompt

    def test_finding_source_quote_appears_as_citation(self):
        """Insight avec source_quote → ligne 'Citation: ...' dans le prompt."""
        insight = _make_finding(1, source_quote="Extrait crucial visible.")
        ctx = _make_context(insights=[insight], total_insights=1)
        prompt = build_writer_prompt(ctx, "investment_memo")
        assert "Extrait crucial visible." in prompt

    def test_finding_without_source_quote_no_citation_line(self):
        """Insight sans source_quote → aucune ligne 'Citation:' dans le prompt."""
        insight = _make_finding(1, source_quote=None)
        ctx = _make_context(insights=[insight], total_insights=1)
        prompt = build_writer_prompt(ctx, "investment_memo")
        assert "Citation:" not in prompt

    def test_dd_report_does_not_truncate_investigations(self):
        """Pour dd_report, INVESTIGATION_MAX_CHARS est None → pas de troncature."""
        assert INVESTIGATION_MAX_CHARS["dd_report"] is None

        long_report = "R" * 5000
        inv = _make_investigation(1, report=long_report)
        ctx = _make_context(investigations=[inv], total_investigations=1)
        prompt = build_writer_prompt(ctx, "dd_report")
        assert "[... tronqué ...]" not in prompt

    def test_investment_memo_truncates_investigations_at_2000(self):
        """Pour investment_memo, les rapports d'investigation sont tronqués à 2000 chars."""
        assert INVESTIGATION_MAX_CHARS["investment_memo"] == 2000

        long_report = "M" * 3000
        inv = _make_investigation(1, report=long_report)
        ctx = _make_context(investigations=[inv], total_investigations=1)
        prompt = build_writer_prompt(ctx, "investment_memo")
        assert "[... tronqué ...]" in prompt
        # Le rapport est coupé à 2000, pas avant
        assert "M" * 2000 in prompt
        assert "M" * 2001 not in prompt
