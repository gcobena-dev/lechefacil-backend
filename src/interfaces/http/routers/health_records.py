from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.use_cases.health import (
    create_health_record,
    delete_health_record,
    list_health_records,
    update_health_record,
)
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.health_records import (
    HealthRecordCreate,
    HealthRecordListResponse,
    HealthRecordResponse,
    HealthRecordUpdate,
)
from src.interfaces.middleware.auth_middleware import AuthContext

router = APIRouter(prefix="/animals/{animal_id}/health", tags=["health"])


@router.post("", response_model=HealthRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_health_record_endpoint(
    animal_id: UUID,
    payload: HealthRecordCreate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    """Create a new health record for an animal."""

    input_data = create_health_record.CreateHealthRecordInput(
        animal_id=animal_id,
        event_type=payload.event_type,
        occurred_at=payload.occurred_at,
        veterinarian=payload.veterinarian,
        cost=payload.cost,
        notes=payload.notes,
        vaccine_name=payload.vaccine_name,
        next_dose_date=payload.next_dose_date,
        medication=payload.medication,
        duration_days=payload.duration_days,
        withdrawal_days=payload.withdrawal_days,
    )

    result = await create_health_record.execute(uow, context.tenant_id, input_data)
    await uow.commit()

    return result.health_record


@router.get("", response_model=HealthRecordListResponse)
async def list_health_records_endpoint(
    animal_id: UUID,
    limit: int = 50,
    offset: int = 0,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    """List health records for an animal."""

    result = await list_health_records.execute(uow, context.tenant_id, animal_id, limit, offset)

    return {
        "items": result.items,
        "total": result.total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{record_id}", response_model=HealthRecordResponse)
async def get_health_record_endpoint(
    animal_id: UUID,
    record_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    """Get a specific health record."""

    record = await uow.health_records.get(context.tenant_id, record_id)
    if not record or record.animal_id != animal_id:
        raise HTTPException(status_code=404, detail="Health record not found")

    return record


@router.put("/{record_id}", response_model=HealthRecordResponse)
async def update_health_record_endpoint(
    animal_id: UUID,
    record_id: UUID,
    payload: HealthRecordUpdate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    """Update a health record."""

    input_data = update_health_record.UpdateHealthRecordInput(
        record_id=record_id,
        **payload.model_dump(exclude_unset=True),
    )

    record = await update_health_record.execute(uow, context.tenant_id, input_data)
    await uow.commit()

    return record


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_health_record_endpoint(
    animal_id: UUID,
    record_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    """Delete a health record."""

    await delete_health_record.execute(uow, context.tenant_id, record_id)
    await uow.commit()
