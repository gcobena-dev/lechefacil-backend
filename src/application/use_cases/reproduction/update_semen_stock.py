from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from src.application.errors import NotFound
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.semen_inventory import SemenInventory


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


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    payload: UpdateSemenStockInput,
) -> SemenInventory:
    stock = await uow.semen_inventory.get(tenant_id, payload.stock_id)
    if not stock:
        raise NotFound(f"Semen stock {payload.stock_id} not found")

    if payload.batch_code is not None:
        stock.batch_code = payload.batch_code
    if payload.tank_id is not None:
        stock.tank_id = payload.tank_id
    if payload.canister_position is not None:
        stock.canister_position = payload.canister_position
    if payload.current_quantity is not None:
        stock.current_quantity = payload.current_quantity
    if payload.supplier is not None:
        stock.supplier = payload.supplier
    if payload.cost_per_straw is not None:
        stock.cost_per_straw = payload.cost_per_straw
    if payload.currency is not None:
        stock.currency = payload.currency
    if payload.purchase_date is not None:
        stock.purchase_date = payload.purchase_date
    if payload.expiry_date is not None:
        stock.expiry_date = payload.expiry_date
    if payload.notes is not None:
        stock.notes = payload.notes

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
