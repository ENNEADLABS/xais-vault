"""
Verifier helpers — prompt building, response parsing, insight update.

Extracted from verifier.py for the 200-line-per-file rule.
"""

import logging
from datetime import datetime, timezone

from packages.core.agent_schemas import VerificationResponse
from packages.llm.response_parser import parse_llm_json

logger = logging.getLogger(__name__)

VALID_VERDICTS = {"confirmed", "contradicted", "inconclusive", "nuanced"}

# Map LLM verdict → insight status in DB
VERDICT_TO_STATUS = {
    "confirmed": "confirmed",
    "contradicted": "rejected",
    "inconclusive": "pending",
    "nuanced": "pending",
}

MAX_TOTAL_CHARS = 400_000


def build_verification_prompt(insight: dict, sources: list[dict]) -> str:
    """Build the full-context prompt with insight details + all source texts.

    The insight is injected first so the model knows exactly what to verify.
    Sources use the same delimiters as the scanner for consistency.
    """
    insight_block = (
        "╔═══════════════════════════════════════╗\n"
        "║         INSIGHT À VÉRIFIER            ║\n"
        "╚═══════════════════════════════════════╝\n"
        f"ID          : {insight.get('id', 'N/A')}\n"
        f"Titre       : {insight.get('title', '')}\n"
        f"Type        : {insight.get('type', '')}\n"
        f"Sévérité    : {insight.get('severity', '')}\n"
        f"Confiance   : {insight.get('confidence_score', '?')}%\n"
        f"Description : {insight.get('description', '')}\n"
    )

    source_quote = insight.get("source_quote")
    source_page = insight.get("source_page")
    if source_quote:
        insight_block += f"Extrait cité : \"{source_quote}\""
        if source_page:
            insight_block += f" (page {source_page})"
        insight_block += "\n"

    insight_block += (
        "\n═══════════════════════════════════════\n"
        "Cross-référence ce insight contre TOUS les documents ci-dessous.\n"
        "═══════════════════════════════════════\n"
    )

    parts: list[str] = [insight_block, "\nDOCUMENTS DU DOSSIER D'INVESTISSEMENT :\n"]

    total_chars = len(insight_block)
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
        "Produis le verdict de vérification au format JSON demandé."
    )

    return "\n\n".join(parts)


def parse_verification_response(content: str) -> dict:
    """Parse the verifier's JSON response into a validated VerificationResponse."""
    fallback = VerificationResponse(
        explanation="Erreur de parsing de la réponse LLM."
    )
    result = parse_llm_json(content, VerificationResponse, fallback)
    data = result.model_dump()
    # Filtrer les évidences sans source_id ni quote (defense in depth)
    data["evidence"] = [
        e for e in data["evidence"] if e.get("source_id") and e.get("quote")
    ]
    return data


async def update_insight_verification(
    supabase,
    *,
    insight_id: str,
    verification: dict,
    agent_trace_id: str | None = None,
) -> None:
    """Store verification result in insights table.

    Updates insights.verification (JSONB) and insights.status.
    """
    verdict = verification["verdict"]
    new_status = VERDICT_TO_STATUS.get(verdict, "pending")

    verification_payload = {
        "verdict": verdict,
        "evidence": verification["evidence"],
        "explanation": verification["explanation"],
    }
    if agent_trace_id:
        verification_payload["agent_trace_id"] = agent_trace_id

    supabase.table("insights").update({
        "verification": verification_payload,
        "status": new_status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", insight_id).execute()

    logger.info(f"Insight {insight_id} updated: verdict={verdict}, status={new_status}")
