from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class SireCatalogORM(Base):
    __tablename__ = "sire_catalog"
    __table_args__ = (
        Index(
            "ux_sire_catalog_tenant_registry",
            "tenant_id",
            "registry_code",
            unique=True,
            postgresql_where="registry_code IS NOT NULL AND deleted_at IS NULL",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    registry_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    registry_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    breed_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    animal_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    genetic_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
