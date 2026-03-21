from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response

from src.application.errors import NotFound, PermissionDenied
from src.domain.models.scale_device import ScaleDevice
from src.infrastructure.auth.context import AuthContext
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.scale_devices import (
    PairingPinResponse,
    PendingRecordsResponse,
    ScaleDeviceCreate,
    ScaleDeviceCreatedResponse,
    ScaleDeviceRecordResponse,
    ScaleDeviceResponse,
    ScaleDeviceUpdate,
)

router = APIRouter(prefix="/scale-devices", tags=["scale-devices"])


@router.post("/", response_model=ScaleDeviceCreatedResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    payload: ScaleDeviceCreate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    """Register a new scale device. Returns the full API key (only shown once)."""
    if not context.role.can_create():
        raise PermissionDenied("Role not allowed to register devices")

    device = ScaleDevice.create(
        tenant_id=context.tenant_id,
        name=payload.name,
        wifi_ssid=payload.wifi_ssid,
        wifi_password=payload.wifi_password,
    )
    pin = ScaleDevice.generate_pairing_pin()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    device.pairing_pin = pin
    device.pairing_pin_expires_at = expires_at
    created = await uow.scale_devices.add(device)
    await uow.commit()
    return ScaleDeviceCreatedResponse.from_domain(created)


@router.get("/", response_model=list[ScaleDeviceResponse])
async def list_devices(
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    """List all scale devices for the tenant."""
    devices = await uow.scale_devices.list_for_tenant(context.tenant_id)
    return [ScaleDeviceResponse.from_domain(d) for d in devices]


@router.get("/{device_id}", response_model=ScaleDeviceResponse)
async def get_device(
    device_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    """Get details of a specific scale device."""
    device = await uow.scale_devices.get(context.tenant_id, device_id)
    if not device:
        raise NotFound("Scale device not found")
    return ScaleDeviceResponse.from_domain(device)


@router.put("/{device_id}", response_model=ScaleDeviceResponse)
async def update_device(
    device_id: UUID,
    payload: ScaleDeviceUpdate,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    """Update a scale device's configuration."""
    if not context.role.can_update():
        raise PermissionDenied("Role not allowed to update devices")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        device = await uow.scale_devices.get(context.tenant_id, device_id)
        if not device:
            raise NotFound("Scale device not found")
        return ScaleDeviceResponse.from_domain(device)

    updated = await uow.scale_devices.update(context.tenant_id, device_id, data)
    if not updated:
        raise NotFound("Scale device not found")
    await uow.commit()
    return ScaleDeviceResponse.from_domain(updated)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_device(
    device_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    """Soft-delete (deactivate) a scale device."""
    if not context.role.can_delete():
        raise PermissionDenied("Role not allowed to delete devices")

    updated = await uow.scale_devices.update(context.tenant_id, device_id, {"is_active": False})
    if not updated:
        raise NotFound("Scale device not found")
    await uow.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{device_id}/regenerate-key", response_model=ScaleDeviceCreatedResponse)
async def regenerate_api_key(
    device_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    """Generate a new API key for the device. Returns full key (only shown once)."""
    if not context.role.can_update():
        raise PermissionDenied("Role not allowed to update devices")

    new_key = secrets.token_hex(32)
    updated = await uow.scale_devices.update(context.tenant_id, device_id, {"api_key": new_key})
    if not updated:
        raise NotFound("Scale device not found")
    await uow.commit()
    return ScaleDeviceCreatedResponse.from_domain(updated)


@router.post("/{device_id}/generate-pin", response_model=PairingPinResponse)
async def generate_pairing_pin(
    device_id: UUID,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    """Generate a new pairing PIN for an existing device. Expires in 10 minutes."""
    if not context.role.can_update():
        raise PermissionDenied("Role not allowed to update devices")

    device = await uow.scale_devices.get(context.tenant_id, device_id)
    if not device:
        raise NotFound("Scale device not found")

    pin = ScaleDevice.generate_pairing_pin()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    await uow.scale_devices.update(
        context.tenant_id, device_id, {"pairing_pin": pin, "pairing_pin_expires_at": expires_at}
    )
    await uow.commit()
    return PairingPinResponse(pin=pin, expires_at=expires_at)


@router.get("/{device_id}/records", response_model=PendingRecordsResponse)
async def list_device_records(
    device_id: UUID,
    status: str | None = Query(None, description="pending|imported|rejected"),
    batch_id: UUID | None = Query(None),
    fecha: str | None = Query(None, description="Filter by date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
):
    """List records for a specific scale device."""
    device = await uow.scale_devices.get(context.tenant_id, device_id)
    if not device:
        raise NotFound("Scale device not found")

    # Convert YYYY-MM-DD (from frontend) to DD/MM/YYYY (stored format)
    fecha_filter = None
    if fecha:
        from datetime import date as date_type

        parsed = date_type.fromisoformat(fecha)
        fecha_filter = parsed.strftime("%d/%m/%Y")

    total = await uow.scale_device_records.count_for_device(
        context.tenant_id, device_id, status=status, batch_id=batch_id, fecha=fecha_filter
    )
    items = await uow.scale_device_records.list_for_device(
        context.tenant_id,
        device_id,
        status=status,
        batch_id=batch_id,
        fecha=fecha_filter,
        limit=limit,
        offset=offset,
    )
    return PendingRecordsResponse(
        items=[ScaleDeviceRecordResponse.model_validate(r) for r in items],
        total=total,
    )
