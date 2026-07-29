"""
Chat streaming — Claude response streaming, citation parsing.

Extracted from chat_engine.py for the 200-line-per-file rule.
"""

import re
from dataclasses import dataclass
from typing import AsyncIterator

from packages.llm.factory import get_llm
from packages.llm.types import LLMUsage

from .chat_rag import ChatContext


@dataclass
class StreamEvent:
    """A single SSE event to send to the client."""
    event: str
    data: str


@dataclass
class ChatResult:
    """Full result after streaming is complete."""
    content: str
    citations: list[dict]
    usage: LLMUsage


async def stream_response(
    context: ChatContext,
) -> AsyncIterator[tuple[str, LLMUsage | None]]:
    """Stream Claude's response chunk by chunk.

    Yields (text_chunk, None) for content events,
    then ("", LLMUsage) for the final usage event.
    """
    llm = get_llm()

    async for chunk in llm.stream(
        context.prompt,
        system=context.system_prompt,
        max_tokens=4096,
        temperature=0.1,
    ):
        if chunk.is_final:
            yield "", chunk.usage
        else:
            yield chunk.content, None


def parse_citations(
    content: str,
    source_map: dict[str, str],
) -> list[dict]:
    """Extract [SOURCE:...] citations from the response text."""
    pattern = r"\[SOURCE:([^:\]]+):([^:\]]*):([^:\]]*):([^\]]*)\]"
    matches = re.findall(pattern, content)

    citations: list[dict] = []
    seen: set[str] = set()

    for source_id, page, section, quote in matches:
        dedup_key = f"{source_id}:{page}:{quote[:30]}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        page_num = None
        if page and page != "?":
            try:
                page_num = int(page)
            except ValueError:
                pass

        citations.append({
            "source_id": source_id.strip(),
            "source_name": source_map.get(source_id.strip(), "Document inconnu"),
            "page_number": page_num,
            "section_title": section.strip() if section and section != "?" else None,
            "quote": quote.strip(),
        })

    return citations


def clean_citations_from_text(content: str) -> str:
    """Remove [SOURCE:...] tags from the display text."""
    return re.sub(r"\[SOURCE:[^\]]*\]", "", content).strip()
