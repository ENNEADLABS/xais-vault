"""
Scanner helpers — prompt building, response parsing, insights storage.

Extracted from scanner.py for the 200-line-per-file rule.
"""

import logging
from datetime import datetime, timezone

from packages.core.agent_schemas import ScanResponse
from packages.llm.response_parser import parse_llm_json

logger = logging.getLogger(__name__)

# Valid enum values for DB constraints (kept for reference and test imports)
VALID_TYPES = {"red_flag", "metric", "observation", "missing_info"}
VALID_SEVERITIES = {"critical", "high", "medium", "low"}


def build_scan_prompt(sources: list[dict]) -> str:
    """Build the full-context prompt from all source texts.

    Each source is clearly delimited with its ID and name for citation tracking.
    Truncates individual sources if total context would exceed ~400k chars (~100k tokens).
    """
    MAX_TOTAL_CHARS = 400_000
    parts: list[str] = ["DOCUMENTS DU DOSSIER D'INVESTISSEMENT :\n"]

    total_chars = 0
    for source in sources:
        text = source.get("extracted_text") or ""
        if not text.strip():
            continue

        header = (
            f"═══════════════════════════════════════\n"
            f"DOCUMENT: {source['name']}\n"
            f"SOURCE_ID: {source['id']}\n"
            f"Type: {source['type']} | Pages: {source.get('page_count', '?')} | Mots: {source.get('word_count', '?')}\n"
            f"═══════════════════════════════════════\n"
        )

        available = MAX_TOTAL_CHARS - total_chars - len(header) - 100
        if available <= 0:
            parts.append(f"\n[... {source['name']} omis — limite de contexte atteinte ...]\n")
            break

        if len(text) > available:
            text = text[:available] + "\n\n[... document tronqué ...]"

        parts.append(header + text)
        total_chars += len(header) + len(text)

    parts.append(
        "\n\n═══════════════════════════════════════\n"
        "FIN DES DOCUMENTS\n"
        "═══════════════════════════════════════\n\n"
        "Analyse l'ensemble de ces documents et produis la liste de insights structurés."
    )

    return "\n\n".join(parts)


def parse_scan_response(content: str) -> dict:
    """Parse the scanner's JSON response into a validated ScanResponse."""
    fallback = ScanResponse()
    result = parse_llm_json(content, ScanResponse, fallback)
    return result.model_dump()


async def store_insights(
    supabase,
    *,
    insights: list[dict],
    workspace_id: str,
    organization_id: str,
) -> int:
    """Validate and insert insights into the DB.

    Returns the number of insights successfully inserted.
    """
    now = datetime.now(timezone.utc).isoformat()
    rows: list[dict] = []

    for f in insights:
        title = f.get("title")
        description = f.get("description")
        if not title or not description:
            logger.warning(f"Skipping insight without title/description: {f}")
            continue

        row = {
            "workspace_id": workspace_id,
            "organization_id": organization_id,
            "type": f.get("type", "observation"),
            "severity": f.get("severity", "medium"),
            "confidence_score": f.get("confidence_score", 50),
            "title": title[:500],
            "description": description,
            "source_id": f.get("source_id"),
            "source_page": f.get("source_page"),
            "source_section": f.get("source_section"),
            "source_quote": (f.get("source_quote") or "")[:500] or None,
            "status": "pending",
            "metadata": {},
            "created_at": now,
            "updated_at": now,
        }
        rows.append(row)

    if not rows:
        logger.warning(f"No valid insights to insert for workspace {workspace_id}")
        return 0

    BATCH_SIZE = 50
    inserted = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        result = supabase.table("insights").insert(batch).execute()
        inserted += len(result.data or [])

    logger.info(f"Inserted {inserted} insights for workspace {workspace_id}")
    return inserted
