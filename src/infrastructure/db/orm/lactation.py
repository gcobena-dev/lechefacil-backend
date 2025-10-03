from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, Index, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class LactationORM(Base):
    __tablename__ = "lactations"
    __table_args__ = (
        Index("ix_lactations_tenant_animal", "tenant_id", "animal_id"),
        Index("ix_lactations_tenant_status", "tenant_id", "status"),
        Index("ix_lactations_tenant_animal_number", "tenant_id", "animal_id", "number"),
        # Partial unique index for ensuring one open lactation per animal
        # Will be created in migration as: CREATE UNIQUE INDEX ix_lactations_one_open_per_animal
        # ON lactations (tenant_id, animal_id) WHERE status = 'open';
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    animal_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)  # lactation number (1, 2, 3...)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="open"
    )  # 'open' | 'closed'
    calving_event_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
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
