"""
Tests for the Researcher Agent (apps/worker/app/agents/researcher.py)
and its helpers (apps/worker/app/agents/researcher_helpers.py).

Pyramide des tests :
  Couche 1 — Unitaires (fonctions pures) :
    - build_web_query            : 3 cas
    - build_research_prompt      : 5 cas
  Couche 1 — Unitaires (avec mock DB/API) :
    - search_workspace_documents      : 3 cas
    - search_web                 : 4 cas
    - store_investigation_result : 2 cas
  Couche 2 — Intégration (orchestration run_investigation avec mocks) :
    - run_investigation           : 5 cas

LLM, Tavily et embedder toujours mockés — aucun appel API réel.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.worker.app.agents.researcher import run_investigation
from apps.worker.app.agents.researcher_helpers import (
    build_research_prompt,
    build_web_query,
    search_web,
    search_workspace_documents,
    store_investigation_result,
)
from tests.conftest import make_llm_response

# ─── Fixtures ───────────────────────────────────────────────────


def make_investigation(**overrides) -> dict:
    base = {
        "id": "inv-001",
        "question": "Quelle est la part de marché des concurrents directs ?",
        "scope": "both",
        "insight_id": None,
        "status": "pending",
    }
    return {**base, **overrides}


def make_finding_for_research(**overrides) -> dict:
    base = {
        "id": "insight-001",
        "title": "Part de marché incertaine",
        "type": "observation",
        "severity": "medium",
        "description": "Le mémo ne mentionne aucun concurrent direct.",
        "source_quote": "Nous sommes leaders sur notre marché.",
    }
    return {**base, **overrides}


FAKE_CHUNKS = [
    {
        "source_id": "src-001",
        "source_name": "Business Plan.pdf",
        "source_type": "pdf",
        "content": "Nous estimons notre part de marché à 15%.",
        "page_number": 4,
        "section_title": "Analyse de marché",
        "similarity": 0.87,
    },
    {
        "source_id": "src-002",
        "source_name": "Pitch Deck.pptx",
        "source_type": "pptx",
        "content": "Nos concurrents principaux sont Alpha Corp et Beta Ltd.",
        "page_number": 8,
        "section_title": None,
        "similarity": 0.73,
    },
]

FAKE_WEB_RESULTS = [
    {
        "url": "https://example.com/market-report",
        "title": "Rapport marché SaaS 2024",
        "snippet": "La croissance du marché SaaS est de 25% en 2024.",
        "accessed_at": "2026-03-14T10:00:00Z",
    },
]

FAKE_REPORT = "## Synthèse\nLes concurrents représentent 40% du marché.\n\n## Analyse documentaire\nSelon le business plan [Source: Business Plan.pdf, p.4], la part de marché est 15%."


# ═══════════════════════════════════════════════════════════════
# Couche 1 — build_web_query (pure function)
# ═══════════════════════════════════════════════════════════════


class TestBuildWebQuery:
    def test_question_only_without_finding(self):
        result = build_web_query("Quelle est la réglementation GDPR ?", None)
        assert "GDPR" in result

    def test_appends_finding_title_if_not_in_question(self):
        insight = make_finding_for_research(title="Alpha Corp concurrents")
        result = build_web_query("Analyse du marché", insight)
        assert "Analyse du marché" in result
        assert "Alpha Corp concurrents" in result

    def test_does_not_duplicate_title_if_already_in_question(self):
        insight = make_finding_for_research(title="Part de marché incertaine")
        result = build_web_query("La part de marché incertaine du workspace", insight)
        # Title should not be appended since it's already in the question (lowercased)
        assert result.count("incertaine") == 1

    def test_truncates_to_400_chars(self):
        long_question = "Q" * 500
        result = build_web_query(long_question, None)
        assert len(result) <= 400


# ═══════════════════════════════════════════════════════════════
# Couche 1 — build_research_prompt (pure function)
# ═══════════════════════════════════════════════════════════════


class TestBuildResearchPrompt:
    def test_includes_question(self):
        prompt = build_research_prompt("Quelle est la concurrence ?", None, [], [])
        assert "Quelle est la concurrence ?" in prompt

    def test_includes_finding_block_when_provided(self):
        insight = make_finding_for_research()
        prompt = build_research_prompt("Question test", insight, [], [])
        assert "INSIGHT DE RÉFÉRENCE" in prompt
        assert "Part de marché incertaine" in prompt

    def test_no_finding_block_when_none(self):
        prompt = build_research_prompt("Question test", None, [], [])
        assert "INSIGHT DE RÉFÉRENCE" not in prompt

    def test_includes_doc_chunks(self):
        prompt = build_research_prompt("Question", None, FAKE_CHUNKS, [])
        assert "Business Plan.pdf" in prompt
        assert "Nous estimons notre part de marché" in prompt
        assert "PASSAGES DOCUMENTAIRES" in prompt

    def test_no_docs_message_when_empty(self):
        prompt = build_research_prompt("Question", None, [], [])
        assert "Aucun passage pertinent" in prompt

    def test_includes_web_results(self):
        prompt = build_research_prompt("Question", None, [], FAKE_WEB_RESULTS)
        assert "Rapport marché SaaS 2024" in prompt
        assert "https://example.com/market-report" in prompt

    def test_no_web_message_when_empty(self):
        prompt = build_research_prompt("Question", None, [], [])
        assert "Aucune recherche web" in prompt

    def test_similarity_shown_as_percentage(self):
        prompt = build_research_prompt("Question", None, FAKE_CHUNKS, [])
        assert "87%" in prompt


# ═══════════════════════════════════════════════════════════════
# Couche 1 — search_workspace_documents (avec mocks)
# ═══════════════════════════════════════════════════════════════


class TestSearchDealDocuments:
    async def test_calls_rpc_with_correct_params(self):
        db = MagicMock()
        db.rpc.return_value.execute.return_value = MagicMock(data=[])
        mock_embedder = AsyncMock()
        mock_embedder.embed_query.return_value = [0.1] * 1536

        await search_workspace_documents(db, mock_embedder, "query test", "workspace-1")

        mock_embedder.embed_query.assert_awaited_once_with(
            "query test", dimensions=1536
        )
        db.rpc.assert_called_once_with(
            "search_chunks_hybrid",
            {
                "query_embedding": [0.1] * 1536,
                "query_text": "query test",
                "target_workspace_id": "workspace-1",
                "match_count": 50,
                "similarity_threshold": 0.3,
                "vector_weight": 0.7,
            },
        )

    async def test_enriches_chunks_with_source_name(self):
        chunk = {"source_id": "src-1", "content": "Texte du chunk.", "similarity": 0.8}
        source = {"id": "src-1", "name": "Memo.pdf", "type": "pdf"}

        db = MagicMock()
        db.rpc.return_value.execute.return_value = MagicMock(data=[chunk])
        db.table.return_value.select.return_value.in_.return_value.execute.return_value = MagicMock(
            data=[source]
        )

        mock_embedder = AsyncMock()
        mock_embedder.embed_query.return_value = [0.1] * 1536

        result = await search_workspace_documents(db, mock_embedder, "query", "workspace-1")

        assert result[0]["source_name"] == "Memo.pdf"

    async def test_returns_empty_list_when_no_results(self):
        db = MagicMock()
        db.rpc.return_value.execute.return_value = MagicMock(data=[])
        mock_embedder = AsyncMock()
        mock_embedder.embed_query.return_value = [0.1] * 1536

        result = await search_workspace_documents(db, mock_embedder, "query", "workspace-1")
        assert result == []


# ═══════════════════════════════════════════════════════════════
# Couche 1 — search_web (avec mocks Tavily)
# ═══════════════════════════════════════════════════════════════


class TestSearchWeb:
    async def test_returns_empty_list_when_no_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            result = await search_web("test query")
        assert result == []

    async def test_parses_tavily_results(self):
        fake_response = {
            "results": [
                {
                    "url": "https://ex.com",
                    "title": "Titre",
                    "content": "Contenu court.",
                },
            ]
        }

        mock_client = MagicMock()
        mock_client.search.return_value = fake_response

        with (
            patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key"}),
            patch(
                "apps.worker.app.agents.researcher_helpers.TavilyClient",
                return_value=mock_client,
            ),
        ):
            result = await search_web("test query")

        assert len(result) == 1
        assert result[0]["url"] == "https://ex.com"
        assert result[0]["title"] == "Titre"
        assert result[0]["snippet"] == "Contenu court."

    async def test_tavily_error_returns_empty_list(self):
        mock_client = MagicMock()
        mock_client.search.side_effect = RuntimeError("API unavailable")

        with (
            patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key"}),
            patch(
                "apps.worker.app.agents.researcher_helpers.TavilyClient",
                return_value=mock_client,
            ),
        ):
            result = await search_web("test query")

        assert result == []

    async def test_snippet_is_truncated_to_500_chars(self):
        long_content = "C" * 1000
        fake_response = {
            "results": [{"url": "u", "title": "t", "content": long_content}]
        }

        mock_client = MagicMock()
        mock_client.search.return_value = fake_response

        with (
            patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key"}),
            patch(
                "apps.worker.app.agents.researcher_helpers.TavilyClient",
                return_value=mock_client,
            ),
        ):
            result = await search_web("test")

        assert len(result[0]["snippet"]) == 500


# ═══════════════════════════════════════════════════════════════
# Couche 1 — store_investigation_result (avec mock DB)
# ═══════════════════════════════════════════════════════════════


class TestStoreInvestigationResult:
    async def test_updates_investigation_with_completed_status(self, mock_supabase):
        await store_investigation_result(
            mock_supabase,
            investigation_id="inv-1",
            report="# Rapport",
            doc_references=[],
            web_sources=[],
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            model_used="claude-opus-4-6",
        )
        update_data = mock_supabase.table.return_value.update.call_args.args[0]
        assert update_data["status"] == "completed"
        assert update_data["report"] == "# Rapport"

    async def test_formats_doc_references_correctly(self, mock_supabase):
        chunks = [
            {
                "source_id": "src-1",
                "page_number": 3,
                "section_title": "Intro",
                "content": "Contenu du chunk.",
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
        doc_refs = update_data["doc_references"]
        assert len(doc_refs) == 1
        assert doc_refs[0]["source_id"] == "src-1"
        assert doc_refs[0]["page"] == 3
        assert doc_refs[0]["section"] == "Intro"


# ═══════════════════════════════════════════════════════════════
# Couche 2 — run_investigation (orchestration avec mocks)
# ═══════════════════════════════════════════════════════════════


class TestRunInvestigation:
    @pytest.fixture
    def supabase_with_data(self):
        db = MagicMock()
        investigation = make_investigation()

        (
            db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value
        ) = MagicMock(data=[investigation])

        db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "trace-1"}]
        )
        db.rpc.return_value.execute.return_value = MagicMock(data=[])
        return db

    @pytest.fixture
    def supabase_not_found(self):
        db = MagicMock()
        (
            db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value
        ) = MagicMock(data=[])
        db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        return db

    async def test_investigation_not_found_raises(self, supabase_not_found):
        with patch("apps.worker.app.agents.researcher.safe_get_one", return_value=None):
            with pytest.raises(ValueError, match="not found"):
                await run_investigation(
                    supabase_not_found,
                    {
                        "investigation_id": "missing",
                        "workspace_id": "d1",
                        "organization_id": "o1",
                    },
                )

    async def test_scope_documents_only_no_web_call(self, supabase_with_data):
        investigation = make_investigation(scope="documents")
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = make_llm_response(FAKE_REPORT)
        mock_embedder = AsyncMock()
        mock_embedder.embed_query.return_value = [0.1] * 1536

        with (
            patch(
                "apps.worker.app.agents.researcher.safe_get_one",
                return_value=investigation,
            ),
            patch("apps.worker.app.agents.researcher.get_llm", return_value=mock_llm),
            patch(
                "apps.worker.app.agents.researcher.get_embedder",
                return_value=mock_embedder,
            ),
            patch(
                "apps.worker.app.agents.researcher.search_web",
                new=AsyncMock(return_value=[]),
            ) as mock_web,
            patch(
                "apps.worker.app.agents.researcher.search_workspace_documents",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "apps.worker.app.agents.researcher.store_investigation_result",
                new=AsyncMock(),
            ),
        ):
            await run_investigation(
                supabase_with_data,
                {
                    "investigation_id": "inv-001",
                    "workspace_id": "d1",
                    "organization_id": "o1",
                },
            )

        mock_web.assert_not_awaited()

    async def test_scope_web_only_no_embed_call(self, supabase_with_data):
        investigation = make_investigation(scope="web")
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = make_llm_response(FAKE_REPORT)

        with (
            patch(
                "apps.worker.app.agents.researcher.safe_get_one",
                return_value=investigation,
            ),
            patch("apps.worker.app.agents.researcher.get_llm", return_value=mock_llm),
            patch(
                "apps.worker.app.agents.researcher.get_embedder"
            ) as mock_get_embedder,
            patch(
                "apps.worker.app.agents.researcher.search_web",
                new=AsyncMock(return_value=FAKE_WEB_RESULTS),
            ),
            patch(
                "apps.worker.app.agents.researcher.store_investigation_result",
                new=AsyncMock(),
            ),
        ):
            result = await run_investigation(
                supabase_with_data,
                {
                    "investigation_id": "inv-001",
                    "workspace_id": "d1",
                    "organization_id": "o1",
                },
            )

        mock_get_embedder.assert_not_called()
        assert result["web_results_found"] == len(FAKE_WEB_RESULTS)

    async def test_happy_path_returns_stats(self, supabase_with_data):
        investigation = make_investigation()
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = make_llm_response(FAKE_REPORT)
        mock_embedder = AsyncMock()
        mock_embedder.embed_query.return_value = [0.1] * 1536

        with (
            patch(
                "apps.worker.app.agents.researcher.safe_get_one",
                return_value=investigation,
            ),
            patch("apps.worker.app.agents.researcher.get_llm", return_value=mock_llm),
            patch(
                "apps.worker.app.agents.researcher.get_embedder",
                return_value=mock_embedder,
            ),
            patch(
                "apps.worker.app.agents.researcher.search_workspace_documents",
                new=AsyncMock(return_value=FAKE_CHUNKS),
            ),
            patch(
                "apps.worker.app.agents.researcher.search_web",
                new=AsyncMock(return_value=FAKE_WEB_RESULTS),
            ),
            patch(
                "apps.worker.app.agents.researcher.store_investigation_result",
                new=AsyncMock(),
            ),
        ):
            result = await run_investigation(
                supabase_with_data,
                {
                    "investigation_id": "inv-001",
                    "workspace_id": "workspace-1",
                    "organization_id": "org-1",
                },
            )

        assert result["investigation_id"] == "inv-001"
        assert result["doc_chunks_found"] == len(FAKE_CHUNKS)
        assert result["web_results_found"] == len(FAKE_WEB_RESULTS)
        assert result["report_length"] == len(FAKE_REPORT)
        assert "cost_usd" in result
        assert "duration_ms" in result

        call_kwargs = mock_llm.generate.call_args.kwargs
        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["max_tokens"] == 4096

    async def test_finding_status_updated_to_investigating(self, supabase_with_data):
        investigation = make_investigation(insight_id="insight-001")
        insight = make_finding_for_research()
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = make_llm_response(FAKE_REPORT)

        call_log: list[str] = []
        original_update = supabase_with_data.table.return_value.update

        def tracking_update(data):
            status = data.get("status")
            if status:
                call_log.append(status)
            return original_update(data)

        supabase_with_data.table.return_value.update = tracking_update

        def safe_get_one_side(result):
            data = result.data or []
            return data[0] if data else None

        with (
            patch(
                "apps.worker.app.agents.researcher.safe_get_one",
                side_effect=[investigation, insight],
            ),
            patch("apps.worker.app.agents.researcher.get_llm", return_value=mock_llm),
            patch(
                "apps.worker.app.agents.researcher.get_embedder",
                return_value=AsyncMock(
                    embed_query=AsyncMock(return_value=[0.1] * 1536)
                ),
            ),
            patch(
                "apps.worker.app.agents.researcher.search_workspace_documents",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "apps.worker.app.agents.researcher.search_web",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "apps.worker.app.agents.researcher.store_investigation_result",
                new=AsyncMock(),
            ),
        ):
            await run_investigation(
                supabase_with_data,
                {
                    "investigation_id": "inv-001",
                    "workspace_id": "d1",
                    "organization_id": "o1",
                },
            )

        assert "investigating" in call_log
