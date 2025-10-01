from __future__ import annotations

from uuid import UUID

from sqlalchemy import Enum, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.domain.value_objects.role import Role
from src.infrastructure.db.base import Base


class MembershipORM(Base):
    __tablename__ = "memberships"
    # Note: UniqueConstraint is redundant since both columns are primary keys
    # Primary key already enforces uniqueness
    # __table_args__ = (UniqueConstraint("user_id",
    # "tenant_id", name="ux_memberships_user_tenant"),)

    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False), nullable=False)
