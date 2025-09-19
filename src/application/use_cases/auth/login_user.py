from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.application.errors import AuthError, PermissionDenied
from src.application.interfaces.unit_of_work import UnitOfWork
from src.infrastructure.auth.jwt_service import JWTService
from src.infrastructure.auth.password import PasswordHasher


@dataclass(slots=True)
class LoginInput:
    email: str
    password: str
    tenant_id: UUID | None = None


@dataclass(slots=True)
class LoginResult:
    access_token: str
    token_type: str
    user_id: UUID
    email: str
    memberships: list[dict[str, Any]]


async def execute(
    *,
    uow: UnitOfWork,
    payload: LoginInput,
    password_hasher: PasswordHasher,
    jwt_service: JWTService,
) -> LoginResult:
    user = await uow.users.get_by_email(payload.email.lower())
    if not user or not user.is_active:
        raise AuthError("Invalid credentials")
    if not password_hasher.verify(payload.password, user.hashed_password):
        raise AuthError("Invalid credentials")

    memberships = await uow.memberships.list_for_user(user.id)
    if payload.tenant_id is not None:
        role = next((m.role for m in memberships if m.tenant_id == payload.tenant_id), None)
        if role is None:
            raise PermissionDenied("User not part of tenant")
        extra_claims = {
            "tenant_id": str(payload.tenant_id),
            "role": role.value,
        }
    else:
        extra_claims = {}

    token = jwt_service.create_access_token(subject=user.id, extra_claims=extra_claims)
    return LoginResult(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        memberships=[{"tenant_id": str(m.tenant_id), "role": m.role.value} for m in memberships],
    )
