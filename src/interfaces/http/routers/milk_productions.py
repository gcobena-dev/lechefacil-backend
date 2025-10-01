from __future__ import annotations

from datetime import date as DtDate
from datetime import datetime, timezone
from datetime import time as DtTime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, Query, Response, status

from src.application.errors import PermissionDenied
from src.domain.models.milk_production import MilkProduction
from src.infrastructure.auth.context import AuthContext
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.milk_productions import (
    MilkProductionCreate,
    MilkProductionListResponse,
    MilkProductionResponse,
    MilkProductionsBulkCreate,
    MilkProductionUpdate,
)

router = APIRouter(prefix="/milk-productions", tags=["milk-productions"])


def _to_liters(input_unit: str, quantity: Decimal, density: Decimal) -> tuple[Decimal, list[str]]:
    warnings: list[str] = []
    if density < Decimal("1.02") or density > Decimal("1.04"):
        warnings.append("density out of typical range (1.02–1.04)")
    if input_unit == "l":
        vol = quantity
    elif input_unit == "kg":
        vol = quantity / density
    elif input_unit == "lb":
        vol = (quantity / Decimal("2.20462")) / density
    else:
        raise ValueError("invalid unit")
    return (vol.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP), warnings)


@router.get("/", response_model=MilkProductionListResponse)
async def list_productions(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    animal_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    from datetime import date as DtDate
    from uuid import UUID as _UUID

    df = DtDate.fromisoformat(date_from) if date_from else None
    dt = DtDate.fromisoformat(date_to) if date_to else None
    # Include UTC spillover by extending date_to by +1 day
    if dt is not None:
        from datetime import timedelta as _Td

        dt = dt + _Td(days=1)
    aid = _UUID(animal_id) if animal_id else None
    total = await uow.milk_productions.count(
        context.tenant_id,
        date_from=df,
        date_to=dt,
        animal_id=aid,
    )
    items = await uow.milk_productions.list(
        context.tenant_id,
        date_from=df,
        date_to=dt,
        animal_id=aid,
        limit=limit,
        offset=offset,
    )
    return MilkProductionListResponse(
        items=[MilkProductionResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/", response_model=MilkProductionResponse, status_code=status.HTTP_201_CREATED)
async def create_production(
    payload: MilkProductionCreate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    if not context.role.can_create():
        raise PermissionDenied("Role not allowed to create productions")
    from src.domain.models.tenant_config import TenantConfig

    cfg = await uow.tenant_config.get(context.tenant_id)
    if not cfg:
        # Get most recent price to populate default config
        most_recent_price = await uow.milk_prices.get_most_recent(context.tenant_id)
        cfg = TenantConfig(
            tenant_id=context.tenant_id,
            default_buyer_id=most_recent_price.buyer_id if most_recent_price else None,
            default_price_per_l=most_recent_price.price_per_l if most_recent_price else None,
            default_currency=most_recent_price.currency if most_recent_price else "USD",
        )
        cfg = await uow.tenant_config.upsert(cfg)
    density = payload.density if payload.density is not None else cfg.default_density
    unit = (
        payload.input_unit if payload.input_unit is not None else cfg.default_production_input_unit
    )
    vol_l, _ = _to_liters(unit, payload.input_quantity, density)
    # Resolve datetime from date/shift if date_time not provided
    dt = payload.date_time
    if dt is None:
        d = payload.date or DtDate.today()
        shift = (payload.shift or "AM").upper()
        # Simple convention: AM -> 06:00, PM -> 18:00 UTC
        base_time = DtTime(hour=6, minute=0) if shift == "AM" else DtTime(hour=18, minute=0)
        dt = datetime.combine(d, base_time).replace(tzinfo=timezone.utc)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Resolve buyer & price snapshot for approximate value
    buyer_id = payload.buyer_id or (cfg.default_buyer_id if cfg else None)
    price = None
    currency = cfg.default_currency if cfg else "USD"
    if buyer_id is not None:
        p = await uow.milk_prices.get_for_date(context.tenant_id, dt.date(), buyer_id)
        if p is not None:
            price = p.price_per_l
            currency = p.currency
    if price is None:
        p = await uow.milk_prices.get_for_date(context.tenant_id, dt.date(), None)
        if p is not None:
            price = p.price_per_l
            currency = p.currency
    if price is None and cfg and cfg.default_price_per_l is not None:
        price = cfg.default_price_per_l
        currency = cfg.default_currency

    # Final fallback: use most recent price if no other price is found
    if price is None:
        most_recent_price = await uow.milk_prices.get_most_recent(context.tenant_id)
        if most_recent_price:
            price = most_recent_price.price_per_l
            currency = most_recent_price.currency
    amount = (vol_l * price).quantize(Decimal("0.01")) if price is not None else None

    # Determine shift to persist
    shift_val = (payload.shift or ("AM" if dt.hour < 12 else "PM")).upper()
    # Prevent duplicate per animal/day/shift
    existing_same = await uow.milk_productions.list(
        context.tenant_id, date_from=dt.date(), date_to=dt.date(), animal_id=payload.animal_id
    )
    dup = next(
        (
            e
            for e in existing_same
            if getattr(e, "shift", ("AM" if e.date_time.hour < 12 else "PM")) == shift_val
        ),
        None,
    )
    if dup is not None:
        from src.application.errors import ValidationError

        raise ValidationError(
            "Ya existe un registro para este animal en el mismo día y turno",
            details={
                "conflicts": [
                    {
                        "animal_id": str(payload.animal_id),
                        "date": str(dt.date()),
                        "shift": shift_val,
                        "input_quantity": str(payload.input_quantity),
                        "existing_date_time": dup.date_time.isoformat(),
                        "existing_volume_l": str(dup.volume_l),
                    }
                ]
            },
        )

    mp = MilkProduction.create(
        tenant_id=context.tenant_id,
        animal_id=payload.animal_id,
        buyer_id=buyer_id,
        date_time=dt,
        shift=shift_val,
        input_unit=unit,
        input_quantity=payload.input_quantity,
        density=density,
        volume_l=vol_l,
        price_snapshot=price,
        currency=currency,
        amount=amount,
        notes=payload.notes,
    )
    created = await uow.milk_productions.add(mp)
    await uow.commit()
    return MilkProductionResponse.model_validate(created)


@router.post(
    "/bulk", response_model=list[MilkProductionResponse], status_code=status.HTTP_201_CREATED
)
async def create_productions_bulk(
    payload: MilkProductionsBulkCreate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> list[MilkProductionResponse]:
    if not context.role.can_create():
        raise PermissionDenied("Role not allowed to create productions")
    from src.domain.models.tenant_config import TenantConfig

    cfg = await uow.tenant_config.get(context.tenant_id)
    if not cfg:
        # Get most recent price to populate default config
        most_recent_price = await uow.milk_prices.get_most_recent(context.tenant_id)
        cfg = TenantConfig(
            tenant_id=context.tenant_id,
            default_buyer_id=most_recent_price.buyer_id if most_recent_price else None,
            default_price_per_l=most_recent_price.price_per_l if most_recent_price else None,
            default_currency=most_recent_price.currency if most_recent_price else "USD",
        )
        cfg = await uow.tenant_config.upsert(cfg)
    # Resolve shared parameters for the batch
    density_shared = payload.density if payload.density is not None else cfg.default_density
    unit_shared = (
        payload.input_unit if payload.input_unit is not None else cfg.default_production_input_unit
    )
    # Resolve datetime from date/shift if date_time not provided
    dt_shared = payload.date_time
    if dt_shared is None:
        d = payload.date or DtDate.today()
        sh = (payload.shift or "AM").upper()
        base_time = DtTime(hour=6, minute=0) if sh == "AM" else DtTime(hour=18, minute=0)
        dt_shared = datetime.combine(d, base_time).replace(tzinfo=timezone.utc)
    elif dt_shared.tzinfo is None:
        dt_shared = dt_shared.replace(tzinfo=timezone.utc)
    # Resolve price snapshot and currency based on buyer/date
    buyer_shared = payload.buyer_id or (cfg.default_buyer_id if cfg else None)
    price_shared = None
    currency_shared = cfg.default_currency if cfg else "USD"
    if buyer_shared is not None:
        p = await uow.milk_prices.get_for_date(context.tenant_id, dt_shared.date(), buyer_shared)
        if p is not None:
            price_shared = p.price_per_l
            currency_shared = p.currency
    if price_shared is None:
        p = await uow.milk_prices.get_for_date(context.tenant_id, dt_shared.date(), None)
        if p is not None:
            price_shared = p.price_per_l
            currency_shared = p.currency
    if price_shared is None and cfg and cfg.default_price_per_l is not None:
        price_shared = cfg.default_price_per_l
        currency_shared = cfg.default_currency

    # Final fallback: use most recent price if no other price is found
    if price_shared is None:
        most_recent_price = await uow.milk_prices.get_most_recent(context.tenant_id)
        if most_recent_price:
            price_shared = most_recent_price.price_per_l
            currency_shared = most_recent_price.currency

    results: list[MilkProductionResponse] = []
    conflicts: list[dict] = []
    for item in payload.items:
        vol_l, _ = _to_liters(unit_shared, item.input_quantity, density_shared)
        amount = (
            (vol_l * price_shared).quantize(Decimal("0.01")) if price_shared is not None else None
        )
        # Compute shift to persist
        shift_val = (payload.shift or ("AM" if dt_shared.hour < 12 else "PM")).upper()
        # Validate duplicates per animal/day/shift
        existing_same = await uow.milk_productions.list(
            context.tenant_id,
            date_from=dt_shared.date(),
            date_to=dt_shared.date(),
            animal_id=item.animal_id,
        )
        dup = next(
            (
                e
                for e in existing_same
                if getattr(e, "shift", ("AM" if e.date_time.hour < 12 else "PM")) == shift_val
            ),
            None,
        )
        if dup is not None:
            conflicts.append(
                {
                    "animal_id": str(item.animal_id),
                    "date": str(dt_shared.date()),
                    "shift": shift_val,
                    "input_quantity": str(item.input_quantity),
                    "existing_date_time": dup.date_time.isoformat(),
                    "existing_volume_l": str(dup.volume_l),
                }
            )
            continue

        mp = MilkProduction.create(
            tenant_id=context.tenant_id,
            animal_id=item.animal_id,
            buyer_id=buyer_shared,
            date_time=dt_shared,
            shift=shift_val,
            input_unit=unit_shared,
            input_quantity=item.input_quantity,
            density=density_shared,
            volume_l=vol_l,
            price_snapshot=price_shared,
            currency=currency_shared,
            amount=amount,
            notes=payload.notes,
        )
        created = await uow.milk_productions.add(mp)
        results.append(MilkProductionResponse.model_validate(created))
    # If there were conflicts, abort with detailed validation error
    if conflicts:
        from src.application.errors import ValidationError

        raise ValidationError(
            "Algunos animales ya tienen registro para ese día/turno",
            details={"conflicts": conflicts},
        )
    await uow.commit()
    return results


@router.put("/{production_id}", response_model=MilkProductionResponse)
async def update_production(
    production_id: str,
    payload: MilkProductionUpdate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    if not context.role.can_update():
        raise PermissionDenied("Role not allowed to update productions")
    from uuid import UUID as _UUID

    updates: dict = {}
    # Update date_time via explicit date_time or via date/shift
    dt_override = None
    if payload.date_time is not None:
        dt_override = payload.date_time
    elif payload.date is not None or payload.shift is not None:
        # Load existing to compute base date/shift
        existing = await uow.milk_productions.get(context.tenant_id, _UUID(production_id))
        if not existing:
            from src.application.errors import NotFound

            raise NotFound("Production not found")
        d = payload.date or existing.date
        sh = (payload.shift or ("AM" if existing.date_time.hour < 12 else "PM")).upper()
        base_time = DtTime(hour=6, minute=0) if sh == "AM" else DtTime(hour=18, minute=0)
        dt_override = datetime.combine(d, base_time).replace(tzinfo=timezone.utc)
    if dt_override is not None:
        if dt_override.tzinfo is None:
            dt_override = dt_override.replace(tzinfo=timezone.utc)
        updates["date_time"] = dt_override
        updates["date"] = dt_override.date()
        # If shift not explicitly provided, recompute from new date_time
        updates["shift"] = "AM" if dt_override.hour < 12 else "PM"
    if payload.shift is not None:
        updates["shift"] = payload.shift
    if payload.animal_id is not None:
        updates["animal_id"] = payload.animal_id
    if payload.buyer_id is not None:
        updates["buyer_id"] = payload.buyer_id
    if payload.input_unit is not None:
        updates["input_unit"] = payload.input_unit
    if payload.input_quantity is not None:
        updates["input_quantity"] = payload.input_quantity
    if payload.density is not None:
        updates["density"] = payload.density
    # If any of unit/quantity/density changed, recompute volume
    if {"input_unit", "input_quantity", "density"} & updates.keys():
        existing = await uow.milk_productions.get(context.tenant_id, _UUID(production_id))
        if not existing:
            from src.application.errors import NotFound

            raise NotFound("Production not found")
        unit = updates.get("input_unit", existing.input_unit)
        qty = updates.get("input_quantity", existing.input_quantity)
        den = updates.get("density", existing.density)
        vol_l, _ = _to_liters(unit, qty, den)
        updates["volume_l"] = vol_l
    # If date/buyer/volume changed, recompute price snapshot and amount
    if {"date_time", "buyer_id", "volume_l", "shift"} & updates.keys():
        existing = await uow.milk_productions.get(context.tenant_id, _UUID(production_id))
        if not existing:
            from src.application.errors import NotFound

            raise NotFound("Production not found")
        dt = updates.get("date_time", existing.date_time)
        sh = updates.get(
            "shift", getattr(existing, "shift", ("AM" if existing.date_time.hour < 12 else "PM"))
        )
        # Prevent duplicate per animal/day/shift after update
        same = await uow.milk_productions.list(
            context.tenant_id,
            date_from=dt.date(),
            date_to=dt.date(),
            animal_id=updates.get("animal_id", existing.animal_id),
        )
        if any(
            r.id != existing.id
            and getattr(r, "shift", ("AM" if r.date_time.hour < 12 else "PM")) == sh
            for r in same
        ):
            from src.application.errors import ValidationError

            raise ValidationError("Ya existe un registro para este animal en ese día/turno")
        bid = updates.get("buyer_id", existing.buyer_id)
        vol = updates.get("volume_l", existing.volume_l)
        price = None
        currency = existing.currency
        if bid is not None:
            p = await uow.milk_prices.get_for_date(context.tenant_id, dt.date(), bid)
            if p is not None:
                price = p.price_per_l
                currency = p.currency
        if price is None:
            p = await uow.milk_prices.get_for_date(context.tenant_id, dt.date(), None)
            if p is not None:
                price = p.price_per_l
                currency = p.currency
        if price is None:
            cfg = await uow.tenant_config.get(context.tenant_id)
            if cfg and cfg.default_price_per_l is not None:
                price = cfg.default_price_per_l
                currency = cfg.default_currency

        # Final fallback: use most recent price if no other price is found
        if price is None:
            most_recent_price = await uow.milk_prices.get_most_recent(context.tenant_id)
            if most_recent_price:
                price = most_recent_price.price_per_l
                currency = most_recent_price.currency
        if price is not None:
            updates["price_snapshot"] = price
            updates["currency"] = currency
            updates["amount"] = (vol * price).quantize(Decimal("0.01"))
    updated = await uow.milk_productions.update(context.tenant_id, _UUID(production_id), updates)
    if not updated:
        from src.application.errors import NotFound

        raise NotFound("Production not found")
    await uow.commit()
    return MilkProductionResponse.model_validate(updated)


@router.delete("/{production_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_production(
    production_id: str, context: AuthContext = Depends(get_auth_context), uow=Depends(get_uow)
):
    if not context.role.can_delete():
        raise PermissionDenied("Role not allowed to delete productions")
    from uuid import UUID as _UUID

    ok = await uow.milk_productions.delete(context.tenant_id, _UUID(production_id))
    if not ok:
        from src.application.errors import NotFound

        raise NotFound("Production not found")
    await uow.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
