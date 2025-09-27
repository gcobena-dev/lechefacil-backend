from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from src.application.errors import ConflictError, NotFound, PermissionDenied, ValidationError
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.animal import Animal
from src.domain.value_objects.role import Role


@dataclass(slots=True)
class UpdateAnimalInput:
    version: int
    name: str | None = None
    breed: str | None = None
    birth_date: date | None = None
    lot: str | None = None
    status_id: UUID | None = None
    photo_url: str | None = None


def ensure_can_update(role: Role) -> None:
    if not role.can_update():
        raise PermissionDenied("Role not allowed to update animals")


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    role: Role,
    animal_id: UUID,
    payload: UpdateAnimalInput,
) -> Animal:
    ensure_can_update(role)
    if payload.version < 1:
        raise ValidationError("Invalid version value")
    existing = await uow.animals.get(tenant_id, animal_id)
    if not existing:
        raise NotFound("Animal not found")
    data: dict = {}
    for field_name in ("name", "breed", "birth_date", "lot", "status_id", "photo_url"):
        value = getattr(payload, field_name)
        if value is not None:
            data[field_name] = value
    if not data:
        return existing
    updated = await uow.animals.update(
        tenant_id,
        animal_id,
        data=data,
        expected_version=payload.version,
    )
    if not updated:
        raise ConflictError("Version mismatch while updating animal")
    await uow.commit()
    return updated
