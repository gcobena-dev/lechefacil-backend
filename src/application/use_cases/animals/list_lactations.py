from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from src.application.errors import NotFound, PermissionDenied
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.lactation import Lactation
from src.domain.value_objects.role import Role


@dataclass(slots=True)
class LactationWithMetrics:
    lactation: Lactation
    total_volume_l: Decimal = Decimal("0.0")
    days_in_milk: int = 0
    average_daily_l: Decimal = Decimal("0.0")
    production_count: int = 0


def ensure_can_view(role: Role) -> None:
    if not role.can_read():
        raise PermissionDenied("Role not allowed to view lactations")


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    role: Role,
    animal_id: UUID,
) -> list[LactationWithMetrics]:
    """List all lactations for an animal with metrics."""

    ensure_can_view(role)

    # Verify animal exists
    animal = await uow.animals.get(tenant_id, animal_id)
    if not animal:
        raise NotFound(f"Animal {animal_id} not found")

    # Get lactations
    lactations = await uow.lactations.list_by_animal(tenant_id, animal_id)

    # Enrich with metrics
    result = []
    for lactation in lactations:
        # Get total volume
        total_volume = await uow.lactations.sum_volume(lactation.id)

        # Calculate days in milk
        end_date = lactation.end_date if lactation.end_date else date.today()
        days_in_milk = (end_date - lactation.start_date).days

        # Calculate average
        average_daily = Decimal("0.0")
        if days_in_milk > 0:
            average_daily = Decimal(str(total_volume)) / Decimal(days_in_milk)

        # TODO: Get production count from repository
        production_count = 0

        result.append(
            LactationWithMetrics(
                lactation=lactation,
                total_volume_l=Decimal(str(total_volume)),
                days_in_milk=days_in_milk,
                average_daily_l=average_daily,
                production_count=production_count,
            )
        )

    return result
