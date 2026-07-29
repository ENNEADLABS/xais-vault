"""
Claude utility functions — tool format conversion, JSON extraction, message building.
Extracted from claude.py to keep ClaudeProvider under 200 lines.
"""

import json
import logging

from .types import ToolCall, ToolResult

logger = logging.getLogger(__name__)


def _build_tool_messages(
    prompt: str,
    tool_results: list[ToolResult] | None,
    previous_tool_calls: list[ToolCall] | None,
) -> list[dict]:
    """Build Anthropic message sequence for tool calling.

    Anthropic requires strict user/assistant/user alternation.
    When tool_results is provided, previous_tool_calls must also be given
    to reconstruct the assistant turn.
    """
    messages: list[dict] = [{"role": "user", "content": prompt}]

    if tool_results:
        if not previous_tool_calls:
            raise ValueError(
                "previous_tool_calls est requis quand tool_results est fourni"
            )
        # Assistant turn: the tool_use blocks from the previous response
        messages.append(
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    }
                    for tc in previous_tool_calls
                ],
            }
        )
        # User turn: tool results
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tr.tool_call_id,
                        "content": tr.content,
                        "is_error": tr.is_error,
                    }
                    for tr in tool_results
                ],
            }
        )

    return messages


def _to_anthropic_tools(tools: list[dict]) -> list[dict]:
    """Convert generic tool definitions to Anthropic format.

    Input format (generic):
    {
        "name": "search_web",
        "description": "Search the web for information",
        "parameters": {
            "type": "object",
            "properties": { "query": {"type": "string"} },
            "required": ["query"]
        }
    }
    """
    return [
        {
            "name": t["name"],
            "description": t.get("description", ""),
            "input_schema": t.get("parameters", {"type": "object", "properties": {}}),
        }
        for t in tools
    ]


def _extract_json(text: str) -> str:
    """Extract valid JSON from a response that might contain markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON response, returning raw content")
        return text

    return cleaned
