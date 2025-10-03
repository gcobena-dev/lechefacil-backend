from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, Index, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.infrastructure.db.base import Base


class AnimalCertificateORM(Base):
    __tablename__ = "animal_certificates"
    __table_args__ = (
        Index("ix_animal_certificates_tenant_animal", "tenant_id", "animal_id"),
        Index("ix_animal_certificates_registry_number", "registry_number"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    animal_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, unique=True)

    # Certificate fields
    registry_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bolus_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tattoo_left: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tattoo_right: Mapped[str | None] = mapped_column(String(64), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    breeder: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    farm: Mapped[str | None] = mapped_column(String(255), nullable=True)
    certificate_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    association_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Additional data (e.g., awards, genetic info, etc.)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
