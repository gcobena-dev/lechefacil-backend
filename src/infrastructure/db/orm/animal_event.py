from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.infrastructure.db.base import Base


class AnimalEventORM(Base):
    __tablename__ = "animal_events"
    __table_args__ = (
        Index("ix_animal_events_tenant_animal_occurred", "tenant_id", "animal_id", "occurred_at"),
        Index("ix_animal_events_tenant_type", "tenant_id", "type"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    animal_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    # Types: BIRTH, CALVING, DRY_OFF, SALE, DEATH, CULL,
    # SERVICE, EMBRYO_TRANSFER, ABORTION, TRANSFER
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    parent_event_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    new_status_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
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
