"""XAIS Vault MCP Server — entry point."""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

from .client import VaultClient  # noqa: E402


@asynccontextmanager
async def lifespan(server):
    """Initialise le client httpx au démarrage, le ferme à l'arrêt."""
    api_url = os.environ.get("XAIS_VAULT_API_URL", "http://localhost:8000")
    api_key = os.environ.get("XAIS_VAULT_API_KEY")
    if not api_key:
        raise RuntimeError("XAIS_VAULT_API_KEY is required")

    async with VaultClient(base_url=api_url, api_key=api_key) as client:
        server.state["client"] = client
        yield


mcp = FastMCP(
    "XAIS Vault",
    instructions="AI-powered document intelligence platform (workspaces + insights)",
    lifespan=lifespan,
)

# Import des tools pour déclencher l'enregistrement des @mcp.tool
from . import tools  # noqa: F401, E402


def main():
    """CLI entry point."""
    mcp.run()
