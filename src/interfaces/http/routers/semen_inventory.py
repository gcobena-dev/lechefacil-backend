from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.use_cases.reproduction import (
    add_semen_stock,
    list_semen_stock,
    update_semen_stock,
)
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.semen_inventory import (
    SemenInventoryCreate,
    SemenInventoryListResponse,
    SemenInventoryResponse,
    SemenInventoryUpdate,
)
from src.interfaces.middleware.auth_middleware import AuthContext

router = APIRouter(prefix="/reproduction/semen", tags=["reproduction"])


@router.post("", response_model=SemenInventoryResponse, status_code=status.HTTP_201_CREATED)
async def add_semen_stock_endpoint(
    payload: SemenInventoryCreate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    input_data = add_semen_stock.AddSemenStockInput(
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
    result = await add_semen_stock.execute(uow, context.tenant_id, input_data)
    await uow.commit()
    return result


@router.get("", response_model=SemenInventoryListResponse)
async def list_semen_stock_endpoint(
    sire_catalog_id: UUID | None = None,
    in_stock_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    result = await list_semen_stock.execute(
        uow,
        context.tenant_id,
        sire_catalog_id=sire_catalog_id,
        in_stock_only=in_stock_only,
        limit=limit,
        offset=offset,
    )
    return {
        "items": result.items,
        "total": result.total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{stock_id}", response_model=SemenInventoryResponse)
async def get_semen_stock_endpoint(
    stock_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    stock = await uow.semen_inventory.get(context.tenant_id, stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail="Semen stock not found")
    return stock


@router.put("/{stock_id}", response_model=SemenInventoryResponse)
async def update_semen_stock_endpoint(
    stock_id: UUID,
    payload: SemenInventoryUpdate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    input_data = update_semen_stock.UpdateSemenStockInput(
        stock_id=stock_id,
        **payload.model_dump(exclude_unset=True),
    )
    result = await update_semen_stock.execute(uow, context.tenant_id, input_data)
    await uow.commit()
    return result


@router.delete("/{stock_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_semen_stock_endpoint(
    stock_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    await update_semen_stock.delete(uow, context.tenant_id, stock_id)
    await uow.commit()
