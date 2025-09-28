from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class AnimalORM(Base):
    __tablename__ = "animals"
    __table_args__ = (UniqueConstraint("tenant_id", "tag", name="ux_animals_tenant_tag"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    tag: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    breed: Mapped[str | None] = mapped_column(String(255), nullable=True)
    breed_variant: Mapped[str | None] = mapped_column(String(50), nullable=True)
    breed_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    lot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_lot_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    status_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
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
