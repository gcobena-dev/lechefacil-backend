from __future__ import annotations

from fastapi import APIRouter, Depends

from src.application.errors import PermissionDenied
from src.domain.models.tenant_config import TenantConfig
from src.infrastructure.auth.context import AuthContext
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.tenant_settings import (
    TenantBillingResponse,
    TenantBillingSettings,
    TenantIdentityResponse,
    TenantIdentityUpdate,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/billing", response_model=TenantBillingResponse)
async def get_billing_settings(
    context: AuthContext = Depends(get_auth_context), uow=Depends(get_uow)
):
    cfg = await uow.tenant_config.get(context.tenant_id)
    if not cfg:
        cfg = TenantConfig(tenant_id=context.tenant_id)
        cfg = await uow.tenant_config.upsert(cfg)
        await uow.commit()
    return TenantBillingResponse.model_validate(cfg)


@router.put("/billing", response_model=TenantBillingResponse)
async def update_billing_settings(
    payload: TenantBillingSettings,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    if not context.role.can_manage_users():
        raise PermissionDenied("Only admin can update billing settings")
    updates = payload.model_dump(exclude_unset=True)
    updated = await uow.tenant_config.update(context.tenant_id, updates)
    if not updated:
        cfg = TenantConfig(tenant_id=context.tenant_id, **updates)
        updated = await uow.tenant_config.upsert(cfg)
    await uow.commit()
    return TenantBillingResponse.model_validate(updated)


@router.get("/tenant", response_model=TenantIdentityResponse)
async def get_tenant_identity(
    context: AuthContext = Depends(get_auth_context), uow=Depends(get_uow)
):
    cfg = await uow.tenant_config.get(context.tenant_id)
    if not cfg:
        cfg = TenantConfig(tenant_id=context.tenant_id)
        cfg = await uow.tenant_config.upsert(cfg)
        await uow.commit()
    return TenantIdentityResponse.model_validate(cfg)


@router.patch("/tenant", response_model=TenantIdentityResponse)
async def update_tenant_identity(
    payload: TenantIdentityUpdate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    if not context.role.can_manage_users():
        raise PermissionDenied("Only admin can update tenant identity")
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        cfg = await uow.tenant_config.get(context.tenant_id)
        if not cfg:
            cfg = TenantConfig(tenant_id=context.tenant_id)
            cfg = await uow.tenant_config.upsert(cfg)
            await uow.commit()
        return TenantIdentityResponse.model_validate(cfg)
    updated = await uow.tenant_config.update(context.tenant_id, updates)
    if not updated:
        cfg = TenantConfig(tenant_id=context.tenant_id, **updates)
        updated = await uow.tenant_config.upsert(cfg)
    await uow.commit()
    return TenantIdentityResponse.model_validate(updated)
