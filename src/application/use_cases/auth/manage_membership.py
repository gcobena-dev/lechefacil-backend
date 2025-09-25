from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.application.errors import ConflictError
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.membership import Membership
from src.domain.models.user import User
from src.domain.value_objects.role import Role
from src.infrastructure.auth.password import PasswordHasher


@dataclass(slots=True)
class AddMembershipInput:
    tenant_id: UUID
    role: Role
    email: Optional[str] = None
    user_id: Optional[UUID] = None
    create_if_missing: bool = False
    initial_password: Optional[str] = None


@dataclass(slots=True)
class AddMembershipResult:
    user_id: UUID
    email: str
    tenant_id: UUID
    role: Role
    created_user: bool
    generated_password: Optional[str]


async def execute(
    *, uow: UnitOfWork, payload: AddMembershipInput, password_hasher: PasswordHasher
) -> AddMembershipResult:
    # Resolve user
    user = None
    if payload.user_id is not None:
        user = await uow.users.get(payload.user_id)
    elif payload.email is not None:
        user = await uow.users.get_by_email(payload.email)

    created_user = False
    generated_password: Optional[str] = None
    if user is None:
        if not payload.create_if_missing:
            raise ConflictError("User not found and create_if_missing is false")
        # Create user with provided initial_password or generated one
        from secrets import token_urlsafe

        pwd = payload.initial_password or token_urlsafe(16)
        generated_password = None if payload.initial_password else pwd
        hashed = password_hasher.hash(pwd)
        user = User.create(
            email=payload.email or "user@example.com",
            hashed_password=hashed,
            is_active=True,
            must_change_password=True,
        )
        user = await uow.users.add(user)
        created_user = True

    # Idempotency: if membership exists, return existing
    existing_role = await uow.memberships.get_role(user.id, payload.tenant_id)
    if existing_role is not None:
        return AddMembershipResult(
            user_id=user.id,
            email=user.email,
            tenant_id=payload.tenant_id,
            role=existing_role,
            created_user=created_user,
            generated_password=generated_password,
        )

    membership = Membership(user_id=user.id, tenant_id=payload.tenant_id, role=payload.role)
    await uow.memberships.add(membership)
    await uow.commit()
    return AddMembershipResult(
        user_id=user.id,
        email=user.email,
        tenant_id=payload.tenant_id,
        role=payload.role,
        created_user=created_user,
        generated_password=generated_password,
    )

