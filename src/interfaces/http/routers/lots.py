from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.domain.models.lot import Lot
from src.infrastructure.auth.context import AuthContext
from src.infrastructure.db.session import SQLAlchemyUnitOfWork
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.lots import LotCreate, LotResponse, LotUpdate

router = APIRouter(prefix="/lots", tags=["lots"])


@router.get("/", response_model=list[LotResponse])
async def list_lots(
    *,
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
    context: AuthContext = Depends(get_auth_context),
    active: bool | None = Query(None),
):
    lots = await uow.lots.list_for_tenant(context.tenant_id, active=active)
    return [LotResponse(id=str(x.id), name=x.name, active=x.active, notes=x.notes) for x in lots]


@router.post("/", response_model=LotResponse, status_code=status.HTTP_201_CREATED)
async def create_lot(
    payload: LotCreate,
    *,
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
    context: AuthContext = Depends(get_auth_context),
):
    if not context.role.can_update():
        from src.application.errors import PermissionDenied

        raise PermissionDenied("Role not allowed to create lots")
    # Enforce unique name per tenant (case-insensitive)
    existing = await uow.lots.find_by_name(context.tenant_id, payload.name.strip())
    if existing:
        from src.application.errors import ConflictError

        raise ConflictError("Lot name already exists for tenant")
    lot = Lot.create(
        tenant_id=context.tenant_id,
        name=payload.name.strip(),
        active=payload.active,
        notes=payload.notes,
    )
    created = await uow.lots.add(lot)
    await uow.commit()
    return LotResponse(
        id=str(created.id), name=created.name, active=created.active, notes=created.notes
    )


@router.put("/{lot_id}", response_model=LotResponse)
async def update_lot(
    lot_id: UUID,
    payload: LotUpdate,
    *,
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
    context: AuthContext = Depends(get_auth_context),
):
    if not context.role.can_update():
        from src.application.errors import PermissionDenied

        raise PermissionDenied("Role not allowed to update lots")
    updates: dict = {}
    if payload.name is not None:
        updates["name"] = payload.name.strip()
    if payload.active is not None:
        updates["active"] = payload.active
    if payload.notes is not None:
        updates["notes"] = payload.notes
    updated = await uow.lots.update(context.tenant_id, lot_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Lot not found")
    await uow.commit()
    return LotResponse(
        id=str(updated.id), name=updated.name, active=updated.active, notes=updated.notes
    )


@router.delete("/{lot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lot(
    lot_id: UUID,
    *,
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
    context: AuthContext = Depends(get_auth_context),
):
    if not context.role.can_delete():
        from src.application.errors import PermissionDenied

        raise PermissionDenied("Role not allowed to delete lots")
    # Prevent delete if animals assigned (by id or by legacy name)
    existing = await uow.lots.get(context.tenant_id, lot_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Lot not found")
    refs = await uow.animals.count_by_current_lot_id_or_name(
        context.tenant_id, lot_id=lot_id, lot_name=existing.name
    )
    if refs > 0:
        raise HTTPException(status_code=409, detail="Lot has animals assigned; deactivate instead")
    ok = await uow.lots.soft_delete(context.tenant_id, lot_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Lot not found")
    await uow.commit()
    return None
