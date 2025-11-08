from __future__ import annotations

from datetime import date as DtDate
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response, status

from src.application.use_cases.animals import (
    create_animal,
    delete_animal,
    get_animal,
    list_animals,
    update_animal,
)
from src.domain.value_objects.owner_type import OwnerType
from src.infrastructure.auth.context import AuthContext
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.animals import (
    AnimalCreate,
    AnimalResponse,
    AnimalsListResponse,
    AnimalUpdate,
    AnimalValueResponse,
)
from src.interfaces.http.schemas.attachments import (
    AttachmentResponse,
    CreatePhotoRequest,
    PresignUploadRequest,
    PresignUploadResponse,
)

router = APIRouter(prefix="/animals", tags=["animals"])


@router.get("/next-tag")
async def get_next_tag(
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> dict[str, str]:
    """Generate next available tag number for the tenant."""
    # Get all animals for tenant using pagination
    all_animals = []
    cursor = None

    while True:
        result = await list_animals.execute(
            uow,
            context.tenant_id,
            limit=100,
            cursor=cursor,
            status_codes=None,
        )
        all_animals.extend(result.items)

        if result.next_cursor is None:
            break
        cursor = result.next_cursor

    # Find numeric tags and get the maximum
    numeric_tags = []
    for animal in all_animals:
        try:
            # Try to parse tag as integer
            tag_num = int(animal.tag)
            numeric_tags.append(tag_num)
        except (ValueError, AttributeError):
            # Skip non-numeric tags
            pass

    # Generate next tag
    if numeric_tags:
        next_num = max(numeric_tags) + 1
    else:
        next_num = 1

    # Format with leading zeros (e.g., "001", "002", etc.)
    next_tag = str(next_num).zfill(3)

    return {"next_tag": next_tag}


@router.get("/", response_model=AnimalsListResponse)
async def list_animals_endpoint(
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
    offset: int | None = Query(None, ge=0),
    sort_by: str | None = Query(
        None,
        description="Sort by one of: tag, name, breed, age, lot, classification",
    ),
    sort_dir: str | None = Query(None, description="Sort direction: asc or desc (default asc)"),
    status_codes: list[str] = Query(
        None, description="Filter by status codes. Repeat param or use comma-separated"
    ),
    q: str | None = Query(
        None,
        description="Text search across tag, name, breed, lot",
    ),
    search: str | None = Query(
        None,
        description="Alias of q for text search",
    ),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AnimalsListResponse:
    cursor_uuid = UUID(cursor) if cursor else None
    # Normalize comma-separated single value into list
    if status_codes and len(status_codes) == 1 and "," in status_codes[0]:
        status_codes = [code.strip() for code in status_codes[0].split(",") if code.strip()]

    # Resolve search term preferring q, then search
    text_search = q if q is not None else search

    result = await list_animals.execute(
        uow,
        context.tenant_id,
        limit=limit,
        cursor=cursor_uuid,
        offset=offset,
        status_codes=status_codes,
        sort_by=sort_by,
        sort_dir=sort_dir,
        search=text_search,
    )
    # Enrich with primary_photo_url, photos_count, and
    # status fields (code, text, description)
    # Load statuses if table exists; otherwise continue
    # without them (tests may not have seeded/migrated)
    try:
        statuses = await uow.animal_statuses.list_for_tenant(context.tenant_id)
        status_by_id = {s.id: s for s in statuses}
    except Exception:
        status_by_id = {}
    # Preload breeds and lots to enrich IDs by name (best-effort)
    try:
        breeds = await uow.breeds.list_for_tenant(context.tenant_id)
        breed_by_name = {b.name.lower(): b for b in breeds}
    except Exception:
        breed_by_name = {}
    try:
        lots = await uow.lots.list_for_tenant(context.tenant_id)
        lot_by_name = {lot.name.lower(): lot for lot in lots}
    except Exception:
        lot_by_name = {}

    enriched_items = []
    for item in result.items:
        primary = await uow.attachments.get_primary_for_owner(
            context.tenant_id, OwnerType.ANIMAL, item.id
        )
        count = await uow.attachments.count_for_owner(context.tenant_id, OwnerType.ANIMAL, item.id)
        data = AnimalResponse.model_validate(item).model_dump()
        # add derived status details
        sid = data.get("status_id")
        if sid and sid in status_by_id:
            status = status_by_id[sid]
            data["status_code"] = status.code
            # default to Spanish for now; later can use Accept-Language or query param
            data["status"] = status.get_name("es")
            data["status_desc"] = status.get_description("es")
        else:
            data["status_code"] = None
            data["status"] = None
            data["status_desc"] = None
        data["photo_url"] = primary.storage_key if primary else None  # backward compat
        # Add breed_id / lot_id by name match (optional enrichment)
        if data.get("breed"):
            b = breed_by_name.get(str(data["breed"]).lower())
            if b:
                data["breed_id"] = b.id
        if data.get("lot"):
            lot_obj = lot_by_name.get(str(data["lot"]).lower())
            if lot_obj:
                data["lot_id"] = lot_obj.id
        data["primary_photo_url"] = primary.storage_key if primary else None
        data["photos_count"] = count
        enriched_items.append(AnimalResponse.model_validate(data))
    items = enriched_items
    next_cursor = str(result.next_cursor) if result.next_cursor else None
    return AnimalsListResponse(items=items, next_cursor=next_cursor, total=result.total)


@router.post("/", response_model=AnimalResponse, status_code=status.HTTP_201_CREATED)
async def create_animal_endpoint(
    payload: AnimalCreate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AnimalResponse:
    # Try to resolve legacy status string to status_id if provided
    status_id = payload.status_id
    if status_id is None and getattr(payload, "status", None):
        try:
            s = await uow.animal_statuses.get_by_code(context.tenant_id, payload.status)  # type: ignore[arg-type]
            if s:
                status_id = s.id
        except Exception:
            # Ignore mapping errors in environments without statuses table
            pass

    # Resolve optional breed_id / lot_id to legacy name fields
    breed_name = payload.breed
    try:
        if getattr(payload, "breed_id", None):
            b = await uow.breeds.get(context.tenant_id, payload.breed_id)
            if not b or not b.active:
                from fastapi import HTTPException

                raise HTTPException(status_code=400, detail="Invalid breed_id")
            breed_name = b.name
    except Exception:
        pass

    lot_name = payload.lot
    try:
        if getattr(payload, "lot_id", None):
            lot_obj = await uow.lots.get(context.tenant_id, payload.lot_id)
            if not lot_obj or not lot_obj.active:
                from fastapi import HTTPException

                raise HTTPException(status_code=400, detail="Invalid lot_id")
            lot_name = lot_obj.name
    except Exception:
        pass

    result = await create_animal.execute(
        uow,
        context.tenant_id,
        context.role,
        create_animal.CreateAnimalInput(
            tag=payload.tag,
            name=payload.name,
            breed=breed_name,
            breed_variant=payload.breed_variant,
            breed_id=getattr(payload, "breed_id", None),
            birth_date=payload.birth_date,
            lot=lot_name,
            current_lot_id=getattr(payload, "lot_id", None),
            status_id=status_id,
            photo_url=payload.photo_url,
            labels=payload.labels,
            # Genealogy fields
            sex=payload.sex,
            dam_id=payload.dam_id,
            sire_id=payload.sire_id,
            external_sire_code=payload.external_sire_code,
            external_sire_registry=payload.external_sire_registry,
        ),
    )
    # Enrich response with legacy status fallback if enrichment cannot be done later
    data = AnimalResponse.model_validate(result).model_dump()
    if data.get("status") is None and getattr(payload, "status", None):
        data["status"] = payload.status
    # best-effort IDs
    try:
        if data.get("breed"):
            b = await uow.breeds.find_by_name(context.tenant_id, data["breed"])  # type: ignore[arg-type]
            if b:
                data["breed_id"] = b.id
        if data.get("lot"):
            lot = await uow.lots.find_by_name(context.tenant_id, data["lot"])  # type: ignore[arg-type]
            if lot:
                data["lot_id"] = lot.id
    except Exception:
        pass
    return AnimalResponse.model_validate(data)


@router.get("/{animal_id}", response_model=AnimalResponse)
async def get_animal_endpoint(
    animal_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AnimalResponse:
    result = await get_animal.execute(uow, context.tenant_id, animal_id)
    primary = await uow.attachments.get_primary_for_owner(
        context.tenant_id, OwnerType.ANIMAL, animal_id
    )
    data = AnimalResponse.model_validate(result).model_dump()
    # add derived status fields
    if data.get("status_id"):
        try:
            statuses = await uow.animal_statuses.list_for_tenant(context.tenant_id)
            status_by_id = {s.id: s for s in statuses}
            s = status_by_id.get(data["status_id"])  # may be None if missing
            if s:
                data["status_code"] = s.code
                data["status"] = s.get_name("es")
                data["status_desc"] = s.get_description("es")
        except Exception:
            # If statuses table is missing in certain environments/tests, skip enrichment
            pass
    data["photo_url"] = primary.storage_key if primary else None
    return AnimalResponse.model_validate(data)


@router.put("/{animal_id}", response_model=AnimalResponse)
async def update_animal_endpoint(
    animal_id: UUID,
    payload: AnimalUpdate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AnimalResponse:
    # Try to resolve legacy status string to status_id if provided
    status_id = payload.status_id
    if status_id is None and getattr(payload, "status", None):
        try:
            s = await uow.animal_statuses.get_by_code(context.tenant_id, payload.status)  # type: ignore[arg-type]
            if s:
                status_id = s.id
        except Exception:
            pass

    # Resolve optional breed_id / lot_id
    updates = {
        "version": payload.version,
        "name": payload.name,
        "breed": payload.breed,
        "breed_variant": payload.breed_variant,
        "breed_id": getattr(payload, "breed_id", None),
        "birth_date": payload.birth_date,
        "lot": payload.lot,
        "current_lot_id": getattr(payload, "lot_id", None),
        "status_id": status_id,
        "photo_url": payload.photo_url,
        "labels": payload.labels,
        # Genealogy fields
        "sex": payload.sex,
        "dam_id": payload.dam_id,
        "sire_id": payload.sire_id,
        "external_sire_code": payload.external_sire_code,
        "external_sire_registry": payload.external_sire_registry,
    }
    try:
        if getattr(payload, "breed_id", None):
            b = await uow.breeds.get(context.tenant_id, payload.breed_id)
            if not b or not b.active:
                from fastapi import HTTPException

                raise HTTPException(status_code=400, detail="Invalid breed_id")
            updates["breed"] = b.name
    except Exception:
        pass
    try:
        if getattr(payload, "lot_id", None):
            lot_obj = await uow.lots.get(context.tenant_id, payload.lot_id)
            if not lot_obj or not lot_obj.active:
                from fastapi import HTTPException

                raise HTTPException(status_code=400, detail="Invalid lot_id")
            updates["lot"] = lot_obj.name
    except Exception:
        pass

    result = await update_animal.execute(
        uow,
        context.tenant_id,
        context.role,
        animal_id,
        update_animal.UpdateAnimalInput(**updates),
    )
    data = AnimalResponse.model_validate(result).model_dump()
    if data.get("status") is None and getattr(payload, "status", None):
        data["status"] = payload.status
    # best-effort IDs
    try:
        if data.get("breed"):
            b = await uow.breeds.find_by_name(context.tenant_id, data["breed"])  # type: ignore[arg-type]
            if b:
                data["breed_id"] = b.id
        if data.get("lot"):
            lot = await uow.lots.find_by_name(context.tenant_id, data["lot"])  # type: ignore[arg-type]
            if lot:
                data["lot_id"] = lot.id
    except Exception:
        pass
    return AnimalResponse.model_validate(data)


@router.put("/{animal_id}/lot", response_model=AnimalResponse)
async def set_animal_lot(
    animal_id: UUID,
    payload: dict,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AnimalResponse:
    from pydantic import BaseModel

    class SetLotPayload(BaseModel):
        lot_id: UUID | None
        version: int

    req = SetLotPayload(**payload)
    lot_name: str | None = None
    if req.lot_id is not None:
        lot = await uow.lots.get(context.tenant_id, req.lot_id)
        if not lot or not lot.active:
            from src.application.errors import ValidationError

            raise ValidationError("Invalid lot_id")
        lot_name = lot.name

    result = await update_animal.execute(
        uow,
        context.tenant_id,
        context.role,
        animal_id,
        update_animal.UpdateAnimalInput(
            version=req.version,
            lot=lot_name,
            current_lot_id=req.lot_id,
        ),
    )
    data = AnimalResponse.model_validate(result).model_dump()
    # Enrich lot_id
    if lot_name:
        data["lot_id"] = req.lot_id
    else:
        data["lot_id"] = None
    return AnimalResponse.model_validate(data)


@router.delete("/{animal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_animal_endpoint(
    animal_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> Response:
    await delete_animal.execute(uow, context.tenant_id, context.role, animal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _round2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@router.get("/{animal_id}/value", response_model=AnimalValueResponse)
async def animal_value_for_date(
    animal_id: UUID,
    date: str = Query(description="ISO date, e.g. 2025-01-01"),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AnimalValueResponse:
    the_date = DtDate.fromisoformat(date)
    prods = await uow.milk_productions.list(
        context.tenant_id, date_from=the_date, date_to=the_date, animal_id=animal_id
    )
    total_l = sum((p.volume_l for p in prods), Decimal("0"))
    # Resolve price from actual deliveries (weighted avg), else from price table/defaults
    deliveries = await uow.milk_deliveries.list(
        context.tenant_id, date_from=the_date, date_to=the_date, buyer_id=None
    )
    price: Decimal | None = None
    currency = "USD"
    source = "deliveries_average"
    if deliveries:
        total_amount = sum((d.amount for d in deliveries), Decimal("0"))
        total_deliv_l = sum((d.volume_l for d in deliveries), Decimal("0"))
        if total_deliv_l > 0:
            price = (total_amount / total_deliv_l).quantize(Decimal("0.0001"))
            currency = deliveries[0].currency
    if price is None:
        # Fallback to configured daily price (prefer default buyer if configured)
        source = "price_daily"
        cfg = await uow.tenant_config.get(context.tenant_id)
        buyer_id = cfg.default_buyer_id if cfg else None
        mp = await uow.milk_prices.get_for_date(context.tenant_id, the_date, buyer_id)
        if mp is None:
            mp = await uow.milk_prices.get_for_date(context.tenant_id, the_date, None)
        if mp is not None:
            price = mp.price_per_l
            currency = mp.currency
        else:
            source = "tenant_default"
            if cfg and cfg.default_price_per_l is not None:
                price = cfg.default_price_per_l
                currency = cfg.default_currency
    if price is None:
        from src.application.errors import ValidationError

        raise ValidationError(
            "No price available for this date (no deliveries, no daily price, no tenant default)"
        )
    amount = _round2(total_l * price)
    return AnimalValueResponse(
        animal_id=animal_id,
        date=the_date,
        total_volume_l=total_l,
        price_per_l=price,
        currency=currency,
        amount=amount,
        source=source,
    )


@router.post("/{animal_id}/photos/uploads", response_model=PresignUploadResponse)
async def presign_photo_upload(
    animal_id: UUID,
    payload: PresignUploadRequest,
    background: BackgroundTasks,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> PresignUploadResponse:
    import uuid

    # Generate unique file ID for the upload
    file_id = uuid.uuid4()
    storage_key = f"tenants/{context.tenant_id}/animals/{animal_id}/uploads/{file_id}"
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


@router.post(
    "/{animal_id}/photos",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_photo(
    animal_id: UUID,
    payload: CreatePhotoRequest,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AttachmentResponse:
    from src.domain.models.attachment import Attachment

    if not context.role.can_update():
        from src.application.errors import PermissionDenied

        raise PermissionDenied("Role not allowed to upload photos")
    attachment = Attachment.create(
        tenant_id=context.tenant_id,
        owner_type=OwnerType.ANIMAL,
        owner_id=animal_id,
        kind="photo",
        storage_key=payload.storage_key,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
        title=payload.title,
        description=payload.description,
        is_primary=payload.is_primary,
        position=payload.position,
    )
    created = await uow.attachments.add(attachment)
    if payload.is_primary:
        await uow.attachments.set_primary(
            context.tenant_id, OwnerType.ANIMAL, animal_id, created.id
        )
    await uow.commit()
    try:
        svc = request.app.state.storage_service
    except AttributeError as exc:
        raise RuntimeError("Storage service not configured") from exc
    url = await svc.get_public_url(created.storage_key)
    return AttachmentResponse(
        id=created.id,
        url=url,
        title=created.title,
        description=created.description,
        is_primary=created.is_primary,
        position=created.position,
        mime_type=created.mime_type,
        size_bytes=created.size_bytes,
        created_at=created.created_at,
    )


@router.get("/{animal_id}/photos", response_model=list[AttachmentResponse])
async def list_photos(
    animal_id: UUID,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> list[AttachmentResponse]:
    try:
        svc = request.app.state.storage_service
    except AttributeError as exc:
        raise RuntimeError("Storage service not configured") from exc
    items = await uow.attachments.list_for_owner(context.tenant_id, OwnerType.ANIMAL, animal_id)
    results: list[AttachmentResponse] = []
    for a in items:
        url = await svc.get_public_url(a.storage_key)
        results.append(
            AttachmentResponse(
                id=a.id,
                url=url,
                title=a.title,
                description=a.description,
                is_primary=a.is_primary,
                position=a.position,
                mime_type=a.mime_type,
                size_bytes=a.size_bytes,
                created_at=a.created_at,
            )
        )
    return results


@router.put("/{animal_id}/photos/{photo_id}", response_model=AttachmentResponse)
async def update_photo(
    animal_id: UUID,
    photo_id: UUID,
    payload: CreatePhotoRequest,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AttachmentResponse:
    if not context.role.can_update():
        from src.application.errors import PermissionDenied

        raise PermissionDenied("Role not allowed to update photos")
    updated = await uow.attachments.update_metadata(
        context.tenant_id,
        photo_id,
        title=payload.title,
        description=payload.description,
        position=payload.position,
        is_primary=payload.is_primary,
    )
    if not updated:
        from src.application.errors import NotFound

        raise NotFound("Photo not found")
    if payload.is_primary:
        await uow.attachments.set_primary(context.tenant_id, OwnerType.ANIMAL, animal_id, photo_id)
        await uow.commit()
    try:
        svc = request.app.state.storage_service
    except AttributeError as exc:
        raise RuntimeError("Storage service not configured") from exc
    url = await svc.get_public_url(updated.storage_key)
    return AttachmentResponse(
        id=updated.id,
        url=url,
        title=updated.title,
        description=updated.description,
        is_primary=updated.is_primary,
        position=updated.position,
        mime_type=updated.mime_type,
        size_bytes=updated.size_bytes,
        created_at=updated.created_at,
    )


@router.delete("/{animal_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    animal_id: UUID,
    photo_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> Response:
    if not context.role.can_delete():
        from src.application.errors import PermissionDenied

        raise PermissionDenied("Role not allowed to delete photos")
    ok = await uow.attachments.soft_delete(context.tenant_id, photo_id)
    if not ok:
        from src.application.errors import NotFound

        raise NotFound("Photo not found")
    await uow.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/labels/suggestions")
async def get_label_suggestions(
    q: str = Query("", description="Search query for labels"),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> list[str]:
    """Get label suggestions based on existing labels across all animals."""
    # Get all animals and collect unique labels
    all_labels: set[str] = set()
    cursor = None

    while True:
        result = await list_animals.execute(
            uow,
            context.tenant_id,
            limit=10,
            cursor=cursor,
            status_codes=None,
        )
        for animal in result.items:
            if hasattr(animal, "labels") and animal.labels:
                all_labels.update(animal.labels)

        if result.next_cursor is None:
            break
        cursor = result.next_cursor

    # Filter labels based on query (case-insensitive)
    if q:
        query_lower = q.lower()
        filtered = [label for label in all_labels if query_lower in label.lower()]
    else:
        filtered = list(all_labels)

    # Sort by popularity (you can enhance this later with actual counts)
    return sorted(filtered)[:20]  # Return top 20 matches
