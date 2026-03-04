from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork


@dataclass(slots=True)
class UpdateProfileInput:
    user_id: UUID
    first_name: str | None = None
    last_name: str | None = None


@dataclass(slots=True)
class UpdateProfileResult:
    first_name: str | None
    last_name: str | None


async def execute(*, uow: UnitOfWork, payload: UpdateProfileInput) -> UpdateProfileResult:
    await uow.users.update_profile(
        user_id=payload.user_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    await uow.commit()
    return UpdateProfileResult(
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
