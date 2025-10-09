from __future__ import annotations

from datetime import date as DtDate
from datetime import datetime, timezone
from datetime import time as DtTime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response, status

from src.application.errors import PermissionDenied
from src.application.events.dispatcher import dispatch_events
from src.application.events.models import (
    ProductionBulkRecordedEvent,
    ProductionLowEvent,
    ProductionRecordedEvent,
)
from src.domain.models.milk_production import MilkProduction
from src.domain.value_objects.owner_type import OwnerType
from src.infrastructure.auth.context import AuthContext
from src.interfaces.http.deps import (
    get_auth_context,
    get_uow,
)
from src.interfaces.http.schemas.attachments import PresignUploadRequest, PresignUploadResponse
from src.interfaces.http.schemas.milk_productions import (
    MilkProductionCreate,
    MilkProductionListResponse,
    MilkProductionResponse,
    MilkProductionsBulkCreate,
    MilkProductionUpdate,
    ProcessOcrRequest,
    ProcessOcrResponse,
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
    background_tasks: BackgroundTasks,
    request: Request,
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

    # Get animal details for notification
    await uow.animals.get(context.tenant_id, payload.animal_id)

    # Default event: production recorded
    event: ProductionRecordedEvent | ProductionLowEvent = ProductionRecordedEvent(
        tenant_id=context.tenant_id,
        actor_user_id=context.user_id,
        production_id=created.id,
        animal_id=payload.animal_id,
        volume_l=vol_l,
        shift=shift_val,
        date=dt.date(),
    )

    # Check for low production: below this animal's recent average (last 30 days, excluding today)
    from datetime import timedelta

    try:
        date_from = dt.date() - timedelta(days=30)
        date_to = dt.date() - timedelta(days=1)
        history = await uow.milk_productions.list(
            context.tenant_id,
            date_from=date_from,
            date_to=date_to,
            animal_id=payload.animal_id,
        )
        if history:
            total_hist = sum(h.volume_l for h in history)
            avg_hist = (total_hist / len(history)) if len(history) > 0 else None
            if avg_hist is not None and vol_l < avg_hist:
                event = ProductionLowEvent(
                    tenant_id=context.tenant_id,
                    actor_user_id=context.user_id,
                    production_id=created.id,
                    animal_id=payload.animal_id,
                    volume_l=vol_l,
                    avg_hist=float(f"{avg_hist:.2f}"),
                    shift=shift_val,
                    date=dt.date(),
                )
    except Exception:
        # If averaging fails, fallback to normal notification without raising
        pass

    # Emit event and commit
    uow.add_event(event)
    events = uow.drain_events()
    await uow.commit()

    # Dispatch post-commit in background
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is not None:
        background_tasks.add_task(dispatch_events, session_factory, events)
    return MilkProductionResponse.model_validate(created)


@router.post(
    "/bulk", response_model=list[MilkProductionResponse], status_code=status.HTTP_201_CREATED
)
async def create_productions_bulk(
    payload: MilkProductionsBulkCreate,
    background_tasks: BackgroundTasks,
    request: Request,
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

    # Emitir evento de registro masivo
    total_volume = sum(Decimal(r.volume_l) for r in results)
    uow.add_event(
        ProductionBulkRecordedEvent(
            tenant_id=context.tenant_id,
            actor_user_id=context.user_id,
            count=len(results),
            total_volume_l=str(total_volume),
            shift=shift_val,
            date=dt_shared.date(),
        )
    )

    events = uow.drain_events()
    await uow.commit()

    # Despachar post-commit en background
    if request is not None:
        session_factory = getattr(request.app.state, "session_factory", None)
        if session_factory is not None:
            background_tasks.add_task(dispatch_events, session_factory, events)
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


# OCR endpoints
@router.post("/ocr/uploads", response_model=PresignUploadResponse)
async def presign_ocr_upload(
    payload: PresignUploadRequest,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
) -> PresignUploadResponse:
    """Generate presigned URL for OCR image upload."""
    import uuid

    # Generate unique file ID for the upload
    file_id = uuid.uuid4()
    file_ext = payload.content_type.split("/")[-1] if "/" in payload.content_type else "jpg"
    storage_key = f"tenants/{context.tenant_id}/" f"milk-productions/ocr/{file_id}.{file_ext}"
    try:
        svc = request.app.state.storage_service
    except AttributeError as exc:
        raise RuntimeError("Storage service not configured") from exc
    presigned = await svc.get_presigned_upload(storage_key, payload.content_type)
    return PresignUploadResponse(
        upload_url=presigned.upload_url,
        storage_key=presigned.storage_key,
        fields=presigned.fields,
    )


@router.post("/ocr/process", response_model=ProcessOcrResponse, status_code=status.HTTP_200_OK)
async def process_ocr_image(
    payload: ProcessOcrRequest,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> ProcessOcrResponse:
    """Process OCR image with OpenAI and match with animals in lactation."""
    import re
    from decimal import Decimal
    from uuid import UUID

    from src.application.errors import ValidationError
    from src.config.settings import get_settings
    from src.domain.models.attachment import Attachment
    from src.infrastructure.services.openai_service import OpenAIService

    if not context.role.can_create():
        raise PermissionDenied("Role not allowed to process OCR")

    settings = get_settings()

    # Extract file UUID from storage_key to use as owner_id
    # storage_key format: "{env}/tenants/{tenant_id}/milk-productions/ocr/{file_uuid}.{ext}"
    # The key contains at least two UUIDs; we want the one after "ocr/" (the last one)
    uuid_pattern = r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    all_uuids = re.findall(uuid_pattern, payload.storage_key, flags=re.IGNORECASE)
    if not all_uuids:
        raise ValidationError("Invalid storage_key format: UUID not found")
    try:
        file_uuid = UUID(all_uuids[-1])
    except Exception as e:
        raise ValidationError("Invalid storage_key format: Bad UUID segment") from e

    # Create attachment record
    attachment = Attachment.create(
        tenant_id=context.tenant_id,
        owner_type=OwnerType.MILK_PRODUCTION_OCR,
        owner_id=file_uuid,  # Use S3 file UUID as owner_id
        kind="photo",
        storage_key=payload.storage_key,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
        title="OCR Milk Production",
        description="Photo processed for milk production OCR",
        is_primary=False,
        position=0,
    )
    created_attachment = await uow.attachments.add(attachment)

    # Get public URL for the image
    try:
        svc = request.app.state.storage_service
    except AttributeError as exc:
        raise RuntimeError("Storage service not configured") from exc
    image_url = await svc.get_public_url(payload.storage_key)

    # Extract milk records using OpenAI Vision API
    if not settings.openai_api_key:
        raise ValidationError("OpenAI API key not configured")

    openai_service = OpenAIService(api_key=settings.openai_api_key.get_secret_value())

    try:
        extracted_records = await openai_service.extract_milk_records(image_url)
    except ValueError as e:
        raise ValidationError(f"Failed to process image: {str(e)}") from e
    except Exception as e:
        raise ValidationError(f"OpenAI processing error: {str(e)}") from e

    # Get animals in lactation for matching
    # First get the LACTATING status ID
    statuses = await uow.animal_statuses.list_for_tenant(context.tenant_id)
    lactating_status = next((s for s in statuses if s.code == "LACTATING"), None)

    if lactating_status:
        animals_result = await uow.animals.list(
            context.tenant_id, status_ids=[lactating_status.id], limit=None
        )
        # Handle tuple return (list with cursor)
        animals = animals_result[0] if isinstance(animals_result, tuple) else animals_result
    else:
        # Fallback: get all animals if LACTATING status not found
        animals_result = await uow.animals.list(context.tenant_id, limit=None)
        animals = animals_result[0] if isinstance(animals_result, tuple) else animals_result

    # Perform fuzzy name matching
    from src.interfaces.http.schemas.milk_productions import (
        OcrMatchedResult,
        OcrUnmatchedResult,
    )

    matched = []
    unmatched = []

    for extracted in extracted_records:
        best_match = None
        best_score = 0.0

        # Simple name matching (TODO: improve with fuzzy matching library like fuzzywuzzy)
        for animal in animals:
            # Check both name and tag
            name_lower = (animal.name or "").lower()
            tag_lower = (animal.tag or "").lower()
            extracted_lower = extracted["name"].lower()

            # Exact match
            if extracted_lower == name_lower or extracted_lower == tag_lower:
                best_match = animal
                best_score = 1.0
                break

            # Partial match
            if extracted_lower in name_lower or name_lower in extracted_lower:
                score = 0.8
                if score > best_score:
                    best_match = animal
                    best_score = score

        if best_match and best_score > 0.7:
            matched.append(
                OcrMatchedResult(
                    animal_id=best_match.id,
                    animal_name=best_match.name or "",
                    animal_tag=best_match.tag or "",
                    liters=Decimal(str(extracted["liters"])),
                    match_confidence=best_score,
                    extracted_name=extracted["name"],
                )
            )
        else:
            # Find suggestions (top 3 closest matches)
            suggestions = []
            for animal in animals[:3]:
                suggestions.append(
                    {
                        "animal_id": str(animal.id),
                        "name": animal.name or "",
                        "similarity": 0.5,
                    }
                )
            unmatched.append(
                OcrUnmatchedResult(
                    extracted_name=extracted["name"],
                    liters=Decimal(str(extracted["liters"])),
                    suggestions=suggestions,
                )
            )

    # Update attachment metadata with OCR results
    await uow.attachments.update_metadata(
        context.tenant_id,
        created_attachment.id,
        title="OCR Milk Production - Processed",
        description=f"Extracted {len(extracted_records)} records, matched {len(matched)}",
    )

    await uow.commit()

    return ProcessOcrResponse(
        image_url=image_url,
        attachment_id=created_attachment.id,
        matched=matched,
        unmatched=unmatched,
        total_extracted=len(extracted_records),
    )
