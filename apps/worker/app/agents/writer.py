"""
Writer Agent — generates professional DOCX deliverables from workspace analysis.

Loads confirmed insights + completed investigations, generates a structured
Markdown document via Claude, then converts it to DOCX.

Helpers in writer_helpers.py. DOCX builder in services/docx_builder.py.
Prompt in prompts/writer_system.txt.
"""

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from packages.db.client import safe_get_one
from packages.llm.factory import get_llm

from ..services.docx_builder import build_docx
from ..services.webhook_dispatcher import _emit_webhook
from .writer_helpers import (
    MAX_TOKENS,
    DealContext,
    build_writer_prompt,
    load_workspace_context,
    update_progress,
    upload_docx,
)

logger = logging.getLogger(__name__)

WRITER_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "writer_system.txt").read_text()


async def run_generation(supabase, payload: dict) -> dict:
    """Execute the Writer agent to generate a deliverable.

    Args:
        supabase: Supabase client (service role)
        payload: {
            "deliverable_id": str,
            "workspace_id": str,
            "organization_id": str,
            "type": "executive_summary" | "investment_memo" | "dd_report",
        }

    Returns:
        dict with generation stats (file_path, file_size, tokens, cost, etc.)
    """
    deliverable_id = payload["deliverable_id"]
    workspace_id = payload["workspace_id"]
    organization_id = payload["organization_id"]
    deliverable_type = payload["type"]
    start_time = time.monotonic()

    # Verify deliverable exists
    deliverable = safe_get_one(
        supabase.table("deliverables")
        .select("id, type, name")
        .eq("id", deliverable_id)
        .eq("organization_id", organization_id)
        .execute()
    )
    if not deliverable:
        raise ValueError(f"Deliverable {deliverable_id} not found")

    supabase.table("deliverables").update({
        "status": "processing",
        "current_step": "loading_data",
        "progress_percent": 5,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", deliverable_id).execute()

    try:
        # 1. Load workspace context
        context: DealContext = await load_workspace_context(supabase, workspace_id, organization_id)
        await update_progress(supabase, deliverable_id, "generating_markdown", 20)

        # 2. Build prompt and call LLM
        prompt = build_writer_prompt(context, deliverable_type)
        max_tokens = MAX_TOKENS.get(deliverable_type, 8192)

        logger.info(
            f"Generating {deliverable_type} for workspace {workspace_id}: "
            f"{context.total_insights} insights, {context.total_investigations} investigations"
        )

        llm = get_llm()
        response = await llm.generate(
            prompt,
            system=WRITER_SYSTEM_PROMPT,
            max_tokens=max_tokens,
            temperature=0.2,
        )

        markdown_content = response.content

        # Save markdown content
        supabase.table("deliverables").update({
            "content_markdown": markdown_content,
            "current_step": "building_docx",
            "progress_percent": 70,
        }).eq("id", deliverable_id).execute()

        # 3. Convert to DOCX
        workspace = context.workspace
        docx_bytes = build_docx(
            markdown_content=markdown_content,
            deliverable_type=deliverable_type,
            workspace_name=workspace.get("name", "Workspace"),
            target_company=workspace.get("target_company"),
        )

        await update_progress(supabase, deliverable_id, "uploading", 90)

        # 4. Upload DOCX
        file_path, file_size = await upload_docx(
            supabase,
            docx_bytes=docx_bytes,
            workspace_id=workspace_id,
            deliverable_id=deliverable_id,
            deliverable_type=deliverable_type,
        )

        duration_ms = int((time.monotonic() - start_time) * 1000)

        # 5. Mark completed
        supabase.table("deliverables").update({
            "status": "completed",
            "current_step": "done",
            "progress_percent": 100,
            "file_path": file_path,
            "file_size_bytes": file_size,
            "total_input_tokens": response.usage.input_tokens,
            "total_output_tokens": response.usage.output_tokens,
            "total_cost_usd": float(response.usage.cost_usd),
            "models_used": [response.usage.model],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", deliverable_id).execute()

        await _emit_webhook(supabase, organization_id=organization_id, event_type="deliverable.ready", data={
            "deliverable_id": deliverable_id,
            "workspace_id": workspace_id,
            "type": deliverable_type,
            "file_path": file_path,
            "file_size_bytes": file_size,
        })

        # 6. Agent trace
        supabase.table("agent_traces").insert({
            "workspace_id": workspace_id,
            "organization_id": organization_id,
            "agent_type": "writer",
            "input_summary": (
                f"type={deliverable_type}, {context.total_insights} insights, "
                f"{context.total_investigations} investigations"
            ),
            "output_summary": f"DOCX {file_size // 1024}KB, {len(markdown_content)} chars Markdown",
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cost_usd": float(response.usage.cost_usd),
            "model_used": response.usage.model,
            "duration_ms": duration_ms,
        }).execute()

        stats = {
            "deliverable_id": deliverable_id,
            "workspace_id": workspace_id,
            "type": deliverable_type,
            "file_path": file_path,
            "file_size_bytes": file_size,
            "markdown_length": len(markdown_content),
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cost_usd": response.usage.cost_usd,
            "duration_ms": duration_ms,
        }

        logger.info(f"Generation complete: {stats}")
        return stats

    except Exception as e:
        supabase.table("deliverables").update({
            "status": "failed",
            "error_message": str(e),
        }).eq("id", deliverable_id).execute()
        raise
