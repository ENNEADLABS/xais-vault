"""
Tests for apps/worker/app/services/indexing.py (index_source pipeline).

All helpers (download, extract, chunk, embed, summarize, store, scan, webhook)
are mocked — only the orchestration logic is tested here.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.worker.app.services.indexing import index_source

SOURCE_ID = str(uuid.uuid4())
DEAL_ID = str(uuid.uuid4())
ORG_ID = str(uuid.uuid4())

BASE_SOURCE = {
    "id": SOURCE_ID,
    "workspace_id": DEAL_ID,
    "organization_id": ORG_ID,
    "type": "pdf",
    "file_path": f"{ORG_ID}/{DEAL_ID}/{SOURCE_ID}/file.pdf",
    "status": "pending",
    "metadata": {},
    "name": "test.pdf",
    "extracted_text": None,
}

BASE_PAYLOAD = {
    "source_id": SOURCE_ID,
    "organization_id": ORG_ID,
}


# ─── Helpers ──────────────────────────────────────────────────


def _make_db(source=None):
    """Supabase mock that returns `source` on SELECT and no-ops on UPDATE."""
    db = MagicMock()
    update_calls = []

    def capture_update(payload):
        update_calls.append(payload)
        m = MagicMock()
        m.eq.return_value.execute.return_value = MagicMock(data=[])
        return m

    chain = MagicMock()
    chain.update.side_effect = capture_update
    chain.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[source] if source else []
    )
    db.table.return_value = chain
    db._update_calls = update_calls
    return db


def _make_extraction():
    m = MagicMock()
    m.text = "Full extracted document text. " * 200
    m.word_count = 600
    m.page_count = 5
    m.metadata = {"extractor": "pdfminer"}
    return m


def _make_chunk():
    from apps.worker.app.services.chunking import Chunk
    return Chunk(content="chunk content", chunk_index=0, token_count=500)


# ─── Full pipeline ────────────────────────────────────────────


@pytest.mark.asyncio
@patch("apps.worker.app.services.indexing._emit_webhook", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.maybe_trigger_scan", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.store_chunks", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.generate_summary", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.embed_chunks", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.chunk_document")
@patch("apps.worker.app.services.indexing.extract", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.download_file", new_callable=AsyncMock)
async def test_happy_path_pdf_returns_stats(
    mock_dl, mock_extract, mock_chunk, mock_embed, mock_summary,
    mock_store, mock_scan, mock_webhook,
):
    """Full PDF pipeline returns stats dict on success."""
    mock_dl.return_value = "/tmp/file.pdf"
    mock_extract.return_value = _make_extraction()
    mock_chunk.return_value = [_make_chunk()]
    mock_embed.return_value = ([[0.1] * 1536], 0.002)
    mock_summary.return_value = ({"summary": "Good doc", "topics": [], "suggested_questions": []}, 0.005)

    db = _make_db(BASE_SOURCE)
    result = await index_source(db, BASE_PAYLOAD)

    assert result["source_id"] == SOURCE_ID
    assert result["chunks"] == 1
    assert "total_cost_usd" in result


@pytest.mark.asyncio
@patch("apps.worker.app.services.indexing._emit_webhook", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.maybe_trigger_scan", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.store_chunks", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.generate_summary", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.embed_chunks", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.chunk_document")
async def test_text_source_skips_extraction(
    mock_chunk, mock_embed, mock_summary, mock_store, mock_scan, mock_webhook,
):
    """skip_extraction=True with extracted_text bypasses download+extract."""
    text_source = {**BASE_SOURCE, "file_path": None, "extracted_text": "Pasted text content " * 100}
    mock_chunk.return_value = [_make_chunk()]
    mock_embed.return_value = ([[0.1] * 1536], 0.001)
    mock_summary.return_value = ({"summary": "ok", "topics": [], "suggested_questions": []}, 0.002)

    payload = {**BASE_PAYLOAD, "skip_extraction": True}
    db = _make_db(text_source)

    result = await index_source(db, payload)

    assert result["source_id"] == SOURCE_ID


@pytest.mark.asyncio
@patch("apps.worker.app.services.indexing._emit_webhook", new_callable=AsyncMock)
async def test_no_file_path_no_text_raises_value_error(mock_webhook):
    """Source with neither file_path nor extracted_text raises ValueError."""
    broken_source = {**BASE_SOURCE, "file_path": None, "extracted_text": None}
    db = _make_db(broken_source)

    with pytest.raises(ValueError, match="no file_path"):
        await index_source(db, BASE_PAYLOAD)


@pytest.mark.asyncio
@patch("apps.worker.app.services.indexing._emit_webhook", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.extract", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.download_file", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.chunk_document")
async def test_empty_chunks_raises_value_error(mock_chunk, mock_dl, mock_extract, mock_webhook):
    """Empty chunk list (e.g. blank PDF) raises ValueError."""
    mock_dl.return_value = "/tmp/file.pdf"
    mock_extract.return_value = _make_extraction()
    mock_chunk.return_value = []  # ← blank document

    db = _make_db(BASE_SOURCE)

    with pytest.raises(ValueError, match="No content"):
        await index_source(db, BASE_PAYLOAD)


@pytest.mark.asyncio
@patch("apps.worker.app.services.indexing._emit_webhook", new_callable=AsyncMock)
async def test_source_not_found_raises_value_error(mock_webhook):
    """Missing source record raises ValueError."""
    db = _make_db(source=None)

    with pytest.raises(ValueError, match="not found"):
        await index_source(db, BASE_PAYLOAD)


# ─── Status transitions ───────────────────────────────────────


@pytest.mark.asyncio
@patch("apps.worker.app.services.indexing._emit_webhook", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.maybe_trigger_scan", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.store_chunks", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.generate_summary", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.embed_chunks", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.chunk_document")
@patch("apps.worker.app.services.indexing.extract", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.download_file", new_callable=AsyncMock)
async def test_status_set_to_processing_at_start(
    mock_dl, mock_extract, mock_chunk, mock_embed, mock_summary,
    mock_store, mock_scan, mock_webhook,
):
    """First DB update sets status to 'processing'."""
    mock_dl.return_value = "/tmp/file.pdf"
    mock_extract.return_value = _make_extraction()
    mock_chunk.return_value = [_make_chunk()]
    mock_embed.return_value = ([[0.1] * 1536], 0.001)
    mock_summary.return_value = ({"summary": "ok", "topics": [], "suggested_questions": []}, 0.001)

    db = _make_db(BASE_SOURCE)
    await index_source(db, BASE_PAYLOAD)

    first_update = db._update_calls[0]
    assert first_update["status"] == "processing"


@pytest.mark.asyncio
@patch("apps.worker.app.services.indexing._emit_webhook", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.maybe_trigger_scan", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.store_chunks", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.generate_summary", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.embed_chunks", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.chunk_document")
@patch("apps.worker.app.services.indexing.extract", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.download_file", new_callable=AsyncMock)
async def test_status_set_to_ready_on_success(
    mock_dl, mock_extract, mock_chunk, mock_embed, mock_summary,
    mock_store, mock_scan, mock_webhook,
):
    """On successful completion, last status update is 'ready'."""
    mock_dl.return_value = "/tmp/file.pdf"
    mock_extract.return_value = _make_extraction()
    mock_chunk.return_value = [_make_chunk()]
    mock_embed.return_value = ([[0.1] * 1536], 0.001)
    mock_summary.return_value = ({"summary": "ok", "topics": [], "suggested_questions": []}, 0.001)

    db = _make_db(BASE_SOURCE)
    await index_source(db, BASE_PAYLOAD)

    last_update = db._update_calls[-1]
    assert last_update["status"] == "ready"


@pytest.mark.asyncio
@patch("apps.worker.app.services.indexing._emit_webhook", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.chunk_document")
@patch("apps.worker.app.services.indexing.extract", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.download_file", new_callable=AsyncMock)
async def test_status_set_to_failed_on_exception(mock_dl, mock_extract, mock_chunk, mock_webhook):
    """When an exception occurs, status is updated to 'failed'."""
    mock_dl.return_value = "/tmp/file.pdf"
    mock_extract.return_value = _make_extraction()
    mock_chunk.side_effect = RuntimeError("chunk exploded")

    db = _make_db(BASE_SOURCE)

    with pytest.raises(RuntimeError):
        await index_source(db, BASE_PAYLOAD)

    failed_calls = [c for c in db._update_calls if c.get("status") == "failed"]
    assert len(failed_calls) == 1


# ─── Temp file cleanup ────────────────────────────────────────


@pytest.mark.asyncio
@patch("apps.worker.app.services.indexing.os.unlink")
@patch("apps.worker.app.services.indexing.os.path.exists", return_value=True)
@patch("apps.worker.app.services.indexing._emit_webhook", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.maybe_trigger_scan", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.store_chunks", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.generate_summary", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.embed_chunks", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.chunk_document")
@patch("apps.worker.app.services.indexing.extract", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.download_file", new_callable=AsyncMock)
async def test_temp_file_cleaned_up_after_processing(
    mock_dl, mock_extract, mock_chunk, mock_embed, mock_summary,
    mock_store, mock_scan, mock_webhook, mock_exists, mock_unlink,
):
    """Temp file is deleted after successful processing."""
    mock_dl.return_value = "/tmp/test_cleanup.pdf"
    mock_extract.return_value = _make_extraction()
    mock_chunk.return_value = [_make_chunk()]
    mock_embed.return_value = ([[0.1] * 1536], 0.001)
    mock_summary.return_value = ({"summary": "ok", "topics": [], "suggested_questions": []}, 0.001)

    db = _make_db(BASE_SOURCE)
    await index_source(db, BASE_PAYLOAD)

    mock_unlink.assert_called_once_with("/tmp/test_cleanup.pdf")


@pytest.mark.asyncio
@patch("apps.worker.app.services.indexing.os.unlink")
@patch("apps.worker.app.services.indexing.os.path.exists", return_value=True)
@patch("apps.worker.app.services.indexing._emit_webhook", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.chunk_document")
@patch("apps.worker.app.services.indexing.extract", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.download_file", new_callable=AsyncMock)
async def test_temp_file_cleaned_up_on_failure(
    mock_dl, mock_extract, mock_chunk, mock_webhook, mock_exists, mock_unlink,
):
    """Temp file is deleted even when processing fails."""
    mock_dl.return_value = "/tmp/test_failure.pdf"
    mock_extract.return_value = _make_extraction()
    mock_chunk.side_effect = RuntimeError("processing failed")

    db = _make_db(BASE_SOURCE)

    with pytest.raises(RuntimeError):
        await index_source(db, BASE_PAYLOAD)

    mock_unlink.assert_called_once_with("/tmp/test_failure.pdf")


# ─── Side effects ────────────────────────────────────────────


@pytest.mark.asyncio
@patch("apps.worker.app.services.indexing._emit_webhook", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.maybe_trigger_scan", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.store_chunks", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.generate_summary", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.embed_chunks", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.chunk_document")
@patch("apps.worker.app.services.indexing.extract", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.download_file", new_callable=AsyncMock)
async def test_triggers_auto_scan_on_success(
    mock_dl, mock_extract, mock_chunk, mock_embed, mock_summary,
    mock_store, mock_scan, mock_webhook,
):
    """maybe_trigger_scan is called once on successful indexing."""
    mock_dl.return_value = "/tmp/file.pdf"
    mock_extract.return_value = _make_extraction()
    mock_chunk.return_value = [_make_chunk()]
    mock_embed.return_value = ([[0.1] * 1536], 0.001)
    mock_summary.return_value = ({"summary": "ok", "topics": [], "suggested_questions": []}, 0.001)

    db = _make_db(BASE_SOURCE)
    await index_source(db, BASE_PAYLOAD)

    mock_scan.assert_called_once()


@pytest.mark.asyncio
@patch("apps.worker.app.services.indexing._emit_webhook", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.maybe_trigger_scan", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.store_chunks", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.generate_summary", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.embed_chunks", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.chunk_document")
@patch("apps.worker.app.services.indexing.extract", new_callable=AsyncMock)
@patch("apps.worker.app.services.indexing.download_file", new_callable=AsyncMock)
async def test_emits_source_ready_webhook(
    mock_dl, mock_extract, mock_chunk, mock_embed, mock_summary,
    mock_store, mock_scan, mock_webhook,
):
    """source.ready webhook is emitted after successful indexing."""
    mock_dl.return_value = "/tmp/file.pdf"
    mock_extract.return_value = _make_extraction()
    mock_chunk.return_value = [_make_chunk()]
    mock_embed.return_value = ([[0.1] * 1536], 0.001)
    mock_summary.return_value = ({"summary": "ok", "topics": [], "suggested_questions": []}, 0.001)

    db = _make_db(BASE_SOURCE)
    await index_source(db, BASE_PAYLOAD)

    webhook_calls = mock_webhook.call_args_list
    ready_calls = [c for c in webhook_calls if c.kwargs.get("event_type") == "source.ready"]
    assert len(ready_calls) == 1
