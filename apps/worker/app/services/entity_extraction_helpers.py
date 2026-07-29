"""
Helpers pour entity_extraction.py — stockage en DB des entités, relations et liens.

Extrait de entity_extraction.py pour respecter la limite de 200 lignes par fichier.
"""

import logging
import unicodedata

from packages.core.entity_schemas import ExtractedEntity, ExtractedRelation
from packages.db.client import safe_get_list

logger = logging.getLogger(__name__)


def normalize_entity_name(name: str) -> str:
    """Normalise un nom d'entité pour la déduplication."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    return ascii_only.lower().strip()


async def store_entities(
    supabase,
    *,
    entities: list[ExtractedEntity],
    embeddings: list[list[float]],
    workspace_id: str,
    organization_id: str,
) -> dict[str, str]:
    """Insert les entités et retourne un mapping nom_normalisé → entity_id."""
    entity_id_map: dict[str, str] = {}

    # Charger les entités existantes du workspace pour upsert
    existing = safe_get_list(
        supabase.table("entities")
        .select("id, name")
        .eq("workspace_id", workspace_id)
        .execute()
    )
    existing_map = {normalize_entity_name(e["name"]): e["id"] for e in existing}

    rows_to_insert = []
    for entity, embedding in zip(entities, embeddings):
        norm_name = normalize_entity_name(entity.name)
        if norm_name in existing_map:
            entity_id_map[norm_name] = existing_map[norm_name]
        else:
            row = {
                "workspace_id": workspace_id,
                "organization_id": organization_id,
                "name": entity.name,
                "entity_type": entity.type,
                "description": entity.description or None,
                "properties": {},
                "embedding": embedding,
            }
            rows_to_insert.append((norm_name, row))

    if rows_to_insert:
        for k in range(0, len(rows_to_insert), 100):
            batch = rows_to_insert[k : k + 100]
            result = supabase.table("entities").insert(
                [r[1] for r in batch]
            ).execute()
            if result.data:
                for (norm_name, _), row_data in zip(batch, result.data):
                    entity_id_map[norm_name] = row_data["id"]

    # Fusionner avec les existantes
    entity_id_map.update(
        {k: v for k, v in existing_map.items() if k not in entity_id_map}
    )

    return entity_id_map


async def store_relations(
    supabase,
    *,
    relations: list[ExtractedRelation],
    entity_id_map: dict[str, str],
    workspace_id: str,
    organization_id: str,
) -> int:
    """Insert les relations entre entités. Retourne le nombre inséré."""
    rows = []
    for rel in relations:
        source_id = entity_id_map.get(normalize_entity_name(rel.source))
        target_id = entity_id_map.get(normalize_entity_name(rel.target))
        if not source_id or not target_id:
            continue
        if source_id == target_id:
            continue

        rows.append({
            "workspace_id": workspace_id,
            "organization_id": organization_id,
            "source_entity_id": source_id,
            "target_entity_id": target_id,
            "relation_type": rel.type,
            "description": rel.description or None,
            "confidence": 1.0,
        })

    if rows:
        for k in range(0, len(rows), 100):
            batch = rows[k : k + 100]
            supabase.table("entity_relations").insert(batch).execute()

    return len(rows)


async def store_chunk_entities(
    supabase,
    *,
    chunk_entity_map: dict[str, list[str]],
    entity_id_map: dict[str, str],
) -> None:
    """Insert les liens chunk ↔ entité."""
    rows = []
    for chunk_id, entity_names in chunk_entity_map.items():
        seen_entity_ids: set[str] = set()
        for name in entity_names:
            entity_id = entity_id_map.get(normalize_entity_name(name))
            if entity_id and entity_id not in seen_entity_ids:
                seen_entity_ids.add(entity_id)
                rows.append({
                    "chunk_id": chunk_id,
                    "entity_id": entity_id,
                    "mention_count": 1,
                })

    if rows:
        for k in range(0, len(rows), 100):
            batch = rows[k : k + 100]
            supabase.table("chunk_entities").upsert(
                batch,
                on_conflict="chunk_id,entity_id",
            ).execute()
