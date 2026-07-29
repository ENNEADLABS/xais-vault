"""
Google Gemini Embedding 2 provider — vector embeddings.
Model: gemini-embedding-2-preview (multimodal, 3072 dims, 8192 token window).
Released March 10, 2026 — state of the art.

Supports Matryoshka Representation Learning:
  - 3072 dims (max precision)
  - 1536 dims (balanced)
  - 768 dims (cost-optimized)

Uses the new google-genai SDK (replaces deprecated google-generativeai).
"""

import logging
import math

from google import genai
from google.genai import types

from .types import EmbeddingResponse, LLMUsage, calculate_cost

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-embedding-2-preview"


def _normalize_l2(vector: list[float]) -> list[float]:
    """Normalisation L2 — obligatoire pour dims < 3072 (doc Google).

    Google indique que les embeddings Gemini Embedding 2 en dims < 3072
    ne sont pas pré-normalisés. Sans normalisation, la distance cosine
    pgvector (`<=>`) peut donner des résultats biaisés.
    En 3072, les embeddings sont déjà normalisés par Google.
    """
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        return vector
    return [x / norm for x in vector]


DEFAULT_DIMENSIONS = 1536


class GeminiEmbeddingProvider:
    """Google Gemini Embedding 2 provider."""

    def __init__(self, api_key: str):
        self._client = genai.Client(api_key=api_key)

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
        dimensions: int = DEFAULT_DIMENSIONS,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> EmbeddingResponse:
        model = model or DEFAULT_MODEL

        result = self._client.models.embed_content(
            model=model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=dimensions,
            ),
        )

        # Normalisation L2 obligatoire pour dims < 3072 (Google doc)
        embeddings = [_normalize_l2(list(e.values)) for e in result.embeddings]

        # Estimate tokens (~4 chars per token)
        total_chars = sum(len(t) for t in texts)
        estimated_tokens = total_chars // 4

        usage = LLMUsage(
            input_tokens=estimated_tokens,
            output_tokens=0,
            cost_usd=calculate_cost(model, estimated_tokens, 0),
            model=model,
        )

        return EmbeddingResponse(
            embeddings=embeddings,
            usage=usage,
            dimensions=dimensions,
        )

    async def embed_query(
        self,
        query: str,
        *,
        model: str | None = None,
        dimensions: int = DEFAULT_DIMENSIONS,
    ) -> list[float]:
        """Embed a single search query (uses RETRIEVAL_QUERY task type)."""
        response = await self.embed(
            [query],
            model=model,
            dimensions=dimensions,
            task_type="RETRIEVAL_QUERY",
        )
        return response.embeddings[0]
