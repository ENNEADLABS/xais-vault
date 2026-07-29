"""MCP tools — RAG chat."""

from ..client import VaultAPIError, VaultClient
from ..server import mcp


def _get_client(ctx) -> VaultClient:
    """Extrait le VaultClient depuis le contexte MCP."""
    return ctx.state["client"]


@mcp.tool()
async def chat(
    ctx,
    workspace_id: str,
    question: str,
    session_id: str | None = None,
) -> str:
    """Poser une question RAG sur les documents d'un workspace.

    Retourne la réponse de l'IA avec citations des sources.
    Pas de streaming — attend la réponse complète.

    Args:
        workspace_id: L'identifiant UUID du workspace
        question: La question à poser
        session_id: ID de session pour continuer une conversation (optionnel)
    """
    client = _get_client(ctx)
    try:
        result = await client.chat(workspace_id, question, session_id)
        answer = result.get("content", "")
        citations = result.get("citations", [])
        session = result.get("session_id", "")

        parts = [answer]
        if citations:
            parts.append("\n\n---\n**Sources citées :**")
            for c in citations:
                source_name = c.get("source_name", "?")
                page = c.get("page_number")
                page_str = f" p.{page}" if page else ""
                parts.append(f"- {source_name}{page_str}")

        if session:
            parts.append(f"\n_Session : `{session}`_")

        return "\n".join(parts)
    except VaultAPIError as e:
        return f"Erreur : {e.message}"
