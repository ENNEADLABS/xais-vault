"""
Protocol definitions for LLM and Embedding providers.
Any provider must implement these interfaces.
"""

from typing import AsyncIterator, Protocol, runtime_checkable

from .types import (
    EmbeddingResponse,
    LLMResponse,
    LLMStreamChunk,
    LLMToolResponse,
    ToolCall,
    ToolResult,
)


@runtime_checkable
class LLMProvider(Protocol):
    """Interface for text generation LLM providers (Claude, etc.)."""

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate a single text response."""
        ...

    async def stream(
        self,
        prompt: str,
        *,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Stream a text response chunk by chunk."""
        ...

    async def generate_with_tools(
        self,
        prompt: str,
        tools: list[dict],
        *,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        tool_results: list[ToolResult] | None = None,
        previous_tool_calls: list[ToolCall] | None = None,
    ) -> LLMToolResponse:
        """Generate a response that may include tool calls."""
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Interface for embedding providers (Gemini Embedding 2, etc.)."""

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
        dimensions: int = 1536,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> EmbeddingResponse:
        """Generate embeddings for a list of texts."""
        ...

    async def embed_query(
        self,
        query: str,
        *,
        model: str | None = None,
        dimensions: int = 1536,
    ) -> list[float]:
        """Generate a single embedding for a search query.
        Convenience method — uses task_type=RETRIEVAL_QUERY.
        """
        ...
