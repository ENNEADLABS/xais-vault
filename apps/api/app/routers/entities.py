"""Router entités — CRUD knowledge graph par workspace."""

from fastapi import APIRouter, Path, Query

from packages.core.entity_schemas import (
    EntityRelationResponse,
    EntityResponse,
    EntityStats,
)
from packages.db.client import safe_get_list

from ..dependencies import DB, Auth

router = APIRouter()


@router.get("", response_model=list[EntityResponse])
async def list_entities(
    auth: Auth,
    db: DB,
    workspace_id: str = Path(...),
    entity_type: str | None = Query(None),
    limit: int = Query(200, ge=1, le=500),
):
    """Liste les entités du knowledge graph pour un workspace."""
    query = (
        db.table("entities")
        .select("id, workspace_id, name, entity_type, description, properties, created_at")
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .order("name")
        .limit(limit)
    )

    if entity_type:
        query = query.eq("entity_type", entity_type)

    entities = safe_get_list(query.execute())

    # Enrichir avec le mention_count depuis chunk_entities
    entity_ids = [e["id"] for e in entities]
    mention_counts: dict[str, int] = {}

    if entity_ids:
        ce_result = (
            db.rpc("get_entity_mention_counts", {"entity_ids": entity_ids})
            .execute()
        )
        for row in safe_get_list(ce_result):
            mention_counts[row["entity_id"]] = row["total_mentions"]

    return [
        EntityResponse(
            id=e["id"],
            workspace_id=e["workspace_id"],
            name=e["name"],
            entity_type=e["entity_type"],
            description=e.get("description"),
            properties=e.get("properties") or {},
            mention_count=mention_counts.get(e["id"], 0),
            created_at=e["created_at"],
        )
        for e in entities
    ]


@router.get("/relations", response_model=list[EntityRelationResponse])
async def list_relations(
    auth: Auth,
    db: DB,
    workspace_id: str = Path(...),
    limit: int = Query(200, ge=1, le=500),
):
    """Liste les relations entre entités pour un workspace."""
    result = (
        db.table("entity_relations")
        .select(
            "id, source_entity_id, target_entity_id, "
            "relation_type, description, confidence, created_at"
        )
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    relations = safe_get_list(result)
    if not relations:
        return []

    # Récupérer les noms des entités
    entity_ids = set()
    for r in relations:
        entity_ids.add(r["source_entity_id"])
        entity_ids.add(r["target_entity_id"])

    names_result = (
        db.table("entities")
        .select("id, name")
        .in_("id", list(entity_ids))
        .execute()
    )
    name_map = {e["id"]: e["name"] for e in safe_get_list(names_result)}

    return [
        EntityRelationResponse(
            id=r["id"],
            source_entity_id=r["source_entity_id"],
            source_entity_name=name_map.get(r["source_entity_id"], "?"),
            target_entity_id=r["target_entity_id"],
            target_entity_name=name_map.get(r["target_entity_id"], "?"),
            relation_type=r["relation_type"],
            description=r.get("description"),
            confidence=r.get("confidence", 1.0),
            created_at=r["created_at"],
        )
        for r in relations
    ]


@router.get("/stats", response_model=EntityStats)
async def get_entity_stats(
    auth: Auth,
    db: DB,
    workspace_id: str = Path(...),
):
    """Statistiques du knowledge graph pour un workspace."""
    entities_result = (
        db.table("entities")
        .select("entity_type", count="exact")
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute()
    )
    total_entities = entities_result.count or 0

    relations_result = (
        db.table("entity_relations")
        .select("id", count="exact")
        .eq("workspace_id", workspace_id)
        .eq("organization_id", auth.organization_id)
        .execute()
    )
    total_relations = relations_result.count or 0

    # Compter par type
    entities_by_type: dict[str, int] = {}
    for e in safe_get_list(entities_result):
        t = e["entity_type"]
        entities_by_type[t] = entities_by_type.get(t, 0) + 1

    return EntityStats(
        total_entities=total_entities,
        total_relations=total_relations,
        entities_by_type=entities_by_type,
    )
