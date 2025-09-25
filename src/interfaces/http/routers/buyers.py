from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.application.errors import PermissionDenied
from src.domain.models.buyer import Buyer
from src.infrastructure.auth.context import AuthContext
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.buyers import BuyerCreate, BuyerResponse

router = APIRouter(prefix="/buyers", tags=["buyers"])


@router.get("/", response_model=list[BuyerResponse])
async def list_buyers(context: AuthContext = Depends(get_auth_context), uow=Depends(get_uow)):
    items = await uow.buyers.list(context.tenant_id)
    return [BuyerResponse.model_validate(item) for item in items]


@router.post("/", response_model=BuyerResponse, status_code=status.HTTP_201_CREATED)
async def create_buyer(
    payload: BuyerCreate, context: AuthContext = Depends(get_auth_context), uow=Depends(get_uow)
):
    if not context.role.can_create():
        raise PermissionDenied("Role not allowed to create buyers")
    buyer = Buyer.create(
        tenant_id=context.tenant_id,
        name=payload.name,
        code=payload.code,
        contact=payload.contact,
        is_active=payload.is_active,
    )
    created = await uow.buyers.add(buyer)
    await uow.commit()
    return BuyerResponse.model_validate(created)
