from __future__ import annotations

from uuid import UUID

from src.application.errors import NotFound, PermissionDenied
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.value_objects.role import Role


def ensure_can_delete(role: Role) -> None:
    if not role.can_delete():
        raise PermissionDenied("Role not allowed to delete animals")


async def execute(uow: UnitOfWork, tenant_id: UUID, role: Role, animal_id: UUID) -> None:
    ensure_can_delete(role)
    deleted = await uow.animals.delete(tenant_id, animal_id)
    if not deleted:
        raise NotFound("Animal not found")
    await uow.commit()
