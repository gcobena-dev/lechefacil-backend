from __future__ import annotations

from datetime import date as DtDate
from datetime import timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response, status

from src.application.errors import PermissionDenied
from src.application.events.dispatcher import dispatch_events
from src.application.events.models import DeliveryRecordedEvent
from src.domain.models.milk_delivery import MilkDelivery
from src.infrastructure.auth.context import AuthContext
from src.interfaces.http.deps import (
    get_auth_context,
    get_uow,
)
from src.interfaces.http.schemas.milk_deliveries import (
    DeliverySummaryItem,
    MilkDeliveryCreate,
    MilkDeliveryResponse,
    MilkDeliveryUpdate,
)

router = APIRouter(prefix="/milk-deliveries", tags=["milk-deliveries"])


def _round2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@router.get("/", response_model=list[MilkDeliveryResponse])
async def list_deliveries(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    buyer_id: str | None = Query(None),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    from uuid import UUID as _UUID

    df = DtDate.fromisoformat(date_from) if date_from else None
    dt = DtDate.fromisoformat(date_to) if date_to else None
    bid = _UUID(buyer_id) if buyer_id else None
    items = await uow.milk_deliveries.list(
        context.tenant_id,
        date_from=df,
        date_to=dt,
        buyer_id=bid,
    )
    return [MilkDeliveryResponse.model_validate(item) for item in items]


@router.post("/", response_model=MilkDeliveryResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery(
    payload: MilkDeliveryCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    # Allow ADMIN, MANAGER, and WORKER to register deliveries
    from src.domain.value_objects.role import Role

    if context.role not in {Role.ADMIN, Role.MANAGER, Role.WORKER}:
        raise PermissionDenied("Role not allowed to create deliveries")
    cfg = await uow.tenant_config.get(context.tenant_id)
    if not cfg:
        # Get most recent price to populate default config
        most_recent_price = await uow.milk_prices.get_most_recent(context.tenant_id)
        if most_recent_price:
            from src.domain.models.tenant_config import TenantConfig

            cfg = TenantConfig(
                tenant_id=context.tenant_id,
                default_buyer_id=most_recent_price.buyer_id,
                default_price_per_l=most_recent_price.price_per_l,
                default_currency=most_recent_price.currency,
            )
            cfg = await uow.tenant_config.upsert(cfg)

    buyer_id = payload.buyer_id or (cfg.default_buyer_id if cfg else None)
    if buyer_id is None:
        from src.application.errors import ValidationError

        raise ValidationError("buyer_id is required (no default buyer configured)")
    # price resolution: buyer/date, else default(date), else tenant default
    dt = payload.date_time
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Prevent duplicate delivery for same buyer and local day
    existing_same_day = await uow.milk_deliveries.list(
        context.tenant_id, date_from=dt.date(), date_to=dt.date(), buyer_id=buyer_id
    )
    if existing_same_day:
        from src.application.errors import ValidationError

        raise ValidationError("Ya registró la entrega de leche para este comprador en esta fecha")

    mp = await uow.milk_prices.get_for_date(context.tenant_id, dt.date(), buyer_id)
    if mp is None:
        mp = await uow.milk_prices.get_for_date(context.tenant_id, dt.date(), None)
    price = mp.price_per_l if mp else (cfg.default_price_per_l if cfg else None)
    currency = mp.currency if mp else (cfg.default_currency if cfg else "USD")

    # Final fallback: use most recent price if no other price is found
    if price is None:
        most_recent_price = await uow.milk_prices.get_most_recent(context.tenant_id)
        if most_recent_price:
            price = most_recent_price.price_per_l
            currency = most_recent_price.currency

    if price is None:
        from src.application.errors import ValidationError

        raise ValidationError("No price configured for this date and no default price set")
    amount = _round2(payload.volume_l * price)
    delivery = MilkDelivery.create(
        tenant_id=context.tenant_id,
        buyer_id=buyer_id,
        date_time=dt,
        volume_l=payload.volume_l,
        price_snapshot=price,
        currency=currency,
        amount=amount,
        notes=payload.notes,
    )
    created = await uow.milk_deliveries.add(delivery)

    # Get buyer details for notification
    await uow.buyers.get(context.tenant_id, buyer_id)

    # Emit domain event
    uow.add_event(
        DeliveryRecordedEvent(
            tenant_id=context.tenant_id,
            actor_user_id=context.user_id,
            delivery_id=created.id,
            buyer_id=buyer_id,
            volume_l=payload.volume_l,
            amount=amount,
            currency=currency,
            date_time=dt,
        )
    )

    events = uow.drain_events()
    await uow.commit()

    # Dispatch events post-commit in background (non-blocking)
    if request is not None:
        session_factory = getattr(request.app.state, "session_factory", None)
        if session_factory is not None:
            background_tasks.add_task(dispatch_events, session_factory, events)

    return MilkDeliveryResponse.model_validate(created)


@router.put("/{delivery_id}", response_model=MilkDeliveryResponse)
async def update_delivery(
    delivery_id: str,
    payload: MilkDeliveryUpdate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    if not context.role.can_update():
        raise PermissionDenied("Role not allowed to update deliveries")
    from uuid import UUID as _UUID

    updates: dict = {}
    if payload.date_time is not None:
        dt = payload.date_time
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        updates["date_time"] = dt
        updates["date"] = dt.date()
    if payload.volume_l is not None:
        updates["volume_l"] = payload.volume_l
    if payload.buyer_id is not None:
        updates["buyer_id"] = payload.buyer_id
    # If buyer/date/volume changed, recompute snapshot/amount
    if {"date_time", "buyer_id", "volume_l"} & updates.keys():
        existing = await uow.milk_deliveries.get(context.tenant_id, _UUID(delivery_id))
        if not existing:
            from src.application.errors import NotFound

            raise NotFound("Delivery not found")
        dt = updates.get("date_time", existing.date_time)
        bid = updates.get("buyer_id", existing.buyer_id)
        vol = updates.get("volume_l", existing.volume_l)

        # Prevent duplicate after update (same buyer and date on a different record)
        same_day = await uow.milk_deliveries.list(
            context.tenant_id, date_from=dt.date(), date_to=dt.date(), buyer_id=bid
        )
        if any(d.id != existing.id for d in same_day):
            from src.application.errors import ValidationError

            raise ValidationError(
                "Ya registró la entrega de leche para este comprador en esta fecha"
            )
        mp = await uow.milk_prices.get_for_date(context.tenant_id, dt.date(), bid)
        if mp is None:
            mp = await uow.milk_prices.get_for_date(context.tenant_id, dt.date(), None)
        cfg = await uow.tenant_config.get(context.tenant_id)
        price = mp.price_per_l if mp else (cfg.default_price_per_l if cfg else None)
        currency = mp.currency if mp else (cfg.default_currency if cfg else existing.currency)

        # Final fallback: use most recent price if no other price is found
        if price is None:
            most_recent_price = await uow.milk_prices.get_most_recent(context.tenant_id)
            if most_recent_price:
                price = most_recent_price.price_per_l
                currency = most_recent_price.currency

        if price is None:
            from src.application.errors import ValidationError

            raise ValidationError("No price configured for this date and no default price set")
        updates["price_snapshot"] = price
        updates["currency"] = currency
        updates["amount"] = _round2(vol * price)
    updated = await uow.milk_deliveries.update(context.tenant_id, _UUID(delivery_id), updates)
    if not updated:
        from src.application.errors import NotFound

        raise NotFound("Delivery not found")
    await uow.commit()
    return MilkDeliveryResponse.model_validate(updated)


@router.delete("/{delivery_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_delivery(
    delivery_id: str, context: AuthContext = Depends(get_auth_context), uow=Depends(get_uow)
):
    if not context.role.can_delete():
        raise PermissionDenied("Role not allowed to delete deliveries")
    from uuid import UUID as _UUID

    ok = await uow.milk_deliveries.delete(context.tenant_id, _UUID(delivery_id))
    if not ok:
        from src.application.errors import NotFound

        raise NotFound("Delivery not found")
    await uow.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/summary", response_model=list[DeliverySummaryItem])
async def summary(
    date_from: str,
    date_to: str,
    buyer_id: str | None = Query(None),
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    from uuid import UUID as _UUID

    df = DtDate.fromisoformat(date_from)
    dt = DtDate.fromisoformat(date_to)
    bid = _UUID(buyer_id) if buyer_id else None
    rows = await uow.milk_deliveries.summarize(
        context.tenant_id, date_from=df, date_to=dt, buyer_id=bid, period=period
    )
    return [DeliverySummaryItem(**r) for r in rows]
