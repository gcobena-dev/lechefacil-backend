from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.errors import AuthError, PermissionDenied
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.value_objects.role import Role
from src.infrastructure.auth.password import PasswordHasher


@dataclass(slots=True)
class ChangePasswordInput:
    user_id: UUID
    current_password: str
    new_password: str


async def execute(
    *,
    uow: UnitOfWork,
    requester_id: UUID,
    requester_role: Role,
    payload: ChangePasswordInput,
    password_hasher: PasswordHasher,
) -> None:
    target_user = await uow.users.get(payload.user_id)
    if not target_user:
        raise AuthError("Invalid user")
    if requester_id != payload.user_id and not requester_role.can_manage_users():
        raise PermissionDenied("Cannot change password for other users")
    if requester_id == payload.user_id:
        if not password_hasher.verify(payload.current_password, target_user.hashed_password):
            raise AuthError("Incorrect current password")
    hashed = password_hasher.hash(payload.new_password)
    await uow.users.update_password(payload.user_id, hashed)
    await uow.commit()
