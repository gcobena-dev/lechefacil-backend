from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import JSONResponse

from src.interfaces.http.deps import get_uow
from src.interfaces.http.schemas.scale_devices import (
    ScalePairRequest,
    ScalePairResponse,
    ScaleSyncRequest,
    ScaleSyncResponse,
)

router = APIRouter(prefix="/scale", tags=["scale-sync"])


async def _get_device_by_key(api_key: str, uow):
    """Look up device by API key; returns domain object or None."""
    return await uow.scale_devices.get_by_api_key(api_key)


@router.post("/sync", response_model=ScaleSyncResponse, status_code=status.HTTP_200_OK)
async def sync_records(
    payload: ScaleSyncRequest,
    x_device_key: str = Header(..., alias="X-Device-Key"),
    uow=Depends(get_uow),
):
    """ESP32 pushes scale records to the cloud."""
    device = await _get_device_by_key(x_device_key, uow)
    if device is None or not device.is_active:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"code": "DEVICE_AUTH_FAILED", "message": "Invalid or inactive device key"},
        )

    from src.domain.models.scale_device_record import ScaleDeviceRecord

    batch_id = uuid4()

    # Check for duplicates
    incoming_ids = [r.id for r in payload.records]
    existing_ids = await uow.scale_device_records.check_duplicates(device.id, incoming_ids)

    # Build non-duplicate records
    new_records: list[ScaleDeviceRecord] = []
    for r in payload.records:
        if r.id in existing_ids:
            continue
        new_records.append(
            ScaleDeviceRecord.create(
                tenant_id=device.tenant_id,
                device_id=device.id,
                device_record_id=r.id,
                codigo=r.codigo,
                peso=Decimal(r.peso),
                fecha=r.fecha,
                hora=r.hora,
                turno=r.turno,
                batch_id=batch_id,
            )
        )

    if new_records:
        await uow.scale_device_records.add_batch(new_records)

    # Update device last_seen_at
    await uow.scale_devices.update_last_seen(device.id, payload.firmware_version)

    await uow.commit()

    return ScaleSyncResponse(
        status="ok",
        batch_id=batch_id,
        accepted=len(new_records),
        duplicates=len(existing_ids),
    )


@router.post("/pair", response_model=ScalePairResponse, status_code=status.HTTP_200_OK)
async def pair_device(
    payload: ScalePairRequest,
    uow=Depends(get_uow),
):
    """ESP32 exchanges a pairing PIN for its API key."""
    device = await uow.scale_devices.get_by_pairing_pin(payload.pin)
    if device is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"code": "INVALID_PIN", "message": "Invalid or expired pairing PIN"},
        )

    await uow.scale_devices.clear_pairing_pin(device.id)
    await uow.commit()

    return ScalePairResponse(api_key=device.api_key, device_name=device.name)


@router.get("/config")
async def get_device_config(
    x_device_key: str = Header(..., alias="X-Device-Key"),
    uow=Depends(get_uow),
):
    """ESP32 fetches its configuration."""
    device = await _get_device_by_key(x_device_key, uow)
    if device is None or not device.is_active:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"code": "DEVICE_AUTH_FAILED", "message": "Invalid or inactive device key"},
        )

    return {
        "wifi_ssid": device.wifi_ssid,
        "wifi_password": device.wifi_password,
        "device_name": device.name,
    }
