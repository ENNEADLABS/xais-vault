"""
Anthropic Claude provider — text generation, streaming, and tool use.
Default model: claude-sonnet-4-20250514 (best cost/quality for analysis).
"""

import logging
from typing import AsyncIterator

import anthropic

from .claude_utils import _build_tool_messages, _extract_json, _to_anthropic_tools
from .types import (
    LLMResponse,
    LLMStreamChunk,
    LLMToolResponse,
    LLMUsage,
    ToolCall,
    ToolResult,
    calculate_cost,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-20250514"


class ClaudeProvider:
    """Anthropic Claude LLM provider."""

    def __init__(self, api_key: str):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    # Seuil au-delà duquel on utilise le streaming en interne
    # pour éviter le timeout SDK "Streaming is required for >10min"
    _STREAM_THRESHOLD = 8192

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
        model = model or DEFAULT_MODEL
        messages = [{"role": "user", "content": prompt}]

        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        # Requêtes longues : streaming interne pour éviter le timeout SDK
        if max_tokens > self._STREAM_THRESHOLD:
            content, usage = await self._generate_via_stream(kwargs, model)
        else:
            response = await self._client.messages.create(**kwargs)
            content = response.content[0].text if response.content else ""
            usage = LLMUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cost_usd=calculate_cost(
                    model, response.usage.input_tokens, response.usage.output_tokens
                ),
                model=model,
            )

        if json_mode:
            content = _extract_json(content)

        return LLMResponse(content=content, usage=usage, raw=None)

    async def _generate_via_stream(
        self, kwargs: dict, model: str
    ) -> tuple[str, LLMUsage]:
        """Collecte un stream complet et retourne le contenu + usage."""
        chunks: list[str] = []
        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                chunks.append(text)
            final = await stream.get_final_message()

        content = "".join(chunks)
        usage = LLMUsage(
            input_tokens=final.usage.input_tokens,
            output_tokens=final.usage.output_tokens,
            cost_usd=calculate_cost(
                model, final.usage.input_tokens, final.usage.output_tokens
            ),
            model=model,
        )
        return content, usage

    async def stream(
        self,
        prompt: str,
        *,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> AsyncIterator[LLMStreamChunk]:
        model = model or DEFAULT_MODEL
        messages = [{"role": "user", "content": prompt}]

        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield LLMStreamChunk(content=text)

            # Final chunk with usage
            final_message = await stream.get_final_message()
            yield LLMStreamChunk(
                content="",
                is_final=True,
                usage=LLMUsage(
                    input_tokens=final_message.usage.input_tokens,
                    output_tokens=final_message.usage.output_tokens,
                    cost_usd=calculate_cost(
                        model,
                        final_message.usage.input_tokens,
                        final_message.usage.output_tokens,
                    ),
                    model=model,
                ),
            )

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
        model = model or DEFAULT_MODEL

        # Build messages — Anthropic requires strict alternation: user → assistant → user
        messages = _build_tool_messages(prompt, tool_results, previous_tool_calls)

        # Convert tools to Anthropic format
        anthropic_tools = _to_anthropic_tools(tools)

        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
            "tools": anthropic_tools,
        }
        if system:
            kwargs["system"] = system

        response = await self._client.messages.create(**kwargs)

        # Extract text and tool calls
        text_content = None
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if block.type == "text":
                text_content = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input if isinstance(block.input, dict) else {},
                    )
                )

        usage = LLMUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost_usd=calculate_cost(
                model, response.usage.input_tokens, response.usage.output_tokens
            ),
            model=model,
        )

        return LLMToolResponse(
            content=text_content,
            tool_calls=tool_calls,
            usage=usage,
            stop_reason=response.stop_reason or "",
            raw=response,
        )
