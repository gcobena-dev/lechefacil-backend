from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.errors import NotFound, PermissionDenied
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.animal_event import AnimalEvent
from src.domain.value_objects.role import Role


def ensure_can_view(role: Role) -> None:
    if not role.can_read():
        raise PermissionDenied("Role not allowed to view events")


@dataclass(slots=True)
class ListEventsResult:
    items: list[AnimalEvent]
    total: int
    page: int
    per_page: int


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    role: Role,
    animal_id: UUID,
    page: int = 1,
    per_page: int = 10,
) -> ListEventsResult:
    """List events for an animal with pagination."""

    ensure_can_view(role)

    # Verify animal exists
    animal = await uow.animals.get(tenant_id, animal_id)
    if not animal:
        raise NotFound(f"Animal {animal_id} not found")

    # Clamp pagination parameters
    page = max(1, page)
    per_page = max(1, per_page)

    total = await uow.animal_events.count_by_animal(tenant_id, animal_id)
    offset = (page - 1) * per_page
    items = await uow.animal_events.list_by_animal_paginated(tenant_id, animal_id, offset, per_page)

    return ListEventsResult(items=items, total=total, page=page, per_page=per_page)
