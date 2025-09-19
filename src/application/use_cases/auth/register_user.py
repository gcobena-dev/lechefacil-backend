from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.errors import ConflictError, PermissionDenied
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.membership import Membership
from src.domain.models.user import User
from src.domain.value_objects.role import Role
from src.infrastructure.auth.password import PasswordHasher


@dataclass(slots=True)
class RegisterUserInput:
    email: str
    password: str
    tenant_id: UUID
    role: Role
    is_active: bool = True


async def execute(
    *,
    uow: UnitOfWork,
    requester_role: Role,
    payload: RegisterUserInput,
    password_hasher: PasswordHasher,
) -> User:
    if not requester_role.can_manage_users():
        raise PermissionDenied("Only admins can create users")
    existing = await uow.users.get_by_email(payload.email)
    if existing:
        raise ConflictError("Email already registered")
    hashed = password_hasher.hash(payload.password)
    user = User.create(email=payload.email, hashed_password=hashed, is_active=payload.is_active)
    created = await uow.users.add(user)
    membership = Membership(user_id=created.id, tenant_id=payload.tenant_id, role=payload.role)
    await uow.memberships.add(membership)
    await uow.commit()
    return created
