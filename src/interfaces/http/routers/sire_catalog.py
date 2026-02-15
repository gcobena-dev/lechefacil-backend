from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.use_cases.reproduction import (
    create_sire,
    delete_sire,
    list_sires,
    sire_performance_report,
    update_sire,
)
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.sire_catalog import (
    SireCatalogCreate,
    SireCatalogListResponse,
    SireCatalogResponse,
    SireCatalogUpdate,
    SirePerformanceResponse,
)
from src.interfaces.middleware.auth_middleware import AuthContext

router = APIRouter(prefix="/reproduction/sires", tags=["reproduction"])


@router.post("", response_model=SireCatalogResponse, status_code=status.HTTP_201_CREATED)
async def create_sire_endpoint(
    payload: SireCatalogCreate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    input_data = create_sire.CreateSireInput(
        name=payload.name,
        short_code=payload.short_code,
        registry_code=payload.registry_code,
        registry_name=payload.registry_name,
        breed_id=payload.breed_id,
        animal_id=payload.animal_id,
        genetic_notes=payload.genetic_notes,
        data=payload.data,
    )
    result = await create_sire.execute(uow, context.tenant_id, input_data)
    await uow.commit()
    return result


@router.get("", response_model=SireCatalogListResponse)
async def list_sires_endpoint(
    active_only: bool = True,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    result = await list_sires.execute(
        uow,
        context.tenant_id,
        active_only=active_only,
        search=search,
        limit=limit,
        offset=offset,
    )
    return {
        "items": result.items,
        "total": result.total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{sire_id}", response_model=SireCatalogResponse)
async def get_sire_endpoint(
    sire_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    sire = await uow.sire_catalog.get(context.tenant_id, sire_id)
    if not sire:
        raise HTTPException(status_code=404, detail="Sire not found")
    return sire


@router.put("/{sire_id}", response_model=SireCatalogResponse)
async def update_sire_endpoint(
    sire_id: UUID,
    payload: SireCatalogUpdate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    input_data = update_sire.UpdateSireInput(
        sire_id=sire_id,
        **payload.model_dump(exclude_unset=True),
    )
    result = await update_sire.execute(uow, context.tenant_id, input_data)
    await uow.commit()
    return result


@router.delete("/{sire_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sire_endpoint(
    sire_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    await delete_sire.execute(uow, context.tenant_id, sire_id)
    await uow.commit()


@router.get("/{sire_id}/performance", response_model=SirePerformanceResponse)
async def sire_performance_endpoint(
    sire_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    result = await sire_performance_report.execute(uow, context.tenant_id, sire_id)
    return {
        "sire": result.sire,
        "total_inseminations": result.total_inseminations,
        "confirmed_pregnancies": result.confirmed_pregnancies,
        "conception_rate": result.conception_rate,
    }
