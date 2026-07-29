"""
Shared fixtures for all tests.

Supabase and LLM are always mocked — no external calls in tests.
LLM responses use stored fixture data (not real API calls).
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.llm.types import LLMResponse, LLMUsage

# ─── Supabase mock helpers ──────────────────────────────────────


class _SupabaseChain(MagicMock):
    """Supabase query builder mock.

    Supports chaining: .table(...).select(...).eq(...).execute()
    Each method returns self so chains work naturally.
    `.execute()` returns a configurable result.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._execute_result = MagicMock(data=[])

    def configure_execute(self, data: list):
        """Set what .execute() will return (as .data)."""
        self._execute_result = MagicMock(data=data)
        return self

    def execute(self, *args, **kwargs):
        return self._execute_result


@pytest.fixture
def mock_supabase():
    """A minimal Supabase client mock.

    All chained calls (.table, .select, .eq, .update, .insert, .delete, .order, .in_)
    return a MagicMock that chains further. Use `mock_supabase.table.return_value`
    to configure specific responses, or use `capturing_supabase` for insert tracking.
    """
    db = MagicMock()
    # Default execute returns empty data
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(data=[])
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
    return db


@pytest.fixture
def capturing_supabase():
    """A Supabase mock that captures every insert() call.

    Access `db.captured_inserts` to assert on what was inserted.
    Each insert returns data equal to the inserted batch (simulates success).
    """
    db = MagicMock()
    captured: list[list[dict]] = []

    def _insert_side_effect(batch):
        captured.append(batch)
        result = MagicMock()
        result.data = list(batch)  # Return same rows to simulate successful insert
        exec_mock = MagicMock(return_value=result)
        return MagicMock(execute=exec_mock)

    # Wire insert side_effect regardless of which table is used
    db.table.return_value.insert.side_effect = _insert_side_effect
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    db.captured_inserts = captured
    return db


# ─── LLM mock helpers ───────────────────────────────────────────


def make_llm_response(content: str, input_tokens: int = 500, output_tokens: int = 300) -> LLMResponse:
    """Build a fake LLMResponse with the given content."""
    return LLMResponse(
        content=content,
        usage=LLMUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round((input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000, 6),
            model="claude-sonnet-4-20250514",
        ),
    )


@pytest.fixture
def mock_llm():
    """A mock LLM provider where generate() can be configured per test."""
    llm = AsyncMock()
    llm.generate.return_value = make_llm_response('{"insights": [], "summary": {}}')
    return llm


# ─── Scanner fixture data ───────────────────────────────────────


SCANNER_FIXTURE_RESPONSE = {
    "insights": [
        {
            "type": "red_flag",
            "severity": "high",
            "confidence_score": 85,
            "title": "Incohérence valorisation mémo vs term sheet",
            "description": "La valorisation pré-money dans le mémo d'investissement (50M€) est 20% supérieure à celle du term sheet (42M€). Incohérence à clarifier avant closing.",
            "source_id": "src-001",
            "source_page": 3,
            "source_section": "Valorisation",
            "source_quote": "Valorisation pré-money : 50M€ (mémo) vs 42M€ (term sheet)",
        },
        {
            "type": "metric",
            "severity": "low",
            "confidence_score": 95,
            "title": "ARR 2024 : 8M€",
            "description": "Le revenu récurrent annuel pour 2024 est de 8M€, en croissance de 45% vs 2023.",
            "source_id": "src-002",
            "source_page": 7,
            "source_section": "Financials",
            "source_quote": "ARR 2024 : 8,0M€ (+45% YoY)",
        },
        {
            "type": "missing_info",
            "severity": "medium",
            "confidence_score": 70,
            "title": "Cap table post-opération absente",
            "description": "Aucun document ne présente la cap table après dilution. Information nécessaire pour évaluer les droits des investisseurs.",
            "source_id": None,
            "source_page": None,
            "source_section": None,
            "source_quote": None,
        },
    ],
    "summary": {
        "total_insights": 3,
        "critical_count": 0,
        "high_count": 1,
        "medium_count": 1,
        "low_count": 1,
        "deal_risk_score": 35,
        "key_observation": "Dossier globalement solide. L'incohérence de valorisation est le point bloquant principal.",
    },
}


@pytest.fixture
def scanner_llm_response_json() -> str:
    """Serialized fixture response for the Scanner LLM call."""
    return json.dumps(SCANNER_FIXTURE_RESPONSE)


# ─── Source fixtures ────────────────────────────────────────────


def make_source(
    source_id: str = "src-001",
    name: str = "Investment Memo.pdf",
    file_type: str = "pdf",
    extracted_text: str = "Le présent mémo décrit l'opportunité d'investissement dans Acme SAS.",
    page_count: int = 12,
    word_count: int = 5000,
) -> dict:
    """Build a fake source dict as returned by the DB."""
    return {
        "id": source_id,
        "name": name,
        "type": file_type,
        "extracted_text": extracted_text,
        "page_count": page_count,
        "word_count": word_count,
    }


@pytest.fixture
def sample_source() -> dict:
    return make_source()


@pytest.fixture
def two_sources() -> list[dict]:
    return [
        make_source("src-001", "Investment Memo.pdf", extracted_text="Mémo principal du workspace."),
        make_source("src-002", "Business Plan.xlsx", extracted_text="Projections financières 2024-2028."),
    ]
