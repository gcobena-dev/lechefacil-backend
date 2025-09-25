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


@router.get("/", response_model=AnimalsListResponse)
async def list_animals_endpoint(
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AnimalsListResponse:
    cursor_uuid = UUID(cursor) if cursor else None
    result = await list_animals.execute(
        uow,
        context.tenant_id,
        limit=limit,
        cursor=cursor_uuid,
    )
    # Enrich with primary_photo_url and photos_count
    enriched_items = []
    for item in result.items:
        primary = await uow.attachments.get_primary_for_owner(
            context.tenant_id, OwnerType.ANIMAL, item.id
        )
        count = await uow.attachments.count_for_owner(context.tenant_id, OwnerType.ANIMAL, item.id)
        data = AnimalResponse.model_validate(item).model_dump()
        data["photo_url"] = primary.storage_key if primary else None  # backward compat
        data["primary_photo_url"] = primary.storage_key if primary else None
        data["photos_count"] = count
        enriched_items.append(AnimalResponse.model_validate(data))
    items = enriched_items
    next_cursor = str(result.next_cursor) if result.next_cursor else None
    return AnimalsListResponse(items=items, next_cursor=next_cursor)


@router.post("/", response_model=AnimalResponse, status_code=status.HTTP_201_CREATED)
async def create_animal_endpoint(
    payload: AnimalCreate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AnimalResponse:
    result = await create_animal.execute(
        uow,
        context.tenant_id,
        context.role,
        create_animal.CreateAnimalInput(
            tag=payload.tag,
            name=payload.name,
            breed=payload.breed,
            birth_date=payload.birth_date,
            lot=payload.lot,
            status=payload.status,
            photo_url=payload.photo_url,
        ),
    )
    return AnimalResponse.model_validate(result)


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
    data["photo_url"] = primary.storage_key if primary else None
    return AnimalResponse.model_validate(data)


@router.put("/{animal_id}", response_model=AnimalResponse)
async def update_animal_endpoint(
    animal_id: UUID,
    payload: AnimalUpdate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AnimalResponse:
    result = await update_animal.execute(
        uow,
        context.tenant_id,
        context.role,
        animal_id,
        update_animal.UpdateAnimalInput(
            version=payload.version,
            name=payload.name,
            breed=payload.breed,
            birth_date=payload.birth_date,
            lot=payload.lot,
            status=payload.status,
            photo_url=payload.photo_url,
        ),
    )
    return AnimalResponse.model_validate(result)


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
    # For MVP we return a storage key scheme and a stub upload URL
    # placeholder for future injection of real storage service
    # Generate storage_key (no-op here, client will upload externally)
    storage_key = f"tenants/{context.tenant_id}/animals/{animal_id}/uploads/{{uuid}}"
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
    from src.infrastructure.storage.dev_stub import DevStubStorage

    svc = DevStubStorage()
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
