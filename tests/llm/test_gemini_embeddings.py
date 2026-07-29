"""
Tests unitaires pour GeminiEmbeddingProvider.

L'API Google Gemini est mockée — aucun appel réseau.
"""

import math
from unittest.mock import MagicMock, patch

import pytest

from packages.llm.gemini_embeddings import GeminiEmbeddingProvider, _normalize_l2

# ─── Helpers ─────────────────────────────────────────────────────


def _make_embedding(values: list[float]) -> MagicMock:
    e = MagicMock()
    e.values = values
    return e


def _make_embed_result(embeddings_list: list[list[float]]) -> MagicMock:
    result = MagicMock()
    result.embeddings = [_make_embedding(v) for v in embeddings_list]
    return result


@pytest.fixture
def provider():
    """GeminiEmbeddingProvider avec client Google mocké."""
    with patch("packages.llm.gemini_embeddings.genai.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        p = GeminiEmbeddingProvider(api_key="test-key")
        p._client = mock_client
        yield p


# ─── _normalize_l2 ───────────────────────────────────────────────


class TestNormalizeL2:
    def test_norme_est_un(self):
        vec = [3.0, 4.0]  # norme = 5.0
        result = _normalize_l2(vec)
        norm = math.sqrt(sum(x * x for x in result))
        assert abs(norm - 1.0) < 1e-9

    def test_direction_preservee(self):
        vec = [3.0, 4.0]
        result = _normalize_l2(vec)
        assert abs(result[0] - 0.6) < 1e-9
        assert abs(result[1] - 0.8) < 1e-9

    def test_vecteur_nul_reste_nul(self):
        vec = [0.0, 0.0, 0.0]
        result = _normalize_l2(vec)
        assert result == [0.0, 0.0, 0.0]

    def test_vecteur_deja_normalise_inchange(self):
        vec = [0.6, 0.8]  # norme déjà = 1.0
        result = _normalize_l2(vec)
        assert abs(result[0] - 0.6) < 1e-9
        assert abs(result[1] - 0.8) < 1e-9


# ─── embed ────────────────────────────────────────────────────────


class TestEmbed:
    @pytest.mark.asyncio
    async def test_returns_embeddings(self, provider):
        vecs = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        provider._client.models.embed_content.return_value = _make_embed_result(vecs)

        result = await provider.embed(["texte A", "texte B"])

        assert len(result.embeddings) == 2
        # Les vecteurs retournés doivent être normalisés L2 (norme ≈ 1.0)
        for emb in result.embeddings:
            norm = math.sqrt(sum(x * x for x in emb))
            assert abs(norm - 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_dimensions_forwarded(self, provider):
        provider._client.models.embed_content.return_value = _make_embed_result([[0.1]])

        result = await provider.embed(["test"], dimensions=768)

        assert result.dimensions == 768
        call_kwargs = provider._client.models.embed_content.call_args.kwargs
        assert call_kwargs["config"].output_dimensionality == 768

    @pytest.mark.asyncio
    async def test_task_type_forwarded(self, provider):
        provider._client.models.embed_content.return_value = _make_embed_result([[0.1]])

        await provider.embed(["test"], task_type="RETRIEVAL_QUERY")

        call_kwargs = provider._client.models.embed_content.call_args.kwargs
        assert call_kwargs["config"].task_type == "RETRIEVAL_QUERY"

    @pytest.mark.asyncio
    async def test_usage_estimated_from_chars(self, provider):
        text = "a" * 400  # 400 chars → ~100 tokens
        provider._client.models.embed_content.return_value = _make_embed_result([[0.1]])

        result = await provider.embed([text])

        assert result.usage.input_tokens == 100
        assert result.usage.output_tokens == 0

    @pytest.mark.asyncio
    async def test_default_model_used(self, provider):
        provider._client.models.embed_content.return_value = _make_embed_result([[0.1]])

        await provider.embed(["test"])

        call_kwargs = provider._client.models.embed_content.call_args.kwargs
        assert call_kwargs["model"] == "gemini-embedding-2-preview"

    @pytest.mark.asyncio
    async def test_custom_model_forwarded(self, provider):
        provider._client.models.embed_content.return_value = _make_embed_result([[0.1]])

        await provider.embed(["test"], model="custom-model")

        call_kwargs = provider._client.models.embed_content.call_args.kwargs
        assert call_kwargs["model"] == "custom-model"


# ─── embed_query ─────────────────────────────────────────────────


class TestEmbedQuery:
    @pytest.mark.asyncio
    async def test_returns_first_embedding(self, provider):
        vec = [0.1, 0.2, 0.3, 0.4]
        provider._client.models.embed_content.return_value = _make_embed_result([vec])

        result = await provider.embed_query("Ma recherche")

        # Le vecteur retourné doit être normalisé L2
        norm = math.sqrt(sum(x * x for x in result))
        assert abs(norm - 1.0) < 1e-6
        # La direction doit être préservée (ratio constant entre les composantes)
        expected = _normalize_l2(vec)
        for a, b in zip(result, expected):
            assert abs(a - b) < 1e-6

    @pytest.mark.asyncio
    async def test_uses_retrieval_query_task_type(self, provider):
        provider._client.models.embed_content.return_value = _make_embed_result([[0.1]])

        await provider.embed_query("query")

        call_kwargs = provider._client.models.embed_content.call_args.kwargs
        assert call_kwargs["config"].task_type == "RETRIEVAL_QUERY"

    @pytest.mark.asyncio
    async def test_dimensions_forwarded(self, provider):
        provider._client.models.embed_content.return_value = _make_embed_result([[0.1]])

        await provider.embed_query("query", dimensions=768)

        call_kwargs = provider._client.models.embed_content.call_args.kwargs
        assert call_kwargs["config"].output_dimensionality == 768
