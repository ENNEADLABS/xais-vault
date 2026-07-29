"""
Writer helpers — workspace context loading, prompt building, storage.

Extracted from writer.py for the 200-line-per-file rule.
"""

import logging
from dataclasses import dataclass, field

from packages.db.client import safe_get_list, safe_get_one

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# Max tokens per deliverable type
MAX_TOKENS = {
    "executive_summary": 4096,
    "investment_memo": 16384,
    "dd_report": 32768,
}

# Max investigation report length per type (chars)
INVESTIGATION_MAX_CHARS = {
    "executive_summary": 500,
    "investment_memo": 2000,
    "dd_report": None,  # No truncation
}

# Max insights count per type (None = all)
FINDINGS_MAX_COUNT = {
    "executive_summary": 10,
    "investment_memo": None,
    "dd_report": None,
}


@dataclass
class DealContext:
    workspace: dict
    sources: list[dict] = field(default_factory=list)
    insights: list[dict] = field(default_factory=list)
    investigations: list[dict] = field(default_factory=list)
    total_sources: int = 0
    total_insights: int = 0
    total_investigations: int = 0


async def load_workspace_context(supabase, workspace_id: str, organization_id: str) -> DealContext:
    """Load all workspace data needed by the writer (no extracted_text — too heavy)."""
    workspace = safe_get_one(
        supabase.table("workspaces")
        .select("*")
        .eq("id", workspace_id)
        .eq("organization_id", organization_id)
        .execute()
    )
    if not workspace:
        raise ValueError(f"Workspace {workspace_id} not found")

    sources = safe_get_list(
        supabase.table("sources")
        .select("id, name, type, word_count, page_count, summary, topics")
        .eq("workspace_id", workspace_id)
        .eq("organization_id", organization_id)
        .eq("status", "ready")
        .execute()
    )

    raw_insights = safe_get_list(
        supabase.table("insights")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("organization_id", organization_id)
        .eq("status", "confirmed")
        .execute()
    )
    insights = sorted(raw_insights, key=lambda f: SEVERITY_ORDER.get(f.get("severity", "low"), 99))

    investigations = safe_get_list(
        supabase.table("investigations")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("organization_id", organization_id)
        .eq("status", "completed")
        .order("created_at", desc=False)
        .execute()
    )

    return DealContext(
        workspace=workspace,
        sources=sources,
        insights=insights,
        investigations=investigations,
        total_sources=len(sources),
        total_insights=len(insights),
        total_investigations=len(investigations),
    )


def build_writer_prompt(context: DealContext, deliverable_type: str) -> str:
    """Build the full Claude prompt for document generation."""
    workspace = context.workspace
    parts: list[str] = []

    parts.append(
        f"DEAL : {workspace.get('name', 'N/A')}\n"
        f"Entreprise cible : {workspace.get('target_company', 'N/A')}\n"
        f"Secteur : {workspace.get('sector', 'N/A')}\n"
        f"Type : {workspace.get('deal_type', 'N/A')}"
    )

    if workspace.get("scan_summary"):
        s = workspace["scan_summary"]
        parts.append(
            "═══ RÉSUMÉ DU SCAN ═══\n"
            f"Insights : {s.get('total_insights', 0)} | "
            f"Critiques : {s.get('critical_count', 0)} | "
            f"Hauts : {s.get('high_count', 0)}\n"
            f"Risque global : {s.get('deal_risk_score', '?')}/100\n"
            f"Observation : {s.get('key_observation', '')}"
        )

    max_insights = FINDINGS_MAX_COUNT.get(deliverable_type)
    insights = context.insights[:max_insights] if max_insights else context.insights
    parts.append(
        f"═══ FINDINGS CONFIRMÉS ({len(insights)}"
        + (f" sur {context.total_insights} affichés" if max_insights and len(context.insights) > len(insights) else "")
        + ") ═══"
    )
    for f in insights:
        verification = f.get("verification") or {}
        entry = (
            f"[{f.get('severity', '?').upper()}] {f.get('title', '')}\n"
            f"{f.get('description', '')}"
        )
        if f.get("source_quote"):
            entry += f"\nCitation: \"{f['source_quote']}\""
        if verification.get("verdict"):
            entry += f"\nVérification: {verification['verdict']} — {verification.get('explanation', '')}"
        parts.append(entry)

    max_inv_chars = INVESTIGATION_MAX_CHARS.get(deliverable_type)
    parts.append(f"═══ INVESTIGATIONS COMPLÉTÉES ({context.total_investigations}) ═══")
    for inv in context.investigations:
        report = inv.get("report") or ""
        if max_inv_chars and len(report) > max_inv_chars:
            report = report[:max_inv_chars] + "\n[... tronqué ...]"
        parts.append(f"Question : {inv.get('question', '')}\n{report}")

    type_label = deliverable_type.replace("_", " ").upper()
    parts.append(
        f"═══ CONSIGNE ═══\n"
        f"Génère un {type_label} en Markdown structuré selon le format demandé."
    )

    return "\n\n".join(parts)


async def update_progress(supabase, deliverable_id: str, step: str, percent: int) -> None:
    """Update deliverable current_step and progress_percent."""
    supabase.table("deliverables").update({
        "current_step": step,
        "progress_percent": percent,
    }).eq("id", deliverable_id).execute()


async def upload_docx(
    supabase,
    docx_bytes: bytes,
    workspace_id: str,
    deliverable_id: str,
    deliverable_type: str,
) -> tuple[str, int]:
    """Upload DOCX to Supabase Storage. Returns (storage_path, file_size_bytes)."""
    file_name = f"{deliverable_type}_{deliverable_id[:8]}.docx"
    storage_path = f"{workspace_id}/{file_name}"

    supabase.storage.from_("deliverables").upload(
        path=storage_path,
        file=docx_bytes,
        file_options={
            "content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
    )

    return storage_path, len(docx_bytes)
