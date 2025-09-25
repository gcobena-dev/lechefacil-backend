from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import DECIMAL, Date, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class MilkDeliveryORM(Base):
    __tablename__ = "milk_deliveries"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    buyer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    date_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    volume_l: Mapped[str] = mapped_column(DECIMAL(12, 3), nullable=False)
    price_snapshot: Mapped[str] = mapped_column(DECIMAL(10, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    amount: Mapped[str] = mapped_column(DECIMAL(12, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    version: Mapped[int] = mapped_column(nullable=False, default=1)
