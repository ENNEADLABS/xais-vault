"""
Edge-case tests pour researcher_helpers.py.

Complète test_researcher.py avec les cas limites non couverts :
- source absente du map (Document inconnu)
- source_quote du insight dans le prompt
- truncation du contenu dans store_investigation_result
"""

from unittest.mock import AsyncMock, MagicMock

from apps.worker.app.agents.researcher_helpers import (
    build_research_prompt,
    search_workspace_documents,
    store_investigation_result,
)

# ═══════════════════════════════════════════════════════════════
# search_workspace_documents — source manquante
# ═══════════════════════════════════════════════════════════════


class TestSearchDealDocumentsEdgeCases:
    async def test_handles_missing_source_gracefully(self):
        """Un chunk dont le source_id n'est pas en DB reçoit 'Document inconnu'."""
        chunk = {"source_id": "orphan-src", "content": "Texte orphelin.", "similarity": 0.7}

        db = MagicMock()
        db.rpc.return_value.execute.return_value = MagicMock(data=[chunk])
        # La table sources ne retourne rien pour ce source_id
        db.table.return_value.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[])

        embedder = AsyncMock()
        embedder.embed_query.return_value = [0.0] * 1536

        result = await search_workspace_documents(db, embedder, "query", "workspace-1")

        assert len(result) == 1
        assert result[0]["source_name"] == "Document inconnu"
        assert result[0]["source_type"] == "?"


# ═══════════════════════════════════════════════════════════════
# build_research_prompt — insight avec/sans source_quote
# ═══════════════════════════════════════════════════════════════


class TestBuildResearchPromptEdgeCases:
    def test_finding_source_quote_appears_in_block(self):
        """Quand le insight a une source_quote, elle apparaît dans le bloc insight."""
        insight = {
            "id": "f-1",
            "title": "Insight avec citation",
            "type": "red_flag",
            "severity": "high",
            "description": "Description.",
            "source_quote": "Extrait clé du document.",
        }
        prompt = build_research_prompt("Question ?", insight, [], [])
        assert "Extrait clé du document." in prompt

    def test_finding_without_source_quote_no_error(self):
        """Insight sans source_quote ne lève pas d'erreur et inclut quand même le titre."""
        insight = {
            "id": "f-1",
            "title": "Insight sans citation",
            "type": "observation",
            "severity": "low",
            "description": "Pas de citation disponible.",
            # source_quote absent
        }
        prompt = build_research_prompt("Question ?", insight, [], [])
        assert "Insight sans citation" in prompt
        assert "Extrait cité" not in prompt


# ═══════════════════════════════════════════════════════════════
# store_investigation_result — truncation doc_references
# ═══════════════════════════════════════════════════════════════


class TestStoreInvestigationResultEdgeCases:
    async def test_doc_reference_content_truncated_to_300(self, mock_supabase):
        """chunk.content > 300 chars est tronqué dans les doc_references stockées."""
        long_content = "C" * 500
        chunks = [
            {
                "source_id": "src-1",
                "page_number": 1,
                "section_title": None,
                "content": long_content,
            }
        ]

        await store_investigation_result(
            mock_supabase,
            investigation_id="inv-1",
            report="# Rapport",
            doc_references=chunks,
            web_sources=[],
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            model_used="claude-opus-4-6",
        )

        update_data = mock_supabase.table.return_value.update.call_args.args[0]
        assert len(update_data["doc_references"][0]["quote"]) == 300
