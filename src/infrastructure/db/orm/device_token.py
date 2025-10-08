from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class DeviceTokenORM(Base):
    __tablename__ = "device_tokens"
    __table_args__ = (
        Index("uq_device_tokens_token", "token", unique=True),
        Index("ix_device_tokens_user", "user_id"),
        Index("ix_device_tokens_tenant", "tenant_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)  # ios | android | web
    token: Mapped[str] = mapped_column(String(512), nullable=False)
    app_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
