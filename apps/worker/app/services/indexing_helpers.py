"""
Indexing helpers — download, embed, summarize, store, auto-scan trigger.

Extracted from indexing.py for the 200-line-per-file rule.
"""

import json
import logging
import os
import tempfile
from pathlib import Path

from packages.db.client import safe_get_list, safe_get_one
from packages.db.job_queue import create_job
from packages.llm.factory import get_embedder, get_llm

from .chunking import Chunk

logger = logging.getLogger(__name__)

# Feature flag — désactivé par défaut (Studio v2 : l'utilisateur lance le scan manuellement)
AUTO_SCAN_ENABLED = os.getenv("AUTO_SCAN_ENABLED", "false").lower() == "true"

EMBEDDING_BATCH_SIZE = 50

SUMMARY_SYSTEM_PROMPT = (
    Path(__file__).parent.parent / "prompts" / "summary_system.txt"
).read_text()


async def download_file(supabase, storage_path: str) -> str:
    """Download a file from Supabase Storage to a temp file."""
    bucket = "sources"
    response = supabase.storage.from_(bucket).download(storage_path)

    ext = os.path.splitext(storage_path)[1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    tmp.write(response)
    tmp.close()

    logger.info(f"Downloaded {storage_path} → {tmp.name}")
    return tmp.name


async def embed_chunks(chunks: list[Chunk]) -> tuple[list[list[float]], float]:
    """Embed all chunks using Gemini Embedding 2.

    Returns (embeddings, total_cost_usd).
    """
    embedder = get_embedder()
    all_embeddings: list[list[float]] = []
    total_cost = 0.0

    texts = [c.content for c in chunks]

    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i : i + EMBEDDING_BATCH_SIZE]
        response = await embedder.embed(
            batch,
            dimensions=1536,
            task_type="RETRIEVAL_DOCUMENT",
        )
        all_embeddings.extend(response.embeddings)
        total_cost += response.usage.cost_usd

    return all_embeddings, total_cost


async def generate_summary(text: str, max_retries: int = 2) -> tuple[dict, float]:
    """Generate summary, topics, and suggested questions via Claude.

    Utilise le pattern retry-with-feedback : si le JSON est invalide ou
    incomplet, on re-prompt avec les erreurs de validation spécifiques.
    Max 2 retries (3 tentatives total).

    Returns (summary_dict, total_cost_usd).
    """
    llm = get_llm()

    max_chars = 100_000
    truncated = text[:max_chars]
    if len(text) > max_chars:
        truncated += "\n\n[... document tronqué pour le résumé ...]"

    base_prompt = f"""Analyse ce document et génère le JSON demandé.

DOCUMENT:
{truncated}"""

    total_cost = 0.0
    errors: list[dict] = []

    for attempt in range(max_retries + 1):
        prompt = base_prompt
        if errors:
            prompt += _format_retry_feedback(errors)

        response = await llm.generate(
            prompt,
            system=SUMMARY_SYSTEM_PROMPT,
            max_tokens=2048,
            temperature=0.1,
            json_mode=True,
        )
        total_cost += response.usage.cost_usd

        validation_errors = _validate_summary(response.content)
        if not validation_errors:
            return json.loads(response.content), total_cost

        error_info = {
            "attempt": attempt + 1,
            "errors": validation_errors,
        }
        errors.append(error_info)
        logger.warning(f"Summary attempt {attempt + 1} failed: {validation_errors}")

        # Même erreur 2 fois de suite → abandonner, le modèle ne sait pas faire
        if len(errors) >= 2 and errors[-1]["errors"] == errors[-2]["errors"]:
            logger.warning("Same errors repeated, stopping retries")
            break

    # Fallback : extraire ce qu'on peut du dernier résultat
    logger.warning(
        f"Summary generation failed after {len(errors)} attempts, using fallback"
    )
    try:
        partial = json.loads(response.content)
    except json.JSONDecodeError:
        partial = {}

    return {
        "summary": partial.get("summary", response.content[:500]),
        "topics": partial.get("topics", []),
        "suggested_questions": partial.get("suggested_questions", []),
    }, total_cost


