"""Tests pour apps/worker/app/services/entity_extraction.py."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.worker.app.services.entity_extraction import (
    _deduplicate_entities,
    extract_entities_from_chunks,
)
from apps.worker.app.services.entity_extraction_helpers import (
    normalize_entity_name,
)
from packages.core.entity_schemas import ExtractedEntity

# ─── normalize_entity_name ──────────────────────────────────────────


class TestNormalizeName:
    def test_lowercase(self):
        assert normalize_entity_name("ACME SAS") == "acme sas"

    def test_strip_accents(self):
        assert normalize_entity_name("Société Générale") == "societe generale"

    def test_strip_whitespace(self):
        assert normalize_entity_name("  Acme  ") == "acme"

    def test_empty_string(self):
        assert normalize_entity_name("") == ""


# ─── _deduplicate_entities ────────────────────────────────────


class TestDeduplicateEntities:
    def test_remove_duplicates(self):
        """Entités avec le même nom normalisé → une seule."""
        entities = [
            ExtractedEntity(name="Acme SAS", type="company"),
            ExtractedEntity(name="ACME SAS", type="company"),
            ExtractedEntity(name="acme sas", type="company"),
        ]
        result = _deduplicate_entities(entities)
        assert len(result) == 1
        assert result[0].name == "Acme SAS"  # Garde la première

    def test_keep_different_entities(self):
        """Entités différentes sont conservées."""
        entities = [
            ExtractedEntity(name="Acme SAS", type="company"),
            ExtractedEntity(name="Beta Corp", type="company"),
        ]
        result = _deduplicate_entities(entities)
        assert len(result) == 2

    def test_empty_list(self):
        assert _deduplicate_entities([]) == []

    def test_accented_dedup(self):
        """Societe et Société sont dédupliqués."""
        entities = [
            ExtractedEntity(name="Société Alpha", type="company"),
            ExtractedEntity(name="Societe Alpha", type="company"),
        ]
        result = _deduplicate_entities(entities)
        assert len(result) == 1


# ─── extract_entities_from_chunks ─────────────────────────────


def _mock_llm_response(entities: list[dict], relations: list[dict] | None = None):
    """Crée un mock de réponse LLM avec le JSON d'extraction."""
    content = json.dumps({
        "entities": entities,
        "relations": relations or [],
    })
    response = MagicMock()
    response.content = content
    response.usage = MagicMock()
    response.usage.cost_usd = 0.0003
    return response


def _mock_embedding_response(count: int):
    """Crée un mock de réponse embedding."""
    response = MagicMock()
    response.embeddings = [[0.1] * 1536 for _ in range(count)]
    response.usage = MagicMock()
    response.usage.cost_usd = 0.00001
    return response


def _mock_supabase():
    """Crée un mock Supabase avec les tables nécessaires."""
    db = MagicMock()

    # entities.select → retourne liste vide (pas d'entités existantes)
    entities_chain = MagicMock()
    for m in ("select", "eq", "execute"):
        getattr(entities_chain, m, MagicMock()).return_value = entities_chain
    entities_chain.execute.return_value = MagicMock(data=[])

    # entities.insert → retourne les entités avec ID
    insert_chain = MagicMock()
    insert_chain.execute.return_value = MagicMock(
        data=[{"id": f"ent-{i}", "name": f"entity-{i}"} for i in range(5)]
    )

    def table_router(name: str):
        mock = MagicMock()
        if name == "entities":
            mock.select.return_value = entities_chain
            mock.insert.return_value = insert_chain
        elif name in ("entity_relations", "chunk_entities", "usage_logs"):
            chain = MagicMock()
            for m in ("insert", "upsert", "execute"):
                getattr(chain, m, MagicMock()).return_value = chain
            chain.execute.return_value = MagicMock(data=[])
            mock.insert.return_value = chain
            mock.upsert.return_value = chain
        return mock

    db.table.side_effect = table_router
    return db


@pytest.mark.asyncio
class TestExtractEntitiesFromChunks:
    async def test_empty_chunks_returns_zero(self):
        """Pas de chunks → stats à zéro."""
        db = MagicMock()
        result = await extract_entities_from_chunks(
            db, chunks=[], workspace_id="d1", organization_id="o1",
        )
        assert result["entities_count"] == 0
        assert result["relations_count"] == 0

    async def test_extraction_with_entities(self):
        """Extraction avec des entités retournées par le LLM."""
        llm_response = _mock_llm_response([
            {"name": "Acme SAS", "type": "company", "description": "Société cible"},
            {"name": "EBITDA 2024", "type": "metric", "description": "12M€"},
        ])

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = llm_response

        mock_embedder = AsyncMock()
        mock_embedder.embed.return_value = _mock_embedding_response(2)

        db = _mock_supabase()

        chunks = [
            {"id": "c1", "content": "Acme SAS a un EBITDA de 12M€ en 2024.", "chunk_index": 0},
        ]

        with (
            patch("apps.worker.app.services.entity_extraction.get_llm", return_value=mock_llm),
            patch("apps.worker.app.services.entity_extraction.get_embedder", return_value=mock_embedder),
        ):
            result = await extract_entities_from_chunks(
                db, chunks=chunks, workspace_id="d1", organization_id="o1",
            )

        assert result["entities_count"] > 0
        assert result["cost_usd"] > 0

    async def test_extraction_handles_llm_error(self):
        """Si le LLM retourne du JSON invalide, on skip le batch sans crash."""
        bad_response = MagicMock()
        bad_response.content = "not json at all"
        bad_response.usage = MagicMock()
        bad_response.usage.cost_usd = 0.0003

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = bad_response

        db = _mock_supabase()

        chunks = [{"id": "c1", "content": "test content", "chunk_index": 0}]

        with patch("apps.worker.app.services.entity_extraction.get_llm", return_value=mock_llm):
            result = await extract_entities_from_chunks(
                db, chunks=chunks, workspace_id="d1", organization_id="o1",
            )

        # Pas de crash, juste 0 entités
        assert result["entities_count"] == 0

    async def test_cost_logged_to_usage_logs(self):
        """Le coût d'extraction est enregistré dans usage_logs."""
        llm_response = _mock_llm_response([
            {"name": "Test Corp", "type": "company", "description": ""},
        ])

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = llm_response

        mock_embedder = AsyncMock()
        mock_embedder.embed.return_value = _mock_embedding_response(1)

        db = _mock_supabase()
        chunks = [{"id": "c1", "content": "Test Corp document.", "chunk_index": 0}]

        with (
            patch("apps.worker.app.services.entity_extraction.get_llm", return_value=mock_llm),
            patch("apps.worker.app.services.entity_extraction.get_embedder", return_value=mock_embedder),
        ):
            await extract_entities_from_chunks(
                db, chunks=chunks, workspace_id="d1", organization_id="o1",
            )

        # Vérifier que usage_logs a été appelé
        db.table.assert_any_call("usage_logs")
