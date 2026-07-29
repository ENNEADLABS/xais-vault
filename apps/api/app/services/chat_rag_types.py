"""
Types partagés pour le pipeline RAG — évite les imports circulaires.
"""

from dataclasses import dataclass, field


@dataclass
class RagMetadata:
    """Métadonnées sur le contexte RAG injecté."""

    chunk_count: int
    source_count: int
    avg_similarity: float
    avg_fts_rank: float
    reranked: bool
    search_mode: str  # "hybrid" | "hybrid+graph" | "fulltext_fallback" | "no_results"
    tokens_used: int
    tokens_budget: int
    sources_used: list[dict]  # [{id, name, chunk_count}]
    entities_matched: int = 0
    graph_chunks_added: int = 0


@dataclass
class ChatContext:
    """Prepared RAG context for a chat query."""

    chunks: list[dict]
    prompt: str
    system_prompt: str
    source_map: dict[str, str] = field(default_factory=dict)
    rag_metadata: RagMetadata | None = None
