"""
Researcher Agent — deep investigation with doc search + web search.

Two-phase research:
  1. Semantic search in workspace chunks via search_chunks_hybrid RPC (Gemini embeddings)
  2. Web search via Tavily (competitors, market, regulation, patents)

Combines both into a Markdown report via Claude.

Helpers in researcher_helpers.py. Prompt in prompts/researcher_system.txt.
"""

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from packages.db.client import safe_get_one
from packages.llm.factory import get_embedder, get_llm

from ..services.webhook_dispatcher import _emit_webhook
from .researcher_helpers import (
    build_research_prompt,
    build_web_query,
    search_web,
    search_workspace_documents,
    store_investigation_result,
)

logger = logging.getLogger(__name__)

RESEARCHER_SYSTEM_PROMPT = (
    Path(__file__).parent / "prompts" / "researcher_system.txt"
).read_text()


async def run_investigation(supabase, payload: dict) -> dict:
    """Execute the Researcher agent on an investigation.

    Args:
        supabase: Supabase client (service role)
        payload: {
            "investigation_id": str,
            "workspace_id": str,
            "organization_id": str,
        }

    Returns:
        dict with investigation stats (doc_chunks_found, web_results_found, report_length, etc.)
    """
    investigation_id = payload["investigation_id"]
    workspace_id = payload["workspace_id"]
    organization_id = payload["organization_id"]
    start_time = time.monotonic()

    # 1. Charger l'investigation
    investigation = safe_get_one(
        supabase.table("investigations")
        .select("*")
        .eq("id", investigation_id)
        .eq("organization_id", organization_id)
        .execute()
    )
    if not investigation:
        raise ValueError(f"Investigation {investigation_id} not found")

    question = investigation["question"]
    scope = investigation.get("scope", "both")
    insight_id = investigation.get("insight_id")

    supabase.table("investigations").update(
        {
            "status": "processing",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", investigation_id).execute()

    try:
        # 2. Charger le insight si applicable
        insight = None
        if insight_id:
            insight = safe_get_one(
                supabase.table("insights")
                .select("*")
                .eq("id", insight_id)
                .eq("organization_id", organization_id)
                .execute()
            )

        # 3. Phase 1 — Recherche documentaire
        doc_chunks: list[dict] = []
        if scope in ("documents", "both"):
            search_query = (
                f"{insight.get('title', '')} {question}".strip()
                if insight
                else question
            )
            embedder = get_embedder()
            doc_chunks = await search_workspace_documents(
                supabase, embedder, search_query, workspace_id
            )
            logger.info(
                f"Doc search for investigation {investigation_id}: {len(doc_chunks)} chunks"
            )

        # 4. Phase 2 — Recherche web
        web_results: list[dict] = []
        if scope in ("web", "both"):
            web_query = build_web_query(question, insight)
            web_results = await search_web(web_query)
            logger.info(
                f"Web search for investigation {investigation_id}: {len(web_results)} results"
            )

        # 5. Construire le prompt
        prompt = build_research_prompt(question, insight, doc_chunks, web_results)

        # 6. Appel LLM
        llm = get_llm()
        response = await llm.generate(
            prompt,
            system=RESEARCHER_SYSTEM_PROMPT,
            max_tokens=4096,
            temperature=0.2,
        )

        duration_ms = int((time.monotonic() - start_time) * 1000)

        # 7. Stocker le résultat
        await store_investigation_result(
            supabase,
            investigation_id=investigation_id,
            report=response.content,
            doc_references=doc_chunks,
            web_sources=web_results,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost_usd=response.usage.cost_usd,
            model_used=response.usage.model,
        )

        await _emit_webhook(
            supabase,
            organization_id=organization_id,
            event_type="investigation.completed",
            data={
                "investigation_id": investigation_id,
                "workspace_id": workspace_id,
                "insight_id": insight_id,
                "question": question[:200],
                "doc_chunks_found": len(doc_chunks),
                "web_results_found": len(web_results),
            },
        )

        # 8. Mettre à jour le insight lié si applicable
        if insight_id:
            supabase.table("insights").update(
                {
                    "status": "investigating",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", insight_id).execute()

        # 9. Agent trace
        supabase.table("agent_traces").insert(
            {
                "workspace_id": workspace_id,
                "organization_id": organization_id,
                "agent_type": "researcher",
                "input_summary": f"Q: '{question[:100]}', {len(doc_chunks)} chunks, {len(web_results)} web",
                "output_summary": f"Report {len(response.content)} chars",
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cost_usd": float(response.usage.cost_usd),
                "model_used": response.usage.model,
                "duration_ms": duration_ms,
            }
        ).execute()

        stats = {
            "investigation_id": investigation_id,
            "workspace_id": workspace_id,
            "insight_id": insight_id,
            "doc_chunks_found": len(doc_chunks),
            "web_results_found": len(web_results),
            "report_length": len(response.content),
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cost_usd": response.usage.cost_usd,
            "duration_ms": duration_ms,
        }

        logger.info(f"Investigation complete: {stats}")
        return stats

    except Exception:
        supabase.table("investigations").update(
            {
                "status": "failed",
            }
        ).eq("id", investigation_id).execute()
        raise