def _validate_summary(content: str) -> list[str]:
    """Valide le JSON de summary et retourne les erreurs trouvées."""
    errors = []
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return [f"JSON invalide : {e}"]

    if not isinstance(data, dict):
        return ["Résultat n'est pas un objet JSON"]

    # Champ summary : requis, minimum 50 caractères
    summary = data.get("summary")
    if not summary:
        errors.append("Champ 'summary' manquant ou vide")
    elif not isinstance(summary, str):
        errors.append(f"Champ 'summary' : attendu str, reçu {type(summary).__name__}")
    elif len(summary) < 50:
        errors.append(f"Champ 'summary' trop court ({len(summary)} chars, minimum 50)")

    # Champ topics : requis, list[str], 3-8 éléments
    topics = data.get("topics")
    if topics is None:
        errors.append("Champ 'topics' manquant")
    elif not isinstance(topics, list):
        errors.append(f"Champ 'topics' : attendu list, reçu {type(topics).__name__}")
    elif len(topics) < 1:
        errors.append("Champ 'topics' vide (minimum 1 topic)")

    # Champ suggested_questions : requis, list[str], 1-5 éléments
    questions = data.get("suggested_questions")
    if questions is None:
        errors.append("Champ 'suggested_questions' manquant")
    elif not isinstance(questions, list):
        errors.append(
            f"Champ 'suggested_questions' : attendu list, reçu {type(questions).__name__}"
        )
    elif len(questions) < 1:
        errors.append("Champ 'suggested_questions' vide (minimum 1 question)")

    return errors


def _format_retry_feedback(errors: list[dict]) -> str:
    """Formate les erreurs des tentatives précédentes pour guider le retry."""
    last = errors[-1]
    error_lines = "\n".join(f"- {e}" for e in last["errors"])
    return (
        f"\n\n---\nTentative {last['attempt']} échouée. "
        f"Erreurs de validation :\n{error_lines}\n"
        f"Corrige ces erreurs. Réponds UNIQUEMENT avec le JSON corrigé."
    )


async def store_chunks(
    supabase,
    *,
    chunks: list[Chunk],
    embeddings: list[list[float]],
    source_id: str,
    workspace_id: str,
    organization_id: str,
) -> None:
    """Insert chunks with embeddings into the chunks table."""
    supabase.table("chunks").delete().eq("source_id", source_id).execute()

    BATCH_SIZE = 100
    rows = [
        {
            "source_id": source_id,
            "workspace_id": workspace_id,
            "organization_id": organization_id,
            "content": chunk.content,
            "chunk_index": chunk.chunk_index,
            "token_count": chunk.token_count,
            "page_number": chunk.page_number,
            "section_title": chunk.section_title,
            "embedding": embedding,
            "metadata": {},
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        supabase.table("chunks").insert(batch).execute()

    logger.info(f"Stored {len(rows)} chunks for source {source_id}")


async def maybe_trigger_scan(supabase, *, workspace_id: str, organization_id: str) -> None:
    """Auto-trigger a scan_workspace job when ALL sources in the workspace are ready."""
    if not AUTO_SCAN_ENABLED:
        logger.info(f"Workspace {workspace_id}: auto-scan disabled (AUTO_SCAN_ENABLED=false)")
        return

    sources = safe_get_list(
        supabase.table("sources")
        .select("id, status")
        .eq("workspace_id", workspace_id)
        .eq("organization_id", organization_id)
        .execute()
    )

    if not sources:
        return

    not_ready = [s for s in sources if s["status"] in ("pending", "processing")]
    if not_ready:
        logger.info(
            f"Workspace {workspace_id}: {len(not_ready)}/{len(sources)} sources still processing, "
            f"skipping auto-scan"
        )
        return

    workspace_result = (
        supabase.table("workspaces").select("scan_status").eq("id", workspace_id).execute()
    )
    workspace = safe_get_one(workspace_result)
    if not workspace or workspace.get("scan_status") != "pending":
        logger.info(
            f"Workspace {workspace_id}: scan_status={workspace.get('scan_status') if workspace else '?'}, skipping auto-scan"
        )
        return

    existing_jobs = safe_get_list(
        supabase.table("jobs")
        .select("id")
        .eq("type", "scan_workspace")
        .in_("status", ["pending", "processing"])
        .eq("payload->>workspace_id", workspace_id)
        .execute()
    )

    if existing_jobs:
        logger.info(f"Workspace {workspace_id}: scan_workspace job already exists, skipping")
        return

    ready_count = len([s for s in sources if s["status"] == "ready"])
    logger.info(
        f"Workspace {workspace_id}: all {ready_count} sources ready — triggering auto-scan"
    )

    await create_job(
        supabase,
        type="scan_workspace",
        payload={"workspace_id": workspace_id, "organization_id": organization_id},
        organization_id=organization_id,
    )
