from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.domain.models.breed import Breed
from src.infrastructure.auth.context import AuthContext
from src.infrastructure.db.session import SQLAlchemyUnitOfWork
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.breeds import BreedCreate, BreedResponse, BreedUpdate

router = APIRouter(prefix="/breeds", tags=["breeds"])


@router.get("/", response_model=list[BreedResponse])
async def list_breeds(
    *,
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
    context: AuthContext = Depends(get_auth_context),
    active: bool | None = Query(None),
):
    breeds = await uow.breeds.list_for_tenant(context.tenant_id, active=active)
    return [
        BreedResponse(
            id=str(b.id),
            name=b.name,
            code=b.code,
            is_system_default=b.is_system_default,
            active=b.active,
            metadata=b.metadata,
        )
        for b in breeds
    ]


@router.post("/", response_model=BreedResponse, status_code=status.HTTP_201_CREATED)
async def create_breed(
    payload: BreedCreate,
    *,
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
    context: AuthContext = Depends(get_auth_context),
):
    if not context.role.can_update():
        from src.application.errors import PermissionDenied

        raise PermissionDenied("Role not allowed to create breeds")
    # Only tenant breeds can be created here (code and system flag are not allowed)
    breed = Breed.create(
        name=payload.name.strip(),
        tenant_id=context.tenant_id,
        active=payload.active,
        metadata=payload.metadata,
    )
    created = await uow.breeds.add(breed)
    await uow.commit()
    return BreedResponse(
        id=str(created.id),
        name=created.name,
        code=created.code,
        is_system_default=created.is_system_default,
        active=created.active,
        metadata=created.metadata,
    )


@router.put("/{breed_id}", response_model=BreedResponse)
async def update_breed(
    breed_id: UUID,
    payload: BreedUpdate,
    *,
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
    context: AuthContext = Depends(get_auth_context),
):
    if not context.role.can_update():
        from src.application.errors import PermissionDenied

        raise PermissionDenied("Role not allowed to update breeds")
    # Prevent editing system breeds
    existing = await uow.breeds.get(context.tenant_id, breed_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Breed not found")
    if existing.tenant_id is None:
        raise HTTPException(status_code=403, detail="Cannot edit system breed")

    updates: dict = {}
    if payload.name is not None:
        updates["name"] = payload.name.strip()
    if payload.active is not None:
        updates["active"] = payload.active
    if payload.metadata is not None:
        updates["metadata"] = payload.metadata

    updated = await uow.breeds.update(context.tenant_id, breed_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Breed not found")
    await uow.commit()
    return BreedResponse(
        id=str(updated.id),
        name=updated.name,
        code=updated.code,
        is_system_default=updated.is_system_default,
        active=updated.active,
        metadata=updated.metadata,
    )


@router.delete("/{breed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_breed(
    breed_id: UUID,
    *,
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
    context: AuthContext = Depends(get_auth_context),
):
    if not context.role.can_delete():
        from src.application.errors import PermissionDenied

        raise PermissionDenied("Role not allowed to delete breeds")
    existing = await uow.breeds.get(context.tenant_id, breed_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Breed not found")
    if existing.tenant_id is None:
        raise HTTPException(status_code=403, detail="Cannot delete system breed")
    # Prevent delete if referenced by animals
    name = existing.name
    refs = await uow.animals.count_by_breed_id_or_name(
        context.tenant_id, breed_id=breed_id, breed_name=name
    )
    if refs > 0:
        raise HTTPException(
            status_code=409, detail="Breed is referenced by animals; deactivate instead"
        )
    ok = await uow.breeds.soft_delete(context.tenant_id, breed_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Breed not found")
    await uow.commit()
    return None
