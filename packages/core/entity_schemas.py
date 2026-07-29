"""Schemas Pydantic pour le knowledge graph (entités + relations)."""

from pydantic import BaseModel, Field, field_validator

# ─── Types valides ────────────────────────────────────────────

ENTITY_TYPES = {"company", "person", "metric", "clause", "date", "amount"}
RELATION_TYPES = {
    "détient", "emploie", "référence", "contredit", "est_filiale_de",
    "a_signé", "concerne", "garantit", "finance", "dépend_de",
    "est_comparable_à", "autre",
}


# ─── Extraction LLM (output structuré) ───────────────────────


class ExtractedEntity(BaseModel):
    """Entité extraite d'un chunk par le LLM."""

    name: str = Field(..., min_length=1, max_length=500)
    type: str
    description: str = ""

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        return v if v in ENTITY_TYPES else "company"

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class ExtractedRelation(BaseModel):
    """Relation extraite entre deux entités nommées."""

    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    type: str
    description: str = ""

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        return v if v in RELATION_TYPES else "autre"


class ExtractionResult(BaseModel):
    """Résultat complet d'une extraction d'entités sur un batch de chunks."""

    entities: list[ExtractedEntity] = Field(default_factory=list)
    relations: list[ExtractedRelation] = Field(default_factory=list)


# ─── API response models ─────────────────────────────────────


class EntityResponse(BaseModel):
    """Entité retournée par l'API."""

    id: str
    workspace_id: str
    name: str
    entity_type: str
    description: str | None
    properties: dict = Field(default_factory=dict)
    mention_count: int = 0
    created_at: str


class EntityRelationResponse(BaseModel):
    """Relation retournée par l'API."""

    id: str
    source_entity_id: str
    source_entity_name: str
    target_entity_id: str
    target_entity_name: str
    relation_type: str
    description: str | None
    confidence: float
    created_at: str


class EntityStats(BaseModel):
    """Statistiques du knowledge graph pour un workspace."""

    total_entities: int
    total_relations: int
    entities_by_type: dict[str, int] = Field(default_factory=dict)
