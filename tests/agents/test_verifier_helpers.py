"""
Edge-case tests pour verifier_helpers.py.

Complète test_verifier.py avec les cas limites non couverts :
- evidence array vide valide
- supports_insight avec valeur par défaut True
"""

import json

from apps.worker.app.agents.verifier_helpers import parse_verification_response


class TestParseVerificationResponseEdgeCases:
    def test_empty_evidence_array_is_valid(self):
        """Liste evidence vide est valide — pas tous les verdicts ont des cross-refs."""
        data = {
            "verdict": "confirmed",
            "evidence": [],
            "explanation": "Confirmé sur la base du contexte global.",
        }
        result = parse_verification_response(json.dumps(data))
        assert result["verdict"] == "confirmed"
        assert result["evidence"] == []
        assert "Confirmé" in result["explanation"]

    def test_supports_finding_absent_defaults_to_true(self):
        """Evidence sans clé 'supports_insight' → bool par défaut True."""
        data = {
            "verdict": "confirmed",
            "evidence": [
                {
                    "source_id": "src-1",
                    "quote": "Extrait valide.",
                    # supports_insight volontairement absent
                }
            ],
            "explanation": "OK.",
        }
        result = parse_verification_response(json.dumps(data))
        assert len(result["evidence"]) == 1
        assert result["evidence"][0]["supports_insight"] is True

    def test_supports_finding_false_is_preserved(self):
        """supports_insight=False doit être conservé (ne pas être forcé à True)."""
        data = {
            "verdict": "contradicted",
            "evidence": [
                {
                    "source_id": "src-1",
                    "quote": "Ce passage contredit le insight.",
                    "supports_insight": False,
                }
            ],
            "explanation": "Contradictoire.",
        }
        result = parse_verification_response(json.dumps(data))
        assert result["evidence"][0]["supports_insight"] is False
