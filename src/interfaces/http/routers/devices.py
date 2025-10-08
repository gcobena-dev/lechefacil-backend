from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.infrastructure.auth.context import AuthContext
from src.infrastructure.db.session import SQLAlchemyUnitOfWork
from src.infrastructure.repos.device_tokens_sqlalchemy import DeviceTokensSQLAlchemyRepository
from src.interfaces.http.deps import get_auth_context, get_uow

router = APIRouter(prefix="/devices", tags=["devices"])


class RegisterDeviceTokenRequest(BaseModel):
    platform: Literal["ios", "android", "web"] = Field(..., description="Device platform")
    token: str = Field(..., min_length=10, max_length=1024)
    app_version: str | None = Field(None, max_length=50)


class RegisterDeviceTokenResponse(BaseModel):
    status: str


class DeleteDeviceTokenRequest(BaseModel):
    token: str


@router.post("/tokens", response_model=RegisterDeviceTokenResponse)
async def register_device_token(
    payload: RegisterDeviceTokenRequest,
    context: AuthContext = Depends(get_auth_context),
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> RegisterDeviceTokenResponse:
    session = uow.session
    repo = DeviceTokensSQLAlchemyRepository(session)
    await repo.upsert(
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        platform=payload.platform,
        token=payload.token,
        app_version=payload.app_version,
    )
    await session.commit()
    return RegisterDeviceTokenResponse(status="ok")


@router.delete("/tokens", response_model=RegisterDeviceTokenResponse)
async def delete_device_token(
    payload: DeleteDeviceTokenRequest,
    context: AuthContext = Depends(get_auth_context),
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> RegisterDeviceTokenResponse:
    session = uow.session
    repo = DeviceTokensSQLAlchemyRepository(session)
    await repo.remove_by_token(user_id=context.user_id, token=payload.token)
    await session.commit()
    return RegisterDeviceTokenResponse(status="ok")
