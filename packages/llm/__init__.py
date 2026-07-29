"""
LLM Abstraction Layer — packages/llm/

Protocol-based abstraction for multi-provider LLM support.
Claude (Anthropic) for text analysis/generation.
Gemini Embedding 2 for vector embeddings.

Usage:
    from packages.llm.factory import get_llm, get_embedder

    llm = get_llm()  # Returns Claude provider
    response = await llm.generate("Analyze this document", system="You are a DD analyst")

    embedder = get_embedder()  # Returns Gemini Embedding 2 provider
    vectors = await embedder.embed(["chunk 1", "chunk 2"])
"""

from .base import EmbeddingProvider, LLMProvider
from .factory import get_embedder, get_llm
from .types import EmbeddingResponse, LLMResponse, LLMStreamChunk, LLMUsage

__all__ = [
    "LLMProvider",
    "EmbeddingProvider",
    "LLMResponse",
    "LLMUsage",
    "LLMStreamChunk",
    "EmbeddingResponse",
    "get_llm",
    "get_embedder",
]
