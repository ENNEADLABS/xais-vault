"""Tests unitaires des tools MCP avec client mocké."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from src.client import VaultAPIError
from src.tools import (
    chat,
    create_workspace,
    generate_deliverable,
    get_workspace,
    investigate_insight,
    list_insights,
    list_investigations,
    list_sources,
    list_workspaces,
    upload_text_source,
)


@pytest.fixture
def mock_ctx():
    """Contexte MCP avec VaultClient mocké."""
    ctx = MagicMock()
    ctx.state = {"client": AsyncMock()}
    return ctx


# ─── list_workspaces ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_deals_formats_output(mock_ctx):
    mock_ctx.state["client"].list_workspaces.return_value = {
        "data": [
            {
                "id": "d1", "emoji": "📁", "name": "Alpha",
                "status": "active", "source_count": 3, "insight_count": 5,
            },
        ],
    }
    result = await list_workspaces(mock_ctx)
    assert "Alpha" in result
    assert "d1" in result
    assert "3 sources" in result
    assert "5 insights" in result


@pytest.mark.asyncio
async def test_list_deals_empty(mock_ctx):
    mock_ctx.state["client"].list_workspaces.return_value = {"data": []}
    result = await list_workspaces(mock_ctx)
    assert "Aucun workspace" in result


@pytest.mark.asyncio
async def test_list_deals_error(mock_ctx):
    mock_ctx.state["client"].list_workspaces.side_effect = VaultAPIError(500, "Internal error")
    result = await list_workspaces(mock_ctx)
    assert "Erreur" in result
    assert "Internal error" in result


# ─── get_workspace ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_deal_formats_detail(mock_ctx):
    mock_ctx.state["client"].get_workspace.return_value = {
        "data": {
            "id": "d1", "emoji": "🏦", "name": "Gamma Corp",
            "status": "active", "deal_type": "equity", "sector": "FinTech",
            "target_company": "Gamma", "source_count": 2, "insight_count": 1,
            "scan_status": "completed", "created_at": "2025-01-01T00:00:00Z",
        }
    }
    result = await get_workspace(mock_ctx, workspace_id="d1")
    assert "Gamma Corp" in result
    assert "FinTech" in result
    assert "equity" in result


@pytest.mark.asyncio
async def test_get_deal_error(mock_ctx):
    mock_ctx.state["client"].get_workspace.side_effect = VaultAPIError(404, "Workspace not found")
    result = await get_workspace(mock_ctx, workspace_id="bad")
    assert "Erreur" in result
    assert "not found" in result


# ─── create_workspace ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_deal_success(mock_ctx):
    mock_ctx.state["client"].create_workspace.return_value = {
        "data": {"id": "d2", "name": "Beta Workspace", "emoji": "📁", "status": "active"}
    }
    result = await create_workspace(mock_ctx, name="Beta Workspace", sector="SaaS")
    assert "Beta Workspace" in result
    assert "d2" in result


# ─── list_sources ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_sources_empty(mock_ctx):
    mock_ctx.state["client"].list_sources.return_value = {"data": []}
    result = await list_sources(mock_ctx, workspace_id="d1")
    assert "Aucune source" in result


@pytest.mark.asyncio
async def test_list_sources_with_data(mock_ctx):
    mock_ctx.state["client"].list_sources.return_value = {
        "data": [{"id": "s1", "name": "BP.pdf", "type": "pdf", "status": "indexed"}]
    }
    result = await list_sources(mock_ctx, workspace_id="d1")
    assert "BP.pdf" in result
    assert "indexed" in result


# ─── upload_text_source ────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_text_source_returns_job(mock_ctx):
    mock_ctx.state["client"].upload_text_source.return_value = {
        "data": {"id": "src-1", "name": "Notes", "status": "pending"},
        "meta": {"job_id": "job-1"},
    }
    result = await upload_text_source(mock_ctx, workspace_id="d1", name="Notes", content="...")
    assert "Notes" in result
    assert "job-1" in result


# ─── chat ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_chat_returns_answer_with_citations(mock_ctx):
    mock_ctx.state["client"].chat.return_value = {
        "content": "L'ARR 2024 est de 8M€.",
        "citations": [{"source_name": "BP.xlsx", "page_number": 7, "quote": "ARR 8M"}],
        "session_id": "sess-1",
    }
    result = await chat(mock_ctx, workspace_id="d1", question="ARR ?")
    assert "8M€" in result
    assert "BP.xlsx" in result
    assert "p.7" in result
    assert "sess-1" in result


@pytest.mark.asyncio
async def test_chat_no_citations(mock_ctx):
    mock_ctx.state["client"].chat.return_value = {
        "content": "Je ne sais pas.",
        "citations": [],
        "session_id": "sess-2",
    }
    result = await chat(mock_ctx, workspace_id="d1", question="?")
    assert "Je ne sais pas" in result
    assert "Sources citées" not in result


# ─── list_insights ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_findings_with_data(mock_ctx):
    mock_ctx.state["client"].list_insights.return_value = {
        "data": [
            {"id": "f1", "title": "Dette élevée", "type": "red_flag",
             "severity": "critical", "status": "pending"},
        ]
    }
    result = await list_insights(mock_ctx, workspace_id="d1")
    assert "Dette élevée" in result
    assert "CRITICAL" in result
    assert "f1" in result


@pytest.mark.asyncio
async def test_list_findings_empty(mock_ctx):
    mock_ctx.state["client"].list_insights.return_value = {"data": []}
    result = await list_insights(mock_ctx, workspace_id="d1")
    assert "Aucun insight" in result


# ─── investigate_insight ───────────────────────────────────


@pytest.mark.asyncio
async def test_investigate_finding_returns_job(mock_ctx):
    mock_ctx.state["client"].investigate_insight.return_value = {
        "data": {"job_id": "job-inv-1"}
    }
    result = await investigate_insight(mock_ctx, workspace_id="d1", insight_id="f1")
    assert "job-inv-1" in result
    assert "f1" in result


# ─── list_investigations ───────────────────────────────────


@pytest.mark.asyncio
async def test_list_investigations_empty(mock_ctx):
    mock_ctx.state["client"].list_investigations.return_value = {"data": []}
    result = await list_investigations(mock_ctx, workspace_id="d1")
    assert "Aucune investigation" in result


@pytest.mark.asyncio
async def test_list_investigations_with_data(mock_ctx):
    mock_ctx.state["client"].list_investigations.return_value = {
        "data": [{"id": "inv-1", "title": "Analyse dettes", "status": "completed"}]
    }
    result = await list_investigations(mock_ctx, workspace_id="d1")
    assert "Analyse dettes" in result
    assert "completed" in result


# ─── generate_deliverable ──────────────────────────────────


@pytest.mark.asyncio
async def test_generate_deliverable_returns_job(mock_ctx):
    mock_ctx.state["client"].generate_deliverable.return_value = {
        "data": {"job_id": "job-del-1"}
    }
    result = await generate_deliverable(
        mock_ctx, workspace_id="d1", type="executive_summary", name="Synthèse",
    )
    assert "job-del-1" in result
    assert "Synthèse" in result
    assert "executive_summary" in result


@pytest.mark.asyncio
async def test_generate_deliverable_error(mock_ctx):
    mock_ctx.state["client"].generate_deliverable.side_effect = VaultAPIError(
        400, "Invalid deliverable type"
    )
    result = await generate_deliverable(
        mock_ctx, workspace_id="d1", type="unknown", name="Test",
    )
    assert "Erreur" in result
    assert "Invalid deliverable type" in result
