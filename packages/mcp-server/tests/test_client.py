"""Tests unitaires du VaultClient avec respx (mock httpx)."""

import pytest
import respx
from httpx import Response
from src.client import VaultAPIError, VaultClient


@pytest.fixture
async def client():
    async with VaultClient(
        base_url="https://test.api",
        api_key="xv_test_abc123",  # gitleaks:allow
    ) as c:
        yield c


@respx.mock
@pytest.mark.asyncio
async def test_list_deals_success(client):
    respx.get("https://test.api/api/v2/workspaces").mock(
        return_value=Response(200, json={
            "data": [{"id": "d1", "name": "Workspace Alpha", "emoji": "📁", "status": "active"}],
            "total": 1, "page": 1, "per_page": 20, "pages": 1,
        })
    )
    result = await client.list_workspaces()
    assert len(result["data"]) == 1
    assert result["data"][0]["name"] == "Workspace Alpha"


@respx.mock
@pytest.mark.asyncio
async def test_list_deals_with_status_filter(client):
    route = respx.get("https://test.api/api/v2/workspaces").mock(
        return_value=Response(200, json={"data": [], "total": 0, "page": 1, "per_page": 20, "pages": 0})
    )
    await client.list_workspaces(status="archived")
    assert route.called
    assert "status=archived" in str(route.calls[0].request.url)


@respx.mock
@pytest.mark.asyncio
async def test_api_error_raises(client):
    respx.get("https://test.api/api/v2/workspaces/bad-id").mock(
        return_value=Response(404, json={
            "error": {"code": 404, "message": "Workspace not found"}
        })
    )
    with pytest.raises(VaultAPIError) as exc_info:
        await client.get_workspace("bad-id")
    assert exc_info.value.status_code == 404
    assert "Workspace not found" in exc_info.value.message


@respx.mock
@pytest.mark.asyncio
async def test_create_deal_sends_name(client):
    respx.post("https://test.api/api/v2/workspaces").mock(
        return_value=Response(201, json={"data": {"id": "d2", "name": "Beta Workspace"}})
    )
    result = await client.create_workspace("Beta Workspace", sector="SaaS")
    assert result["data"]["name"] == "Beta Workspace"


@respx.mock
@pytest.mark.asyncio
async def test_chat_parses_sse(client):
    sse_body = (
        "event: session\ndata: {\"id\": \"sess-1\"}\n\n"
        "event: content\ndata: {\"text\": \"L'ARR est de \"}\n\n"
        "event: content\ndata: {\"text\": \"8M€.\"}\n\n"
        "event: citations\ndata: {\"citations\": [{\"source_name\": \"Memo\", \"quote\": \"ARR 8M\"}]}\n\n"
        "event: usage\ndata: {\"input_tokens\": 500, \"output_tokens\": 100}\n\n"
        "event: done\ndata: {}\n\n"
    )
    respx.post("https://test.api/api/v2/workspaces/d1/chat").mock(
        return_value=Response(200, text=sse_body)
    )
    result = await client.chat("d1", "Quel est l'ARR ?")
    assert result["content"] == "L'ARR est de 8M€."
    assert result["session_id"] == "sess-1"
    assert len(result["citations"]) == 1
    assert result["usage"]["input_tokens"] == 500


@respx.mock
@pytest.mark.asyncio
async def test_chat_with_session_id(client):
    route = respx.post("https://test.api/api/v2/workspaces/d1/chat").mock(
        return_value=Response(200, text="event: content\ndata: {\"text\": \"Réponse\"}\n\n")
    )
    await client.chat("d1", "Question", session_id="sess-existing")
    import json
    body = json.loads(route.calls[0].request.content)
    assert body["session_id"] == "sess-existing"


@respx.mock
@pytest.mark.asyncio
async def test_upload_text_source(client):
    respx.post("https://test.api/api/v2/workspaces/d1/sources/text").mock(
        return_value=Response(202, json={
            "data": {"id": "src-1", "name": "Notes", "status": "pending"},
            "meta": {"job_id": "job-1"},
        })
    )
    result = await client.upload_text_source("d1", "Notes", "Contenu...")
    assert result["meta"]["job_id"] == "job-1"


@respx.mock
@pytest.mark.asyncio
async def test_investigate_insight(client):
    respx.patch("https://test.api/api/v2/workspaces/d1/insights/f1").mock(
        return_value=Response(202, json={"data": {"job_id": "job-2"}})
    )
    result = await client.investigate_insight("d1", "f1")
    assert result["data"]["job_id"] == "job-2"


@respx.mock
@pytest.mark.asyncio
async def test_generate_deliverable(client):
    respx.post("https://test.api/api/v2/workspaces/d1/deliverables").mock(
        return_value=Response(202, json={"data": {"job_id": "job-3"}})
    )
    result = await client.generate_deliverable("d1", "executive_summary", "Synthèse")
    assert result["data"]["job_id"] == "job-3"


@respx.mock
@pytest.mark.asyncio
async def test_auth_header_is_sent(client):
    route = respx.get("https://test.api/api/v2/workspaces").mock(
        return_value=Response(200, json={"data": [], "total": 0, "page": 1, "per_page": 20, "pages": 0})
    )
    await client.list_workspaces()
    assert route.calls[0].request.headers["X-API-Key"] == "xv_test_abc123"


@respx.mock
@pytest.mark.asyncio
async def test_204_returns_empty_dict(client):
    respx.delete("https://test.api/api/v2/workspaces/d1").mock(
        return_value=Response(204)
    )
    result = await client._request("DELETE", "/workspaces/d1")
    assert result == {}
