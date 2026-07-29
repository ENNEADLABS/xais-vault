"""MCP tools — workspace management (list, get, create)."""

from ..client import VaultAPIError, VaultClient
from ..server import mcp


def _get_client(ctx) -> VaultClient:
    """Extrait le VaultClient depuis le contexte MCP."""
    return ctx.state["client"]


@mcp.tool()
async def list_workspaces(ctx, status: str | None = None) -> str:
    """Liste les workspaces de l'organisation.

    Args:
        status: Filtre optionnel — "active", "archived" ou "closed"
    """
    client = _get_client(ctx)
    try:
        result = await client.list_workspaces(status=status)
        workspaces = result.get("data", [])
        if not workspaces:
            return "Aucun workspace trouvé."
        lines = []
        for d in workspaces:
            lines.append(
                f"- **{d.get('emoji', '📁')} {d['name']}** (id: `{d['id']}`) — "
                f"{d['status']}, {d.get('source_count', 0)} sources, "
                f"{d.get('insight_count', 0)} insights"
            )
        return "\n".join(lines)
    except VaultAPIError as e:
        return f"Erreur : {e.message}"


@mcp.tool()
async def get_workspace(ctx, workspace_id: str) -> str:
    """Détail d'un workspace avec nombre de sources et insights.

    Args:
        workspace_id: L'identifiant UUID du workspace
    """
    client = _get_client(ctx)
    try:
        result = await client.get_workspace(workspace_id)
        d = result.get("data", {})
        return (
            f"# {d.get('emoji', '📁')} {d['name']}\n\n"
            f"- **ID** : `{d['id']}`\n"
            f"- **Statut** : {d['status']}\n"
            f"- **Type** : {d.get('deal_type', 'N/A')}\n"
            f"- **Secteur** : {d.get('sector', 'N/A')}\n"
            f"- **Cible** : {d.get('target_company', 'N/A')}\n"
            f"- **Sources** : {d.get('source_count', 0)}\n"
            f"- **Insights** : {d.get('insight_count', 0)}\n"
            f"- **Scan** : {d.get('scan_status', 'N/A')}\n"
            f"- **Créé le** : {d['created_at']}\n"
        )
    except VaultAPIError as e:
        return f"Erreur : {e.message}"


@mcp.tool()
async def create_workspace(
    ctx,
    name: str,
    description: str | None = None,
    deal_type: str | None = None,
    sector: str | None = None,
    target_company: str | None = None,
    emoji: str | None = None,
) -> str:
    """Créer un nouveau workspace (workspace d'analyse).

    Args:
        name: Nom du workspace (obligatoire)
        description: Description libre
        deal_type: Type — equity, debt, ma, restructuring, other
        sector: Secteur d'activité
        target_company: Nom de la société cible
        emoji: Emoji du workspace (défaut : 📁)
    """
    client = _get_client(ctx)
    kwargs = {}
    if description:
        kwargs["description"] = description
    if deal_type:
        kwargs["deal_type"] = deal_type
    if sector:
        kwargs["sector"] = sector
    if target_company:
        kwargs["target_company"] = target_company
    if emoji:
        kwargs["emoji"] = emoji
    try:
        result = await client.create_workspace(name, **kwargs)
        d = result.get("data", {})
        return (
            f"Workspace créé : **{d.get('emoji', '📁')} {d['name']}** (id: `{d['id']}`)\n"
            f"Statut : {d.get('status', 'active')}"
        )
    except VaultAPIError as e:
        return f"Erreur : {e.message}"
