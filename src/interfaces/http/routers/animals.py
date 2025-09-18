from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from src.application.use_cases.animals import (
    create_animal,
    delete_animal,
    get_animal,
    list_animals,
    update_animal,
)
from src.infrastructure.auth.context import AuthContext
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.animals import (
    AnimalCreate,
    AnimalResponse,
    AnimalsListResponse,
    AnimalUpdate,
)

router = APIRouter(prefix="/api/v1/animals", tags=["animals"])


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
    items = [AnimalResponse.model_validate(item) for item in result.items]
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
    return AnimalResponse.model_validate(result)


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
