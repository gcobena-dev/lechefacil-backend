from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DECIMAL, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class TenantConfigORM(Base):
    __tablename__ = "tenant_configs"

    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    default_buyer_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    default_density: Mapped[str] = mapped_column(DECIMAL(4, 2), nullable=False, default="1.03")
    default_delivery_input_unit: Mapped[str] = mapped_column(String(8), nullable=False, default="l")
    default_production_input_unit: Mapped[str] = mapped_column(String(8), nullable=False, default="lb")
    default_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    default_price_per_l: Mapped[str | None] = mapped_column(DECIMAL(10, 4), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
