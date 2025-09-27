from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.infrastructure.auth.context import AuthContext
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.animal_statuses import AnimalStatusResponse

router = APIRouter(prefix="/animals/statuses", tags=["animal-statuses"])


@router.get("/list", response_model=list[AnimalStatusResponse])
async def list_animal_statuses(
    lang: str = Query("es", description="Language code (es, en)"),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> list[AnimalStatusResponse]:
    statuses = await uow.animal_statuses.list_for_tenant(context.tenant_id)

    return [
        AnimalStatusResponse(
            id=status.id,
            code=status.code,
            name=status.get_name(lang),
            description=status.get_description(lang),
            is_system_default=status.is_system_default,
        )
        for status in statuses
    ]
