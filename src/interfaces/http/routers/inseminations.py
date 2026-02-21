from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from src.application.errors import PermissionDenied
from src.application.events.dispatcher import dispatch_events
from src.application.use_cases.reproduction import (
    get_pending_pregnancy_checks,
    list_inseminations,
    record_insemination,
    record_pregnancy_check,
)
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.inseminations import (
    InseminationCreate,
    InseminationListResponse,
    InseminationResponse,
    InseminationUpdate,
    PregnancyCheckInput,
)
from src.interfaces.middleware.auth_middleware import AuthContext

router = APIRouter(prefix="/reproduction/inseminations", tags=["reproduction"])


@router.post("", response_model=InseminationResponse, status_code=status.HTTP_201_CREATED)
async def create_insemination_endpoint(
    payload: InseminationCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    input_data = record_insemination.RecordInseminationInput(
        animal_id=payload.animal_id,
        service_date=payload.service_date,
        method=payload.method,
        sire_catalog_id=payload.sire_catalog_id,
        semen_inventory_id=payload.semen_inventory_id,
        technician=payload.technician,
        straw_count=payload.straw_count,
        heat_detected=payload.heat_detected,
        protocol=payload.protocol,
        notes=payload.notes,
    )
    result = await record_insemination.execute(
        uow, context.tenant_id, input_data, actor_user_id=context.user_id
    )
    await uow.commit()

    # Dispatch notifications in background (post-commit)
    events = uow.drain_events()
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory and events:
        background_tasks.add_task(dispatch_events, session_factory, events)

    return result.insemination


@router.get("", response_model=InseminationListResponse)
async def list_inseminations_endpoint(
    animal_id: UUID | None = None,
    sire_catalog_id: UUID | None = None,
    pregnancy_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    result = await list_inseminations.execute(
        uow,
        context.tenant_id,
        animal_id=animal_id,
        sire_catalog_id=sire_catalog_id,
        pregnancy_status=pregnancy_status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    # Enrich with animal tag/name and sire name
    animal_ids = {ins.animal_id for ins in result.items}
    animals_map = {}
    for aid in animal_ids:
        animal = await uow.animals.get(context.tenant_id, aid)
        if animal:
            animals_map[aid] = animal

    sire_ids = {ins.sire_catalog_id for ins in result.items if ins.sire_catalog_id}
    sires_map = {}
    for sid in sire_ids:
        sire = await uow.sire_catalog.get(context.tenant_id, sid)
        if sire:
            sires_map[sid] = sire

    enriched = []
    for ins in result.items:
        data = InseminationResponse.model_validate(ins)
        animal = animals_map.get(ins.animal_id)
        if animal:
            data.animal_tag = animal.tag
            data.animal_name = animal.name
        sire = sires_map.get(ins.sire_catalog_id) if ins.sire_catalog_id else None
        if sire:
            data.sire_name = sire.name
        enriched.append(data)

    return {
        "items": enriched,
        "total": result.total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/pending-checks", response_model=list[InseminationResponse])
async def pending_pregnancy_checks_endpoint(
    min_days: int = 35,
    max_days: int = 50,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    items = await get_pending_pregnancy_checks.execute(
        uow, context.tenant_id, min_days=min_days, max_days=max_days
    )

    # Enrich with animal tag/name and sire name
    animal_ids = {ins.animal_id for ins in items}
    animals_map = {}
    for aid in animal_ids:
        animal = await uow.animals.get(context.tenant_id, aid)
        if animal:
            animals_map[aid] = animal

    sire_ids = {ins.sire_catalog_id for ins in items if ins.sire_catalog_id}
    sires_map = {}
    for sid in sire_ids:
        sire = await uow.sire_catalog.get(context.tenant_id, sid)
        if sire:
            sires_map[sid] = sire

    enriched = []
    for ins in items:
        data = InseminationResponse.model_validate(ins)
        animal = animals_map.get(ins.animal_id)
        if animal:
            data.animal_tag = animal.tag
            data.animal_name = animal.name
        sire = sires_map.get(ins.sire_catalog_id) if ins.sire_catalog_id else None
        if sire:
            data.sire_name = sire.name
        enriched.append(data)

    return enriched


@router.get("/{insemination_id}", response_model=InseminationResponse)
async def get_insemination_endpoint(
    insemination_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    record = await uow.inseminations.get(context.tenant_id, insemination_id)
    if not record:
        raise HTTPException(status_code=404, detail="Insemination not found")
    return record


@router.put("/{insemination_id}", response_model=InseminationResponse)
async def update_insemination_endpoint(
    insemination_id: UUID,
    payload: InseminationUpdate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    if not context.role.can_update():
        raise PermissionDenied("Role not allowed to update inseminations")
    record = await uow.inseminations.get(context.tenant_id, insemination_id)
    if not record:
        raise HTTPException(status_code=404, detail="Insemination not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "technician" in update_data:
        record.technician = update_data["technician"]
    if "notes" in update_data:
        record.notes = update_data["notes"]
    if "heat_detected" in update_data:
        record.heat_detected = update_data["heat_detected"]
    if "protocol" in update_data:
        record.protocol = update_data["protocol"]

    record.bump_version()
    updated = await uow.inseminations.update(record)
    await uow.commit()
    return updated


@router.delete("/{insemination_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_insemination_endpoint(
    insemination_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    if not context.role.can_delete():
        raise PermissionDenied("Role not allowed to delete inseminations")
    record = await uow.inseminations.get(context.tenant_id, insemination_id)
    if not record:
        raise HTTPException(status_code=404, detail="Insemination not found")
    record.deleted_at = datetime.now(timezone.utc)
    await uow.inseminations.delete(record)
    await uow.commit()
    return None


@router.post("/{insemination_id}/pregnancy-check", response_model=InseminationResponse)
async def pregnancy_check_endpoint(
    insemination_id: UUID,
    payload: PregnancyCheckInput,
    background_tasks: BackgroundTasks,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    input_data = record_pregnancy_check.RecordPregnancyCheckInput(
        insemination_id=insemination_id,
        result=payload.result,
        check_date=payload.check_date,
        checked_by=payload.checked_by,
    )
    result = await record_pregnancy_check.execute(
        uow, context.tenant_id, input_data, actor_user_id=context.user_id
    )
    await uow.commit()

    # Dispatch notifications in background (post-commit)
    events = uow.drain_events()
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory and events:
        background_tasks.add_task(dispatch_events, session_factory, events)

    return result
