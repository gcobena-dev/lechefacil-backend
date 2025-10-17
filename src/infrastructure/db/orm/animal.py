from __future__ import annotations

import json
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class StringList(TypeDecorator):
    """Stores a list of strings as ARRAY in PostgreSQL, JSON in SQLite."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String))
        else:
            return dialect.type_descriptor(Text)

    def process_bind_param(self, value, dialect):
        if value is None:
            value = []
        if dialect.name == "postgresql":
            return value
        else:
            return json.dumps(value)

    def process_result_value(self, value, dialect):
        if dialect.name == "postgresql":
            return value if value is not None else []
        else:
            if value is None:
                return []
            return json.loads(value) if value else []


class AnimalORM(Base):
    __tablename__ = "animals"
    __table_args__ = (
        UniqueConstraint("tenant_id", "tag", name="ux_animals_tenant_tag"),
        UniqueConstraint("tenant_id", "id", name="ux_animals_tenant_id"),
    )

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
    labels: Mapped[list[str]] = mapped_column(StringList, nullable=False, server_default="[]")

    # Genealogy fields
    sex: Mapped[str | None] = mapped_column(String(6), nullable=True)
    dam_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("animals.id"), nullable=True
    )
    sire_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("animals.id"), nullable=True
    )
    external_sire_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    external_sire_registry: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Disposition fields
    disposition_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disposition_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Health/withdrawal fields
    in_milk_withdrawal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    withdrawal_until: Mapped[date | None] = mapped_column(Date, nullable=True)

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
