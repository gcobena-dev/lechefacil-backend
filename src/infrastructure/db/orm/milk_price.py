from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import DECIMAL, Date, DateTime, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class MilkPriceDailyORM(Base):
    __tablename__ = "milk_prices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "date", "buyer_id", name="ux_prices_tenant_date_buyer"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    price_per_l: Mapped[str] = mapped_column(DECIMAL(10, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    buyer_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    version: Mapped[int] = mapped_column(nullable=False, default=1)
