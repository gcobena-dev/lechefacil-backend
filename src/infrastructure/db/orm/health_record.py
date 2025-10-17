from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class HealthRecordORM(Base):
    __tablename__ = "health_records"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "animal_id"],
            ["animals.tenant_id", "animals.id"],
            name="fk_health_records_animal",
        ),
        Index(
            "idx_health_records_tenant_animal",
            "tenant_id",
            "animal_id",
            "occurred_at",
            postgresql_where="deleted_at IS NULL",
        ),
        Index(
            "idx_health_records_next_doses",
            "tenant_id",
            "next_dose_date",
            postgresql_where="next_dose_date IS NOT NULL AND "
            "event_type = 'VACCINATION' AND deleted_at IS NULL",
        ),
        Index(
            "idx_health_records_withdrawals",
            "tenant_id",
            "withdrawal_until",
            postgresql_where="withdrawal_until IS NOT NULL AND deleted_at IS NULL",
        ),
        Index(
            "idx_health_records_event_type",
            "tenant_id",
            "event_type",
            "occurred_at",
            postgresql_where="deleted_at IS NULL",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    animal_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Common fields
    veterinarian: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Vaccination fields
    vaccine_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    next_dose_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Treatment fields
    medication: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    withdrawal_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    withdrawal_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Note: Attachments are in the 'attachments' table with
    # owner_type='HEALTH_EVENT' and owner_id=this.id

    # Audit fields
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
