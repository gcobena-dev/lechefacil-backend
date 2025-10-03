from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnimalCertificateBase(BaseModel):
    """Base schema for animal certificates."""

    registry_number: str | None = None
    bolus_id: str | None = None
    tattoo_left: str | None = None
    tattoo_right: str | None = None
    issue_date: date | None = None
    breeder: str | None = None
    owner: str | None = None
    farm: str | None = None
    certificate_name: str | None = None
    association_code: str | None = None
    notes: str | None = None
    data: dict | None = None


class AnimalCertificateCreate(AnimalCertificateBase):
    """Schema for creating a certificate."""

    animal_id: UUID


class AnimalCertificateUpdate(BaseModel):
    """Schema for updating a certificate."""

    version: int
    registry_number: str | None = None
    bolus_id: str | None = None
    tattoo_left: str | None = None
    tattoo_right: str | None = None
    issue_date: date | None = None
    breeder: str | None = None
    owner: str | None = None
    farm: str | None = None
    certificate_name: str | None = None
    association_code: str | None = None
    notes: str | None = None
    data: dict | None = None


class AnimalCertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    animal_id: UUID
    registry_number: str | None
    bolus_id: str | None
    tattoo_left: str | None
    tattoo_right: str | None
    issue_date: date | None
    breeder: str | None
    owner: str | None
    farm: str | None
    certificate_name: str | None
    association_code: str | None
    notes: str | None
    data: dict | None
    created_at: datetime
    updated_at: datetime
    version: int

    # Enriched fields (optional)
    animal_tag: str | None = None
    animal_name: str | None = None


class CertificateAttachmentInfo(BaseModel):
    """Information about certificate image attachments."""

    certificate_id: UUID
    images: list[str] = []  # URLs to certificate images
    documents: list[str] = []  # URLs to additional documents
