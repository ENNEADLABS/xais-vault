"""MCP tools — source management (list, upload)."""

from ..client import VaultAPIError, VaultClient
from ..server import mcp


def _get_client(ctx) -> VaultClient:
    """Extrait le VaultClient depuis le contexte MCP."""
    return ctx.state["client"]


@mcp.tool()
async def list_sources(ctx, workspace_id: str) -> str:
    """Liste les sources (documents) d'un workspace.

    Args:
        workspace_id: L'identifiant UUID du workspace
    """
    client = _get_client(ctx)
    try:
        result = await client.list_sources(workspace_id)
        sources = result.get("data", [])
        if not sources:
            return f"Aucune source dans le workspace `{workspace_id}`."
        lines = [f"**{len(sources)} source(s) dans le workspace `{workspace_id}` :**\n"]
        for s in sources:
            status = s.get("status", "?")
            lines.append(
                f"- **{s['name']}** (id: `{s['id']}`) — {s.get('type', '?')}, {status}"
            )
        return "\n".join(lines)
    except VaultAPIError as e:
        return f"Erreur : {e.message}"


@mcp.tool()
async def upload_text_source(ctx, workspace_id: str, name: str, content: str) -> str:
    """Ajouter du texte comme source dans un workspace. L'indexation est asynchrone.

    Args:
        workspace_id: L'identifiant UUID du workspace
        name: Nom de la source (ex: "Term Sheet Q1 2025.txt")
        content: Contenu texte à indexer
    """
    client = _get_client(ctx)
    try:
        result = await client.upload_text_source(workspace_id, name, content)
        job_id = result.get("meta", {}).get("job_id", "?")
        src_id = result.get("data", {}).get("id", "?")
        return (
            f'Source **"{name}"** ajoutée au workspace `{workspace_id}`.\n'
            f"Indexation en cours (job: `{job_id}`, source: `{src_id}`)."
        )
    except VaultAPIError as e:
        return f"Erreur : {e.message}"
