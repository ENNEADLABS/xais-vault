"""MCP tools package — réexporte les fonctions pour usage direct (tests + API publique)."""

from .tools_chat import chat
from .tools_deliverables import generate_deliverable
from .tools_insights import (
    investigate_insight,
    list_insights,
    list_investigations,
)
from .tools_sources import list_sources, upload_text_source
from .tools_workspaces import create_workspace, get_workspace, list_workspaces

__all__ = [
    "chat",
    "create_workspace",
    "generate_deliverable",
    "get_workspace",
    "investigate_insight",
    "list_insights",
    "list_investigations",
    "list_sources",
    "list_workspaces",
    "upload_text_source",
]
