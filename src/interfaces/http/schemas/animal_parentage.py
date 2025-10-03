from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnimalParentageCreate(BaseModel):
    """Schema for creating parentage records."""

    child_id: UUID
    relation: str = Field(..., description="Relation type: DAM, SIRE, RECIPIENT, DONOR")
    parent_animal_id: UUID | None = None  # Local parent (if exists in system)
    external_code: str | None = None  # External parent code
    external_registry: str | None = None  # Registry name
    source: str = "manual"  # 'manual' | 'event' | 'import'
    effective_from: date | None = None
    data: dict | None = None

    @field_validator("relation")
    def validate_relation(cls, v):
        valid_relations = {"DAM", "SIRE", "RECIPIENT", "DONOR"}
        if v not in valid_relations:
            raise ValueError(f"Invalid relation. Must be one of: {', '.join(valid_relations)}")
        return v

    @field_validator("source")
    def validate_source(cls, v):
        valid_sources = {"manual", "event", "import"}
        if v not in valid_sources:
            raise ValueError(f"Invalid source. Must be one of: {', '.join(valid_sources)}")
        return v


class AnimalParentageUpdate(BaseModel):
    """Schema for updating parentage records."""

    version: int
    parent_animal_id: UUID | None = None
    external_code: str | None = None
    external_registry: str | None = None
    effective_from: date | None = None
    data: dict | None = None


class AnimalParentageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    child_id: UUID
    relation: str
    parent_animal_id: UUID | None
    external_code: str | None
    external_registry: str | None
    source: str
    effective_from: date | None
    data: dict | None
    created_at: datetime
    updated_at: datetime
    version: int

    # Enriched fields (optional, populated by queries)
    parent_tag: str | None = None
    parent_name: str | None = None


class AnimalParentageListResponse(BaseModel):
    items: list[AnimalParentageResponse]


class AnimalPedigreeResponse(BaseModel):
    """Complete pedigree information for an animal."""

    animal_id: UUID
    animal_tag: str
    dam: AnimalParentageResponse | None = None
    sire: AnimalParentageResponse | None = None
    maternal_grandam: AnimalParentageResponse | None = None
    maternal_grandsire: AnimalParentageResponse | None = None
    paternal_grandam: AnimalParentageResponse | None = None
    paternal_grandsire: AnimalParentageResponse | None = None
