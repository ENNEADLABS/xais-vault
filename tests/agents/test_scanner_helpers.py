"""
Edge-case tests for scanner_helpers.py.

Ces tests complètent la couverture de test_scanner.py (build_scan_prompt,
parse_scan_response, store_insights) en ciblant les cas limites non couverts :
parsing JSON avec champs extra, markdown code blocks, insights invalides, etc.
"""

import json

from apps.worker.app.agents.scanner_helpers import parse_scan_response, store_insights


def _make_insight(**overrides) -> dict:
    base = {
        "type": "red_flag",
        "severity": "high",
        "confidence_score": 80,
        "title": "Test Insight",
        "description": "Description détaillée.",
        "source_id": "src-001",
        "source_page": 3,
        "source_section": "Financials",
        "source_quote": "Extrait.",
    }
    return {**base, **overrides}


# ═══════════════════════════════════════════════════════════════
# parse_scan_response — edge cases JSON
# ═══════════════════════════════════════════════════════════════


class TestParseScanResponseEdgeCases:
    def test_extra_fields_do_not_break_parsing(self):
        """Champs supplémentaires inattendus dans la réponse LLM sont ignorés par Pydantic."""
        payload = {
            "insights": [{"title": "OK", "description": "Desc."}],
            "summary": {},
            "model_version": "claude-opus-4",
            "unexpected_field": True,
        }
        result = parse_scan_response(json.dumps(payload))
        assert len(result["insights"]) == 1
        assert result["insights"][0]["title"] == "OK"
        # Pydantic ignore les champs inconnus
        assert "unexpected_field" not in result

    def test_markdown_codeblock_is_parsed(self):
        """Réponse wrappée dans ```json ... ``` est extraite et parsée correctement."""
        content = '```json\n{"insights": [{"title": "Test", "description": "Desc."}], "summary": {}}\n```'
        result = parse_scan_response(content)
        assert len(result["insights"]) == 1
        assert result["insights"][0]["title"] == "Test"

    def test_findings_not_a_list_returns_fallback(self):
        """Si 'insights' n'est pas une liste, Pydantic échoue → fallback."""
        payload = {"insights": "pas une liste", "summary": {}}
        result = parse_scan_response(json.dumps(payload))
        assert result["insights"] == []

    def test_parse_invalid_confidence_normalized(self):
        """confidence_score hors-bornes (>100 ou <0) est normalisé à 50."""
        payload = {
            "insights": [{"title": "F1", "description": "D1.", "confidence_score": 150}],
            "summary": {},
        }
        result = parse_scan_response(json.dumps(payload))
        assert len(result["insights"]) == 1
        assert result["insights"][0]["confidence_score"] == 50

    def test_parse_invalid_type_normalized_to_observation(self):
        """type invalide est normalisé à 'observation' par le validateur Pydantic."""
        payload = {
            "insights": [{"title": "F1", "description": "D1.", "type": "invalide"}],
            "summary": {},
        }
        result = parse_scan_response(json.dumps(payload))
        assert result["insights"][0]["type"] == "observation"

    def test_parse_invalid_severity_normalized_to_medium(self):
        """severity invalide est normalisée à 'medium' par le validateur Pydantic."""
        payload = {
            "insights": [{"title": "F1", "description": "D1.", "severity": "extreme"}],
            "summary": {},
        }
        result = parse_scan_response(json.dumps(payload))
        assert result["insights"][0]["severity"] == "medium"


# ═══════════════════════════════════════════════════════════════
# store_insights — edge cases DB
# ═══════════════════════════════════════════════════════════════


class TestStoreInsightsEdgeCases:
    async def test_source_quote_longer_than_500_is_truncated(self, capturing_supabase):
        long_quote = "Q" * 600
        await store_insights(
            capturing_supabase,
            insights=[_make_insight(source_quote=long_quote)],
            workspace_id="workspace-1",
            organization_id="org-1",
        )
        row = capturing_supabase.captured_inserts[0][0]
        assert len(row["source_quote"]) == 500

    async def test_all_insights_invalid_returns_0(self, capturing_supabase):
        """Tous les insights sans title/description → rien n'est inséré."""
        insights = [
            _make_insight(title=None),
            _make_insight(title=""),
            _make_insight(description=None),
        ]
        count = await store_insights(
            capturing_supabase,
            insights=insights,
            workspace_id="workspace-1",
            organization_id="org-1",
        )
        assert count == 0
        assert len(capturing_supabase.captured_inserts) == 0

    async def test_none_source_quote_key_stored_as_none(self, capturing_supabase):
        """Clé source_quote absente du dict → stocké comme None, pas chaîne vide."""
        insight = {
            "type": "observation",
            "severity": "low",
            "confidence_score": 60,
            "title": "Insight sans citation",
            "description": "Pas de citation disponible.",
            # source_quote volontairement absent
        }
        await store_insights(
            capturing_supabase,
            insights=[insight],
            workspace_id="workspace-1",
            organization_id="org-1",
        )
        row = capturing_supabase.captured_inserts[0][0]
        assert row["source_quote"] is None

    async def test_source_page_integer_is_preserved(self, capturing_supabase):
        """source_page entier est stocké tel quel."""
        await store_insights(
            capturing_supabase,
            insights=[_make_insight(source_page=42)],
            workspace_id="workspace-1",
            organization_id="org-1",
        )
        row = capturing_supabase.captured_inserts[0][0]
        assert row["source_page"] == 42

    async def test_empty_string_description_is_skipped(self, capturing_supabase):
        """description='' est falsy → insight sauté (même comportement que None)."""
        count = await store_insights(
            capturing_supabase,
            insights=[_make_insight(description="")],
            workspace_id="workspace-1",
            organization_id="org-1",
        )
        assert count == 0
