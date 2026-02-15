from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from src.application.errors import NotFound
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.semen_inventory import SemenInventory


@dataclass(slots=True)
class AddSemenStockInput:
    sire_catalog_id: UUID
    initial_quantity: int
    batch_code: str | None = None
    tank_id: str | None = None
    canister_position: str | None = None
    supplier: str | None = None
    cost_per_straw: Decimal | None = None
    currency: str = "USD"
    purchase_date: date | None = None
    expiry_date: date | None = None
    notes: str | None = None


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    payload: AddSemenStockInput,
) -> SemenInventory:
    # Validate sire exists
    sire = await uow.sire_catalog.get(tenant_id, payload.sire_catalog_id)
    if not sire:
        raise NotFound(f"Sire {payload.sire_catalog_id} not found")

    stock = SemenInventory.create(
        tenant_id=tenant_id,
        sire_catalog_id=payload.sire_catalog_id,
        initial_quantity=payload.initial_quantity,
        batch_code=payload.batch_code,
        tank_id=payload.tank_id,
        canister_position=payload.canister_position,
        supplier=payload.supplier,
        cost_per_straw=payload.cost_per_straw,
        currency=payload.currency,
        purchase_date=payload.purchase_date,
        expiry_date=payload.expiry_date,
        notes=payload.notes,
    )
    return await uow.semen_inventory.add(stock)
