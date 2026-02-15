from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class InseminationORM(Base):
    __tablename__ = "inseminations"
    __table_args__ = (
        Index(
            "ix_inseminations_tenant_animal_date",
            "tenant_id",
            "animal_id",
            "service_date",
        ),
        Index(
            "ix_inseminations_tenant_sire",
            "tenant_id",
            "sire_catalog_id",
        ),
        Index(
            "ix_inseminations_pending",
            "tenant_id",
            "pregnancy_status",
            "service_date",
            postgresql_where="pregnancy_status = 'PENDING' AND deleted_at IS NULL",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    animal_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("animals.id"),
        nullable=False,
    )
    sire_catalog_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sire_catalog.id"),
        nullable=True,
    )
    semen_inventory_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("semen_inventory.id"),
        nullable=True,
    )
    service_event_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("animal_events.id"),
        nullable=True,
    )
    service_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    technician: Mapped[str | None] = mapped_column(String(255), nullable=True)
    straw_count: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    heat_detected: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    protocol: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pregnancy_status: Mapped[str] = mapped_column(
        String(16), server_default="'PENDING'", nullable=False
    )
    pregnancy_check_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pregnancy_checked_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expected_calving_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    calving_event_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("animal_events.id"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
