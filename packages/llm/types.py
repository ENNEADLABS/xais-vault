"""
Shared types for the LLM abstraction layer.
Used by all providers (Claude, Gemini, etc.)
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class LLMUsage:
    """Token usage and cost tracking for a single LLM call."""

    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    model: str = ""


@dataclass
class LLMResponse:
    """Standard response from any LLM provider."""

    content: str
    usage: LLMUsage
    raw: Any = None  # Provider-specific raw response (for debugging)


@dataclass
class LLMStreamChunk:
    """Single chunk from a streaming LLM response."""

    content: str = ""
    is_final: bool = False
    usage: LLMUsage | None = None  # Only present on final chunk


@dataclass
class ToolCall:
    """A tool call requested by the LLM."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    """Result of executing a tool call."""

    tool_call_id: str
    content: str
    is_error: bool = False


@dataclass
class LLMToolResponse:
    """Response from an LLM that may include tool calls."""

    content: str | None  # Text response (may be None if tool call only)
    tool_calls: list[ToolCall]
    usage: LLMUsage
    stop_reason: str = ""  # "end_turn" | "tool_use" | "max_tokens"
    raw: Any = None


@dataclass
class EmbeddingResponse:
    """Response from an embedding provider."""

    embeddings: list[list[float]]
    usage: LLMUsage
    dimensions: int = 1536


# ─── Pricing tables (per 1M tokens, March 2026) ─────────────────

CLAUDE_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
}

GEMINI_PRICING: dict[str, dict[str, float]] = {
    "gemini-embedding-2-preview": {"input": 0.006, "output": 0.0},  # Embedding only
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate USD cost for a given model and token count."""
    all_pricing = {**CLAUDE_PRICING, **GEMINI_PRICING}
    pricing = all_pricing.get(model)
    if not pricing:
        return 0.0
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)
