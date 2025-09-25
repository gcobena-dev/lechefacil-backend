from __future__ import annotations

from dataclasses import dataclass

from src.application.errors import ConflictError
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.user import User
from src.infrastructure.auth.password import PasswordHasher


@dataclass(slots=True)
class SelfRegisterInput:
    email: str
    password: str


@dataclass(slots=True)
class SelfRegisterResult:
    user_id: str
    email: str


async def execute(*, uow: UnitOfWork, payload: SelfRegisterInput, password_hasher: PasswordHasher) -> SelfRegisterResult:
    existing = await uow.users.get_by_email(payload.email)
    if existing:
        raise ConflictError("Email already registered")
    hashed = password_hasher.hash(payload.password)
    user = User.create(email=payload.email, hashed_password=hashed, is_active=True)
    created = await uow.users.add(user)
    await uow.commit()
    return SelfRegisterResult(user_id=str(created.id), email=created.email)

