from __future__ import annotations

from uuid import UUID

from src.application.errors import NotFound, PermissionDenied
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.animal_event import AnimalEvent
from src.domain.value_objects.role import Role


def ensure_can_view(role: Role) -> None:
    if not role.can_read():
        raise PermissionDenied("Role not allowed to view events")


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    role: Role,
    animal_id: UUID,
) -> list[AnimalEvent]:
    """List all events for an animal (timeline)."""

    ensure_can_view(role)

    # Verify animal exists
    animal = await uow.animals.get(tenant_id, animal_id)
    if not animal:
        raise NotFound(f"Animal {animal_id} not found")

    # Get events (already ordered by occurred_at desc in repository)
    events = await uow.animal_events.list_by_animal(tenant_id, animal_id)

    return events
