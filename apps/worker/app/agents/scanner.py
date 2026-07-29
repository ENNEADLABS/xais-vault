"""
Scanner Agent — full-context analysis of workspace sources.

Loads all extracted_text from ready sources, injects everything into
Claude's context window, and asks for structured JSON insights.

Helpers in scanner_helpers.py. Prompt in prompts/scanner_system.txt.
"""

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from packages.db.client import safe_get_list
from packages.llm.factory import get_llm

from ..services.webhook_dispatcher import _emit_webhook
from .scanner_helpers import build_scan_prompt, parse_scan_response, store_insights

logger = logging.getLogger(__name__)

SCANNER_SYSTEM_PROMPT = (
    Path(__file__).parent / "prompts" / "scanner_system.txt"
).read_text()

# Configurations par mode de scan
SCAN_MODES = {
    "quick": {"max_tokens": 4096, "temperature": 0.1},
    "standard": {"max_tokens": 8192, "temperature": 0.1},
    "deep": {"max_tokens": 16384, "temperature": 0.2},
}


async def run_scan(supabase, payload: dict) -> dict:
    """Execute the Scanner agent on a workspace.

    Args:
        supabase: Supabase client (service role)
        payload: {"workspace_id": str, "organization_id": str, "mode": str (optional)}

    Returns:
        dict with scan stats (insights_count, cost, etc.)
    """
    workspace_id = payload["workspace_id"]
    organization_id = payload["organization_id"]
    mode = payload.get("mode", "standard")
    mode_config = SCAN_MODES.get(mode, SCAN_MODES["standard"])
    start_time = time.monotonic()

    supabase.table("workspaces").update(
        {
            "scan_status": "scanning",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", workspace_id).execute()

    try:
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
            logger.warning(f"No ready sources for workspace {workspace_id}, skipping scan")
            supabase.table("workspaces").update(
                {
                    "scan_status": "pending",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", workspace_id).execute()
            return {"status": "skipped", "reason": "no_ready_sources"}

        prompt = build_scan_prompt(sources)

        logger.info(
            f"Scanning workspace {workspace_id}: {len(sources)} sources, "
            f"~{sum(s.get('word_count', 0) or 0 for s in sources)} words"
        )

        llm = get_llm()
        response = await llm.generate(
            prompt,
            system=SCANNER_SYSTEM_PROMPT,
            max_tokens=mode_config["max_tokens"],
            temperature=mode_config["temperature"],
            json_mode=True,
        )

        scan_data = parse_scan_response(response.content)
        insights_list = scan_data.get("insights", [])
        summary = scan_data.get("summary", {})

        insights_count = await store_insights(
            supabase,
            insights=insights_list,
            workspace_id=workspace_id,
            organization_id=organization_id,
        )

        duration_ms = int((time.monotonic() - start_time) * 1000)

        supabase.table("workspaces").update(
            {
                "scan_status": "scanned",
                "scan_summary": summary,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", workspace_id).execute()

        if insights_count > 0:
            await _emit_webhook(
                supabase,
                organization_id=organization_id,
                event_type="insight.created",
                data={
                    "workspace_id": workspace_id,
                    "count": insights_count,
                    "types": list(
                        set(f.get("type", "observation") for f in insights_list)
                    ),
                },
            )

        await _emit_webhook(
            supabase,
            organization_id=organization_id,
            event_type="scan.completed",
            data={
                "workspace_id": workspace_id,
                "sources_scanned": len(sources),
                "insights_created": insights_count,
            },
        )

        total_words = sum(s.get("word_count", 0) or 0 for s in sources)
        supabase.table("agent_traces").insert(
            {
                "workspace_id": workspace_id,
                "organization_id": organization_id,
                "agent_type": "scanner",
                "input_summary": f"{len(sources)} sources, {total_words} words",
                "output_summary": f"{insights_count} insights generated",
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cost_usd": float(response.usage.cost_usd),
                "model_used": response.usage.model,
                "duration_ms": duration_ms,
            }
        ).execute()

        stats = {
            "workspace_id": workspace_id,
            "sources_scanned": len(sources),
            "insights_created": insights_count,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cost_usd": response.usage.cost_usd,
            "duration_ms": duration_ms,
        }

        logger.info(f"Scan complete for workspace {workspace_id}: {stats}")
        return stats

    except Exception:
        supabase.table("workspaces").update(
            {
                "scan_status": "failed",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", workspace_id).execute()
        raise
