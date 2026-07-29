"""MCP tools — insights and investigations."""

from ..client import VaultAPIError, VaultClient
from ..server import mcp


def _get_client(ctx) -> VaultClient:
    """Extrait le VaultClient depuis le contexte MCP."""
    return ctx.state["client"]


@mcp.tool()
async def list_insights(
    ctx,
    workspace_id: str,
    type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
) -> str:
    """Liste les insights d'un workspace, filtrables par type/severity/status.

    Args:
        workspace_id: L'identifiant UUID du workspace
        type: Filtre — red_flag, metric, observation
        severity: Filtre — critical, high, medium, low
        status: Filtre — pending, verified, dismissed
    """
    client = _get_client(ctx)
    try:
        result = await client.list_insights(
            workspace_id,
            type=type,
            severity=severity,
            status=status,
        )
        insights = result.get("data", [])
        if not insights:
            return f"Aucun insight pour le workspace `{workspace_id}`."
        lines = [f"**{len(insights)} insight(s) dans le workspace `{workspace_id}` :**\n"]
        for f in insights:
            sev = f.get("severity", "?")
            ftype = f.get("type", "?")
            fstatus = f.get("status", "?")
            lines.append(
                f"- [{sev.upper()}] **{f['title']}** (id: `{f['id']}`) "
                f"— {ftype}, {fstatus}"
            )
        return "\n".join(lines)
    except VaultAPIError as e:
        return f"Erreur : {e.message}"


@mcp.tool()
async def investigate_insight(ctx, workspace_id: str, insight_id: str) -> str:
    """Lancer une investigation approfondie sur un insight. Retourne 202 (job async).

    Args:
        workspace_id: L'identifiant UUID du workspace
        insight_id: L'identifiant UUID du insight à investiguer
    """
    client = _get_client(ctx)
    try:
        result = await client.investigate_insight(workspace_id, insight_id)
        job_id = result.get("data", {}).get("job_id", "?")
        return (
            f"Investigation lancée pour le insight `{insight_id}`.\n"
            f"Job en cours : `{job_id}`. Utilisez `list_investigations` pour suivre l'avancement."
        )
    except VaultAPIError as e:
        return f"Erreur : {e.message}"


@mcp.tool()
async def list_investigations(
    ctx,
    workspace_id: str,
    status: str | None = None,
    insight_id: str | None = None,
) -> str:
    """Liste les investigations d'un workspace.

    Args:
        workspace_id: L'identifiant UUID du workspace
        status: Filtre — pending, processing, completed, failed
        insight_id: Filtre par insight source
    """
    client = _get_client(ctx)
    try:
        result = await client.list_investigations(
            workspace_id,
            status=status,
            insight_id=insight_id,
        )
        investigations = result.get("data", [])
        if not investigations:
            return f"Aucune investigation pour le workspace `{workspace_id}`."
        lines = [
            f"**{len(investigations)} investigation(s) dans le workspace `{workspace_id}` :**\n"
        ]
        for inv in investigations:
            inv_status = inv.get("status", "?")
            lines.append(
                f"- **{inv.get('title', 'Investigation')}** (id: `{inv['id']}`) "
                f"— {inv_status}"
            )
        return "\n".join(lines)
    except VaultAPIError as e:
        return f"Erreur : {e.message}"
