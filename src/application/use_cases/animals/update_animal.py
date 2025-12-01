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
    breed_variant: str | None = None
    breed_id: UUID | None = None
    birth_date: date | None = None
    lot: str | None = None
    current_lot_id: UUID | None = None
    status_id: UUID | None = None
    photo_url: str | None = None
    labels: list[str] | None = None
    # Genealogy fields
    sex: str | None = None
    dam_id: UUID | None = None
    sire_id: UUID | None = None
    external_sire_code: str | None = None
    external_sire_registry: str | None = None


def ensure_can_update(role: Role) -> None:
    if not role.can_update():
        raise PermissionDenied("Role not allowed to update animals")


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    role: Role,
    actor_user_id: UUID,
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
    for field_name in (
        "name",
        "breed",
        "breed_variant",
        "breed_id",
        "birth_date",
        "lot",
        "current_lot_id",
        "status_id",
        "photo_url",
        "labels",
        # Genealogy fields
        "sex",
        "dam_id",
        "sire_id",
        "external_sire_code",
        "external_sire_registry",
    ):
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
    # Emit event for notifications
    try:
        from src.application.events.models import AnimalUpdatedEvent

        uow.add_event(
            AnimalUpdatedEvent(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                animal_id=updated.id,
                tag=updated.tag,
                name=updated.name,
                changed_fields=list(data.keys()),
            )
        )
    except Exception:
        pass
    await uow.commit()
    return updated
