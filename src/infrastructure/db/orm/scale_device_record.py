from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DECIMAL, DateTime, Index, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class ScaleDeviceRecordORM(Base):
    __tablename__ = "scale_device_records"
    __table_args__ = (
        Index("ix_scale_device_records_tenant_batch", "tenant_id", "batch_id"),
        Index("ix_scale_device_records_tenant_status", "tenant_id", "status"),
        Index("ix_scale_device_records_device_record", "device_id", "device_record_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    device_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    device_record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    peso: Mapped[str] = mapped_column(DECIMAL(12, 3), nullable=False)
    fecha: Mapped[str] = mapped_column(String(10), nullable=False)
    hora: Mapped[str] = mapped_column(String(8), nullable=False)
    turno: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    matched_animal_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    milk_production_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    batch_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
