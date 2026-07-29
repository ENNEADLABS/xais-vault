# XAIS Vault MCP Server

Serveur MCP qui expose l'API XAIS Vault comme des tools pour Claude Code.

## Prérequis

- Python 3.12+
- Une API key XAIS Vault (créée dans Settings > API Keys)

## Installation

### 1. Variables d'environnement

Créer un fichier `.env` dans `packages/mcp-server/` :

```env
XAIS_VAULT_API_URL=http://localhost:8000
XAIS_VAULT_API_KEY=xv_live_votre_cle_ici
```

### 2. Configuration Claude Code

Ajouter dans `~/.claude/claude_desktop_config.json` (ou `~/.claude.json`) :

```json
{
  "mcpServers": {
    "xais-vault": {
      "command": "uv",
      "args": ["run", "--directory", "/chemin/vers/packages/mcp-server", "xais-vault-mcp"],
      "env": {
        "XAIS_VAULT_API_URL": "http://localhost:8000",
        "XAIS_VAULT_API_KEY": "xv_live_votre_cle_ici"
      }
    }
  }
}
```

## Tools disponibles

| Tool | Description |
|------|-------------|
| `list_workspaces` | Liste les workspaces de l'org (filtre par status) |
| `get_workspace` | Détail complet d'un workspace |
| `create_workspace` | Créer un nouveau workspace |
| `list_sources` | Sources (documents) d'un workspace |
| `upload_text_source` | Ajouter du texte comme source (indexation async) |
| `chat` | Question RAG sur les documents d'un workspace |
| `list_insights` | Insights d'un workspace (filtrables) |
| `investigate_insight` | Lancer une investigation sur un insight (async) |
| `list_investigations` | Investigations d'un workspace |
| `generate_deliverable` | Générer un livrable DOCX (executive_summary, investment_memo, dd_report) |

## Tests

```bash
cd packages/mcp-server
uv run pytest tests/ -v
```

## Architecture

Le MCP server est un **client HTTP pur** — il délègue tout à l'API REST via httpx.
Cela garantit que l'auth, le RLS, le rate limiting et les validations s'appliquent identiquement.

Le chat utilise SSE côté API, mais le client consomme le stream et retourne une réponse complète
(texte + citations + usage) au tool MCP — pas de streaming dans les tools MCP.
