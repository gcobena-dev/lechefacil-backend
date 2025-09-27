from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status

from src.application.errors import PermissionDenied
from src.domain.models.milk_price import MilkPrice
from src.infrastructure.auth.context import AuthContext
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.milk_prices import (
    MilkPriceCreate,
    MilkPriceResponse,
    MilkPriceUpdate,
)

router = APIRouter(prefix="/milk-prices", tags=["milk-prices"])


@router.get("/", response_model=list[MilkPriceResponse])
async def list_prices(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    buyer_id: str | None = Query(None),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    buyer_uuid = None
    if buyer_id:
        from uuid import UUID

        buyer_uuid = UUID(buyer_id)
    items = await uow.milk_prices.list(
        context.tenant_id, date_from=date_from, date_to=date_to, buyer_id=buyer_uuid
    )
    return [MilkPriceResponse.model_validate(item) for item in items]


@router.post("/", response_model=MilkPriceResponse, status_code=status.HTTP_201_CREATED)
async def create_price(
    payload: MilkPriceCreate, context: AuthContext = Depends(get_auth_context), uow=Depends(get_uow)
):
    if not context.role.can_create():
        raise PermissionDenied("Role not allowed to create prices")
    # Enforce buyer_id present (schema already requires it, but double-check for clarity)
    if payload.buyer_id is None:
        from src.application.errors import ValidationError

        raise ValidationError("buyer_id is required to register a price")

    existing = await uow.milk_prices.get_existing(context.tenant_id, payload.date, payload.buyer_id)
    if existing:
        updated = await uow.milk_prices.update(
            context.tenant_id,
            existing.id,
            {"price_per_l": payload.price_per_l, "currency": payload.currency},
        )
        result_price = updated
    else:
        price = MilkPrice.create(
            tenant_id=context.tenant_id,
            date=payload.date,
            price_per_l=payload.price_per_l,
            currency=payload.currency,
            buyer_id=payload.buyer_id,
        )
        created = await uow.milk_prices.add(price)
        result_price = created

    # Update tenant config with most recent price info (even if buyer_id is None)
    if result_price:
        tenant_config = await uow.tenant_config.get(context.tenant_id)
        if tenant_config:
            await uow.tenant_config.update(
                context.tenant_id,
                {
                    "default_buyer_id": result_price.buyer_id,  # may be None
                    "default_price_per_l": result_price.price_per_l,
                    "default_currency": result_price.currency,
                },
            )
        else:
            from src.domain.models.tenant_config import TenantConfig

            new_config = TenantConfig(
                tenant_id=context.tenant_id,
                default_buyer_id=result_price.buyer_id,
                default_price_per_l=result_price.price_per_l,
                default_currency=result_price.currency,
            )
            await uow.tenant_config.upsert(new_config)

    await uow.commit()
    return MilkPriceResponse.model_validate(result_price)  # type: ignore[arg-type]


@router.put("/{price_id}", response_model=MilkPriceResponse)
async def update_price(
    price_id: str,
    payload: MilkPriceUpdate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    if not context.role.can_update():
        raise PermissionDenied("Role not allowed to update prices")
    from uuid import UUID

    updates: dict = {}
    if payload.date is not None:
        updates["date"] = payload.date
    if payload.price_per_l is not None:
        updates["price_per_l"] = payload.price_per_l
    if payload.currency is not None:
        updates["currency"] = payload.currency
    if payload.buyer_id is not None:
        updates["buyer_id"] = payload.buyer_id
    updated = await uow.milk_prices.update(context.tenant_id, UUID(price_id), updates)
    if not updated:
        from src.application.errors import NotFound

        raise NotFound("Price not found")

    # Check if this is the most recent price and update tenant config if needed
    most_recent = await uow.milk_prices.get_most_recent(context.tenant_id)
    if most_recent and most_recent.id == updated.id:
        tenant_config = await uow.tenant_config.get(context.tenant_id)
        if tenant_config:
            await uow.tenant_config.update(
                context.tenant_id,
                {
                    "default_buyer_id": updated.buyer_id,  # may be None
                    "default_price_per_l": updated.price_per_l,
                    "default_currency": updated.currency,
                },
            )
        else:
            from src.domain.models.tenant_config import TenantConfig

            new_config = TenantConfig(
                tenant_id=context.tenant_id,
                default_buyer_id=updated.buyer_id,
                default_price_per_l=updated.price_per_l,
                default_currency=updated.currency,
            )
            await uow.tenant_config.upsert(new_config)

    await uow.commit()
    return MilkPriceResponse.model_validate(updated)


@router.delete("/{price_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_price(
    price_id: str, context: AuthContext = Depends(get_auth_context), uow=Depends(get_uow)
):
    if not context.role.can_delete():
        raise PermissionDenied("Role not allowed to delete prices")
    from uuid import UUID

    ok = await uow.milk_prices.delete(context.tenant_id, UUID(price_id))
    if not ok:
        from src.application.errors import NotFound

        raise NotFound("Price not found")
    await uow.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
