from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from src.application.errors import NotFound
from src.application.interfaces.unit_of_work import UnitOfWork
from src.application.patching import resolve_patch
from src.domain.models.semen_inventory import SemenInventory

#: Columns that may be blanked out; `current_quantity` and `currency` are
#: NOT NULL.
CLEARABLE_FIELDS = frozenset(
    {
        "batch_code",
        "tank_id",
        "canister_position",
        "supplier",
        "cost_per_straw",
        "purchase_date",
        "expiry_date",
        "notes",
    }
)

PATCHABLE_FIELDS = ("current_quantity", "currency", *sorted(CLEARABLE_FIELDS))


@dataclass(slots=True)
class UpdateSemenStockInput:
    stock_id: UUID
    batch_code: str | None = None
    tank_id: str | None = None
    canister_position: str | None = None
    current_quantity: int | None = None
    supplier: str | None = None
    cost_per_straw: Decimal | None = None
    currency: str | None = None
    purchase_date: date | None = None
    expiry_date: date | None = None
    notes: str | None = None
    #: Field names the client actually sent, so a `null` can clear a field
    #: instead of being read as "not provided".
    fields_set: frozenset[str] = frozenset()


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    payload: UpdateSemenStockInput,
) -> SemenInventory:
    stock = await uow.semen_inventory.get(tenant_id, payload.stock_id)
    if not stock:
        raise NotFound(f"Semen stock {payload.stock_id} not found")

    for name, value in resolve_patch(
        payload,
        PATCHABLE_FIELDS,
        sent=payload.fields_set,
        nullable=CLEARABLE_FIELDS,
    ).items():
        setattr(stock, name, value)

    stock.bump_version()
    return await uow.semen_inventory.update(stock)


async def delete(
    uow: UnitOfWork,
    tenant_id: UUID,
    stock_id: UUID,
) -> None:
    stock = await uow.semen_inventory.get(tenant_id, stock_id)
    if not stock:
        raise NotFound(f"Semen stock {stock_id} not found")
    stock.deleted_at = datetime.now(timezone.utc)
    await uow.semen_inventory.delete(stock)
