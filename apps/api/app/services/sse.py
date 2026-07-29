"""
SSE helpers — format events and build the chat event stream generator.

Extracted from the chat router for the 200-line-per-file rule.
"""

import json
import logging

from .chat_rag import ChatContext
from .chat_session import persist_messages
from .chat_streaming import clean_citations_from_text, parse_citations, stream_response

logger = logging.getLogger(__name__)


def sse_event(event: str, data: dict | list | str) -> str:
    """Format a single SSE event line."""
    payload = (
        json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
    )
    return f"event: {event}\ndata: {payload}\n\n"


async def build_chat_event_stream(
    *,
    context: ChatContext,
    session_id: str,
    organization_id: str,
    user_content: str,
    db,
):
    """Async generator that yields SSE events for a chat response.

    Protocol:
      event: session    → {"session_id": "..."}
      event: content    → {"text": "..."}  (repeated)
      event: citations  → [...]
      event: usage      → {tokens, cost, model}
      event: done       → {}
    """
    yield sse_event("session", {"id": session_id})

    # Métadonnées RAG — le frontend affiche un indicateur de contexte
    if context.rag_metadata and context.rag_metadata.chunk_count > 0:
        yield sse_event(
            "context",
            {
                "chunk_count": context.rag_metadata.chunk_count,
                "source_count": context.rag_metadata.source_count,
                "avg_similarity": context.rag_metadata.avg_similarity,
                "avg_fts_rank": context.rag_metadata.avg_fts_rank,
                "search_mode": context.rag_metadata.search_mode,
                "tokens_used": context.rag_metadata.tokens_used,
                "tokens_budget": context.rag_metadata.tokens_budget,
                "sources_used": context.rag_metadata.sources_used,
            },
        )

    full_content = ""
    final_usage = None
    step = "stream"

    try:
        async for text_chunk, usage in stream_response(context):
            if usage:
                final_usage = usage
            elif text_chunk:
                full_content += text_chunk
                yield sse_event("content", {"text": text_chunk})

        step = "citations"
        citations = parse_citations(full_content, context.source_map)
        display_content = clean_citations_from_text(full_content)

        yield sse_event("citations", {"citations": citations})

        usage_data = {}
        if final_usage:
            usage_data = {
                "input_tokens": final_usage.input_tokens,
                "output_tokens": final_usage.output_tokens,
                "cost_usd": final_usage.cost_usd,
                "model": final_usage.model,
            }
        yield sse_event("usage", usage_data)

        step = "persist"
        await persist_messages(
            db,
            session_id=session_id,
            organization_id=organization_id,
            user_content=user_content,
            assistant_content=display_content,
            citations=citations,
            usage=final_usage,
        )

    except GeneratorExit:
        logger.error("Chat stream cancelled at step=%s (client disconnect?)", step)
        return
    except Exception as e:
        logger.exception("Chat stream error at step=%s: %s", step, e)
        error_hint = f"{type(e).__name__} at {step}"
        yield sse_event("error", {"message": error_hint})

    yield sse_event("done", {})
