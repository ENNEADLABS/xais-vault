"""MCP tools — deliverable generation."""

from ..client import VaultAPIError, VaultClient
from ..server import mcp


def _get_client(ctx) -> VaultClient:
    """Extrait le VaultClient depuis le contexte MCP."""
    return ctx.state["client"]


@mcp.tool()
async def generate_deliverable(
    ctx,
    workspace_id: str,
    type: str,
    name: str,
    options: dict | None = None,
) -> str:
    """Lancer la génération d'un livrable DOCX. Retourne 202 (job async).

    Args:
        workspace_id: L'identifiant UUID du workspace
        type: Type de livrable — executive_summary, investment_memo, dd_report
        name: Nom du livrable (ex: "Synthèse exécutive Alpha Q1 2025")
        options: Options additionnelles (optionnel)
    """
    client = _get_client(ctx)
    try:
        result = await client.generate_deliverable(workspace_id, type, name, options)
        job_id = result.get("data", {}).get("job_id", "?")
        return (
            f'Génération du livrable **"{name}"** ({type}) lancée pour le workspace `{workspace_id}`.\n'
            f"Job en cours : `{job_id}`. Le livrable sera disponible dans l'interface une fois terminé."
        )
    except VaultAPIError as e:
        return f"Erreur : {e.message}"
