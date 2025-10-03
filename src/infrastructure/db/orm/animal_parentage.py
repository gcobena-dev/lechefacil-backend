from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, Index, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.infrastructure.db.base import Base


class AnimalParentageORM(Base):
    __tablename__ = "animal_parentage"
    __table_args__ = (
        Index("ix_animal_parentage_tenant_child", "tenant_id", "child_id"),
        Index("ix_animal_parentage_tenant_relation", "tenant_id", "relation"),
        Index("ix_animal_parentage_tenant_external_code", "tenant_id", "external_code"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    child_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    relation: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # 'DAM' | 'SIRE' | 'RECIPIENT' | 'DONOR'
    parent_animal_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )  # local animal
    external_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    external_registry: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)  # 'manual' | 'event' | 'import'
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
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
