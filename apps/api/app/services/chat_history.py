"""
Chat history management — summarization et injection dans le prompt.

Si la conversation dépasse SUMMARY_TRIGGER messages, un résumé LLM
remplace les anciens messages pour préserver le contexte sans exploser le budget tokens.
"""

import logging

from packages.db.client import safe_get_list, safe_get_one
from packages.llm.factory import get_llm

logger = logging.getLogger(__name__)

MAX_RECENT_MESSAGES = 10
SUMMARY_TRIGGER = 15
RECENT_AFTER_SUMMARY = 5

SUMMARIZE_SYSTEM = (
    "Résume cette conversation d'analyse documentaire en 500 tokens maximum.\n"
    "Conserve : questions principales, conclusions clés, sources mentionnées, décisions en cours.\n"
    "Ne résume PAS les formulations exactes — va à l'essentiel."
)


async def build_history_block(db, session_id: str) -> str:
    """Construit le bloc d'historique pour le prompt.

    Si > SUMMARY_TRIGGER messages : résumé + 5 derniers messages.
    Sinon : 10 derniers messages (comportement classique).
    """
    count_result = (
        db.table("chat_messages")
        .select("id", count="exact")
        .eq("session_id", session_id)
        .execute()
    )
    total = count_result.count or 0

    if total <= MAX_RECENT_MESSAGES:
        recent = await _build_recent_messages(db, session_id, MAX_RECENT_MESSAGES)
        if not recent:
            return ""
        return f"HISTORIQUE DE LA CONVERSATION :\n{recent}\n\n---\n\n"

    # Mode résumé
    session = safe_get_one(
        db.table("chat_sessions")
        .select("history_summary")
        .eq("id", session_id)
        .execute()
    )
    summary = (session or {}).get("history_summary")

    if not summary:
        summary = await _generate_summary(db, session_id)

    recent = await _build_recent_messages(db, session_id, RECENT_AFTER_SUMMARY)

    return (
        f"RÉSUMÉ DE LA CONVERSATION PRÉCÉDENTE :\n{summary}\n\n"
        f"---\n\nMESSAGES RÉCENTS :\n{recent}\n\n---\n\n"
    )


async def maybe_update_summary(db, session_id: str) -> None:
    """Met à jour le résumé si > 10 messages depuis le dernier résumé."""
    session = safe_get_one(
        db.table("chat_sessions")
        .select("history_summary_until")
        .eq("id", session_id)
        .execute()
    )
    if not session or not session.get("history_summary_until"):
        return

    # Compter les messages après le dernier résumé
    new_count_result = (
        db.table("chat_messages")
        .select("id", count="exact")
        .eq("session_id", session_id)
        .gt("id", session["history_summary_until"])
        .execute()
    )
    new_count = new_count_result.count or 0

    if new_count >= MAX_RECENT_MESSAGES:
        logger.info(
            "history_summarization.triggered",
            extra={
                "session_id": session_id,
                "new_messages_count": new_count,
                "trigger_threshold": MAX_RECENT_MESSAGES,
            },
        )
        await _generate_summary(db, session_id)


async def _generate_summary(db, session_id: str) -> str:
    """Génère un résumé de l'historique via le LLM."""
    messages = safe_get_list(
        db.table("chat_messages")
        .select("id, role, content, created_at")
        .eq("session_id", session_id)
        .order("created_at")
        .execute()
    )

    if not messages:
        return ""

    # Résumer tout sauf les 5 derniers (qui seront en clair)
    to_summarize = (
        messages[:-RECENT_AFTER_SUMMARY]
        if len(messages) > RECENT_AFTER_SUMMARY
        else messages
    )

    conversation_text = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'][:1000]}"
        for m in to_summarize
    )

    llm = get_llm()
    response = await llm.generate(
        f"Conversation à résumer :\n\n{conversation_text}",
        system=SUMMARIZE_SYSTEM,
        max_tokens=600,
        temperature=0.1,
    )

    # Métriques de coût de la summarization
    usage = response.usage
    logger.info(
        "history_summarization.llm_cost",
        extra={
            "session_id": session_id,
            "model": usage.model,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cost_usd": usage.cost_usd,
            "messages_summarized": len(to_summarize),
        },
    )

    # Persister le coût dans usage_logs (monitoring super-admin)
    _persist_usage(db, session_id, usage)

    last_id = to_summarize[-1].get("id") if to_summarize else None
    db.table("chat_sessions").update(
        {
            "history_summary": response.content,
            "history_summary_until": last_id,
        }
    ).eq("id", session_id).execute()

    logger.info(
        "history_summarization.completed",
        extra={
            "session_id": session_id,
            "summary_length_chars": len(response.content),
        },
    )
    return response.content


def _persist_usage(db, session_id: str, usage) -> None:
    """Persiste le coût de summarization dans usage_logs pour le monitoring."""
    try:
        session_info = safe_get_one(
            db.table("chat_sessions").select("workspace_id").eq("id", session_id).execute()
        )
        if not session_info or not session_info.get("workspace_id"):
            return

        workspace_info = safe_get_one(
            db.table("workspaces")
            .select("organization_id")
            .eq("id", session_info["workspace_id"])
            .execute()
        )
        if not workspace_info:
            return

        db.table("usage_logs").insert(
            {
                "organization_id": workspace_info["organization_id"],
                "workspace_id": session_info["workspace_id"],
                "operation": "summarization",
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cost_usd": usage.cost_usd,
                "model_used": usage.model,
            }
        ).execute()
    except Exception:
        logger.warning("history_summarization.usage_persist_failed", exc_info=True)


async def _build_recent_messages(db, session_id: str, limit: int = 10) -> str:
    """Récupère et formate les N derniers messages."""
    result = (
        db.table("chat_messages")
        .select("role, content")
        .eq("session_id", session_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    messages = safe_get_list(result)
    if not messages:
        return ""

    messages.reverse()
    parts = []
    for msg in messages:
        role_label = "Utilisateur" if msg["role"] == "user" else "Assistant"
        parts.append(f"{role_label}: {msg['content'][:2000]}")

    return "\n".join(parts)
