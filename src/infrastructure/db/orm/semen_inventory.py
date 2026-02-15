from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
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


class SemenInventoryORM(Base):
    __tablename__ = "semen_inventory"
    __table_args__ = (
        Index(
            "ix_semen_inventory_tenant_sire",
            "tenant_id",
            "sire_catalog_id",
        ),
        Index(
            "ix_semen_inventory_tenant_stock",
            "tenant_id",
            "current_quantity",
            postgresql_where="current_quantity > 0 AND deleted_at IS NULL",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    sire_catalog_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sire_catalog.id"),
        nullable=False,
    )
    batch_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tank_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    canister_position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    initial_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    current_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    supplier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cost_per_straw: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), server_default="USD", nullable=False)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
