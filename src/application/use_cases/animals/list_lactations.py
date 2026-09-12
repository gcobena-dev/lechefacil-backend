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
    #: What the milk of this lactation was worth, summed from the value each
    #: record was given on the day it was entered.
    total_amount: Decimal = Decimal("0.0")
    currency: str | None = None


def ensure_can_view(role: Role) -> None:
    if not role.can_read():
        raise PermissionDenied("Role not allowed to view lactations")


def compute_metrics(
    lactation: Lactation,
    totals: dict | None,
    fallback_currency: str | None = None,
) -> LactationWithMetrics:
    """Turn one lactation and its production totals into the card's numbers.

    Days in milk runs to today while the lactation is open, so the average of a
    cow still milking keeps moving as the days pass.
    """
    totals = totals or {}
    total_volume = Decimal(str(totals.get("total_volume_l") or 0))
    total_amount = Decimal(str(totals.get("total_amount") or 0))

    end_date = lactation.end_date if lactation.end_date else date.today()
    days_in_milk = (end_date - lactation.start_date).days

    average_daily = Decimal("0.0")
    if days_in_milk > 0:
        average_daily = total_volume / Decimal(days_in_milk)

    return LactationWithMetrics(
        lactation=lactation,
        total_volume_l=total_volume,
        days_in_milk=days_in_milk,
        average_daily_l=average_daily,
        production_count=int(totals.get("production_count") or 0),
        total_amount=total_amount,
        currency=totals.get("currency") or fallback_currency,
    )


async def default_currency(uow: UnitOfWork, tenant_id: UUID) -> str | None:
    """The farm's currency, to label a total that has no productions to read it from."""
    try:
        config = await uow.tenant_config.get(tenant_id)
    except Exception:
        return None
    return getattr(config, "default_currency", None) if config else None


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    role: Role,
    animal_id: UUID,
) -> list[LactationWithMetrics]:
    """List all lactations for an animal with metrics."""

    ensure_can_view(role)

    animal = await uow.animals.get(tenant_id, animal_id)
    if not animal:
        raise NotFound(f"Animal {animal_id} not found")

    lactations = await uow.lactations.list_by_animal(tenant_id, animal_id)
    if not lactations:
        return []

    totals = await uow.lactations.metrics_for_lactations(tenant_id, [ln.id for ln in lactations])
    fallback = await default_currency(uow, tenant_id)

    return [compute_metrics(ln, totals.get(ln.id), fallback) for ln in lactations]
