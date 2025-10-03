from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from src.application.use_cases.animals import list_lactations
from src.infrastructure.auth.context import AuthContext
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.lactations import (
    LactationResponse,
    LactationsListResponse,
)

router = APIRouter(tags=["lactations"])


@router.get(
    "/animals/{animal_id}/lactations",
    response_model=LactationsListResponse,
)
async def get_animal_lactations(
    animal_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> LactationsListResponse:
    """Get all lactations for an animal with production metrics.

    Returns lactations ordered by number (most recent first) with:
    - Total volume in liters
    - Days in milk
    - Average daily production
    - Production count
    """
    lactations_with_metrics = await list_lactations.execute(
        uow=uow,
        tenant_id=context.tenant_id,
        role=context.role,
        animal_id=animal_id,
    )

    items = []
    for lm in lactations_with_metrics:
        lactation_response = LactationResponse.model_validate(lm.lactation)
        lactation_response.total_volume_l = lm.total_volume_l
        lactation_response.days_in_milk = lm.days_in_milk
        lactation_response.average_daily_l = lm.average_daily_l
        lactation_response.production_count = lm.production_count
        items.append(lactation_response)

    return LactationsListResponse(items=items)


@router.get(
    "/lactations/{lactation_id}",
    response_model=LactationResponse,
)
async def get_lactation(
    lactation_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> LactationResponse:
    """Get details of a specific lactation with metrics."""
    async with uow:
        lactation = await uow.lactations.get(context.tenant_id, lactation_id)
        if not lactation:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Lactation not found")

        # Calculate metrics
        total_volume = await uow.lactations.sum_volume(lactation_id)

        from datetime import date
        from decimal import Decimal

        end_date = lactation.end_date if lactation.end_date else date.today()
        days_in_milk = (end_date - lactation.start_date).days

        average_daily = Decimal("0.0")
        if days_in_milk > 0:
            average_daily = Decimal(str(total_volume)) / Decimal(days_in_milk)

        response = LactationResponse.model_validate(lactation)
        response.total_volume_l = Decimal(str(total_volume))
        response.days_in_milk = days_in_milk
        response.average_daily_l = average_daily
        response.production_count = 0  # TODO: implement count

        return response
