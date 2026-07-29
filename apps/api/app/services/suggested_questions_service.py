"""
Suggested Questions Service — aggregation of pre-computed questions across sources.

Each source stores `suggested_questions TEXT[]` (5-8 questions generated during indexing).
This service aggregates them across all ready sources of a workspace, dedupes case-insensitive,
and returns a bounded list as exploration entry points in the Studio.
"""

from packages.db.client import safe_get_list


async def get_workspace_suggested_questions(
    db,
    workspace_id: str,
    organization_id: str,
    limit: int = 8,
) -> list[dict]:
    """Aggregate and dedupe suggested questions across a workspace's ready sources.

    Args:
        db: Supabase client.
        workspace_id: Workspace UUID.
        organization_id: Organization UUID (defense in depth, filtered in addition to RLS).
        limit: Max number of questions to return (default 8, caller should clamp 1-20).

    Returns:
        List of dicts with keys: question, source_id, source_name.
        Questions are dedupe'd case-insensitive (trimmed + lower-cased key).
        Empty strings and whitespace-only entries are ignored.
        Order follows the order of sources returned by the query; within a source,
        question order is preserved.
    """
    result = (
        db.table("sources")
        .select("id, name, suggested_questions")
        .eq("workspace_id", workspace_id)
        .eq("organization_id", organization_id)
        .eq("status", "ready")
        .execute()
    )
    sources = safe_get_list(result)

    seen: set[str] = set()
    aggregated: list[dict] = []
    for src in sources:
        questions = src.get("suggested_questions") or []
        for q in questions:
            if not isinstance(q, str):
                continue
            q_clean = q.strip()
            key = q_clean.lower()
            if not key or key in seen:
                continue
            seen.add(key)
            aggregated.append(
                {
                    "question": q_clean,
                    "source_id": src["id"],
                    "source_name": src["name"],
                }
            )
            if len(aggregated) >= limit:
                return aggregated

    return aggregated
