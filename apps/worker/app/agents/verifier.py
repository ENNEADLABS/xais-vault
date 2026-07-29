"""
Verifier Agent — cross-reference a insight against all workspace sources.

Loads the target insight and all extracted_text from ready sources,
injects everything into Claude's context window, and asks for a
structured JSON verdict.

Helpers in verifier_helpers.py. Prompt in prompts/verifier_system.txt.
"""

import logging
import time
from pathlib import Path

from packages.db.client import safe_get_list, safe_get_one
from packages.llm.factory import get_llm

from .verifier_helpers import (
    VERDICT_TO_STATUS,
    build_verification_prompt,
    parse_verification_response,
    update_insight_verification,
)

logger = logging.getLogger(__name__)

VERIFIER_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "verifier_system.txt").read_text()


async def run_verification(supabase, payload: dict) -> dict:
    """Execute the Verifier agent on a insight.

    Args:
        supabase: Supabase client (service role)
        payload: {"insight_id": str, "workspace_id": str, "organization_id": str}

    Returns:
        dict with verification stats (verdict, evidence_count, cost, etc.)
    """
    insight_id = payload["insight_id"]
    workspace_id = payload["workspace_id"]
    organization_id = payload["organization_id"]
    start_time = time.monotonic()

    # 1. Load the insight
    insight = safe_get_one(
        supabase.table("insights")
        .select("*")
        .eq("id", insight_id)
        .eq("organization_id", organization_id)
        .execute()
    )
    if not insight:
        raise ValueError(f"Insight {insight_id} not found")

    # 2. Load all ready sources for the workspace
    sources = safe_get_list(
        supabase.table("sources")
        .select("id, name, type, extracted_text, page_count, word_count")
        .eq("workspace_id", workspace_id)
        .eq("organization_id", organization_id)
        .eq("status", "ready")
        .order("created_at", desc=False)
        .execute()
    )

    if not sources:
        logger.warning(f"No ready sources for workspace {workspace_id}, marking insight inconclusive")
        verification = {
            "verdict": "inconclusive",
            "evidence": [],
            "explanation": "Aucun document disponible pour vérifier ce insight.",
        }
        await update_insight_verification(
            supabase,
            insight_id=insight_id,
            verification=verification,
        )
        return {"insight_id": insight_id, "verdict": "inconclusive", "reason": "no_ready_sources"}

    # 3. Build prompt
    prompt = build_verification_prompt(insight, sources)

    total_words = sum(s.get("word_count", 0) or 0 for s in sources)
    logger.info(
        f"Verifying insight {insight_id}: {len(sources)} sources, ~{total_words} words"
    )

    # 4. Call LLM
    llm = get_llm()
    response = await llm.generate(
        prompt,
        system=VERIFIER_SYSTEM_PROMPT,
        max_tokens=4096,
        temperature=0.1,
        json_mode=True,
    )

    # 5. Parse response
    verification = parse_verification_response(response.content)

    duration_ms = int((time.monotonic() - start_time) * 1000)

    # 6. Record agent trace first (to get its ID for the verification payload)
    trace_result = supabase.table("agent_traces").insert({
        "workspace_id": workspace_id,
        "organization_id": organization_id,
        "agent_type": "verifier",
        "input_summary": f"Insight '{insight.get('title', insight_id)}', {len(sources)} sources, {total_words} words",
        "output_summary": f"verdict={verification['verdict']}, evidence={len(verification['evidence'])} items",
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cost_usd": float(response.usage.cost_usd),
        "model_used": response.usage.model,
        "duration_ms": duration_ms,
    }).execute()

    trace_id = (trace_result.data[0]["id"] if trace_result.data else None)

    # 7. Store verification result on the insight
    await update_insight_verification(
        supabase,
        insight_id=insight_id,
        verification=verification,
        agent_trace_id=trace_id,
    )

    stats = {
        "insight_id": insight_id,
        "workspace_id": workspace_id,
        "verdict": verification["verdict"],
        "evidence_count": len(verification["evidence"]),
        "new_status": VERDICT_TO_STATUS.get(verification["verdict"], "pending"),
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cost_usd": response.usage.cost_usd,
        "duration_ms": duration_ms,
    }

    logger.info(f"Verification complete for insight {insight_id}: {stats}")
    return stats
