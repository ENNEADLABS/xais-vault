"""
Researcher helpers — doc search, web search, prompt building, result storage.

Extracted from researcher.py for the 200-line-per-file rule.
"""

import logging
import os
from datetime import datetime, timezone

from tavily import TavilyClient

logger = logging.getLogger(__name__)


async def search_workspace_documents(
    supabase,
    embedder,
    query: str,
    workspace_id: str,
    match_count: int = 15,
    similarity_threshold: float = 0.3,
) -> list[dict]:
    """Recherche hybrid (vector + full-text) + reranking RRF."""
    from apps.api.app.services.chat_reranker import rerank_rrf

    query_embedding = await embedder.embed_query(query, dimensions=1536)

    result = supabase.rpc(
        "search_chunks_hybrid",
        {
            "query_embedding": query_embedding,
            "query_text": query,
            "target_workspace_id": workspace_id,
            "match_count": 50,  # Over-fetch pour le reranking
            "similarity_threshold": similarity_threshold,
            "vector_weight": 0.7,
        },
    ).execute()

    chunks = result.data or []
    if chunks:
        chunks = rerank_rrf(chunks, top_k=match_count)

    if chunks:
        source_ids = list({c["source_id"] for c in chunks})
        sources_result = (
            supabase.table("sources")
            .select("id, name, type")
            .in_("id", source_ids)
            .execute()
        )
        source_map = {s["id"]: s for s in (sources_result.data or [])}

        for chunk in chunks:
            source = source_map.get(chunk["source_id"], {})
            chunk["source_name"] = source.get("name", "Document inconnu")
            chunk["source_type"] = source.get("type", "?")

    return chunks


async def search_web(
    query: str,
    *,
    max_results: int = 5,
    search_depth: str = "advanced",
) -> list[dict]:
    """Recherche web via Tavily. Retourne [] si la clé API est absente ou en cas d'erreur."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        logger.warning("TAVILY_API_KEY not set, skipping web search")
        return []

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,
            include_raw_content=False,
        )

        return [
            {
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "snippet": (r.get("content") or "")[:500],
                "accessed_at": datetime.now(timezone.utc).isoformat(),
            }
            for r in response.get("results", [])
        ]

    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return []


def build_web_query(question: str, insight: dict | None) -> str:
    """Construit une query Tavily optimisée depuis la question et le insight."""
    parts = [question]
    if insight:
        title = insight.get("title", "")
        if title and title.lower() not in question.lower():
            parts.append(title)
    return " ".join(parts)[:400]


def build_research_prompt(
    question: str,
    insight: dict | None,
    doc_chunks: list[dict],
    web_results: list[dict],
) -> str:
    """Assemble le prompt complet pour Claude : question + insight + docs + web."""
    parts: list[str] = [f"QUESTION D'INVESTIGATION :\n{question}"]

    if insight:
        block = (
            "╔═══════════════════════════════════════╗\n"
            "║       INSIGHT DE RÉFÉRENCE            ║\n"
            "╚═══════════════════════════════════════╝\n"
            f"Titre       : {insight.get('title', '')}\n"
            f"Type        : {insight.get('type', '')}\n"
            f"Sévérité    : {insight.get('severity', '')}\n"
            f"Description : {insight.get('description', '')}\n"
        )
        if insight.get("source_quote"):
            block += f'Extrait cité : "{insight["source_quote"]}"\n'
        parts.append(block)

    if doc_chunks:
        parts.append(
            "═══════════════════════════════════════\n"
            f"PASSAGES DOCUMENTAIRES ({len(doc_chunks)} résultats)\n"
            "═══════════════════════════════════════"
        )
        for i, chunk in enumerate(doc_chunks, 1):
            page = chunk.get("page_number")
            page_str = f", p.{page}" if page else ""
            section = chunk.get("section_title")
            section_str = f" — {section}" if section else ""
            sim = chunk.get("similarity", 0)
            parts.append(
                f"[{i}] {chunk.get('source_name', '?')}{page_str}{section_str} "
                f"(similarité: {sim:.0%})\n{chunk.get('content', '')}"
            )
    else:
        parts.append(
            "PASSAGES DOCUMENTAIRES : Aucun passage pertinent trouvé dans les documents."
        )

    if web_results:
        parts.append(
            "═══════════════════════════════════════\n"
            f"RÉSULTATS WEB ({len(web_results)} sources)\n"
            "═══════════════════════════════════════"
        )
        for i, r in enumerate(web_results, 1):
            parts.append(f"[Web {i}] {r['title']}\nURL: {r['url']}\n{r['snippet']}")
    else:
        parts.append(
            "RÉSULTATS WEB : Aucune recherche web effectuée ou aucun résultat."
        )

    parts.append(
        "\n═══════════════════════════════════════\n"
        "Produis le rapport d'investigation au format Markdown.\n"
        "═══════════════════════════════════════"
    )

    return "\n\n".join(parts)


async def store_investigation_result(
    supabase,
    *,
    investigation_id: str,
    report: str,
    doc_references: list[dict],
    web_sources: list[dict],
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    model_used: str,
) -> None:
    """Met à jour l'investigation avec le rapport, les sources et le statut completed."""
    db_doc_refs = [
        {
            "source_id": c.get("source_id"),
            "page": c.get("page_number"),
            "section": c.get("section_title"),
            "quote": (c.get("content") or "")[:300],
        }
        for c in doc_references
    ]

    supabase.table("investigations").update(
        {
            "status": "completed",
            "report": report,
            "web_sources": web_sources,
            "doc_references": db_doc_refs,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": float(cost_usd),
            "model_used": model_used,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", investigation_id).execute()
