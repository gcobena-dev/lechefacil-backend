from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScaleDeviceCreate(BaseModel):
    name: str = Field(max_length=100)
    wifi_ssid: str | None = Field(default=None, max_length=64)
    wifi_password: str | None = Field(default=None, max_length=128)


class ScaleDeviceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    wifi_ssid: str | None = Field(default=None, max_length=64)
    wifi_password: str | None = Field(default=None, max_length=128)
    is_active: bool | None = None


class ScaleDeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    name: str
    api_key_masked: str
    is_active: bool
    last_seen_at: datetime | None
    firmware_version: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, device) -> ScaleDeviceResponse:
        masked = "****" + device.api_key[-4:] if len(device.api_key) >= 4 else "****"
        return cls(
            id=device.id,
            tenant_id=device.tenant_id,
            name=device.name,
            api_key_masked=masked,
            is_active=device.is_active,
            last_seen_at=device.last_seen_at,
            firmware_version=device.firmware_version,
            created_at=device.created_at,
        )


class ScaleDeviceCreatedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    name: str
    api_key: str
    api_key_masked: str
    is_active: bool
    last_seen_at: datetime | None
    firmware_version: str | None
    pairing_pin: str | None = None
    pairing_pin_expires_at: datetime | None = None
    created_at: datetime

    @classmethod
    def from_domain(cls, device) -> ScaleDeviceCreatedResponse:
        masked = "****" + device.api_key[-4:] if len(device.api_key) >= 4 else "****"
        return cls(
            id=device.id,
            tenant_id=device.tenant_id,
            name=device.name,
            api_key=device.api_key,
            api_key_masked=masked,
            is_active=device.is_active,
            last_seen_at=device.last_seen_at,
            firmware_version=device.firmware_version,
            pairing_pin=device.pairing_pin,
            pairing_pin_expires_at=device.pairing_pin_expires_at,
            created_at=device.created_at,
        )


class ScalePairRequest(BaseModel):
    pin: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ScalePairResponse(BaseModel):
    api_key: str
    device_name: str


class PairingPinResponse(BaseModel):
    pin: str
    expires_at: datetime


class ScaleSyncRecord(BaseModel):
    id: int
    codigo: str = Field(max_length=50)
    peso: str
    fecha: str = Field(max_length=10)
    hora: str = Field(max_length=8)
    turno: str = Field(max_length=2)


class ScaleSyncRequest(BaseModel):
    records: list[ScaleSyncRecord]
    firmware_version: str | None = Field(default=None, max_length=20)


class ScaleSyncResponse(BaseModel):
    status: str
    batch_id: UUID
    accepted: int
    duplicates: int


class ScaleDeviceRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    device_record_id: int
    codigo: str
    peso: Decimal
    fecha: str
    hora: str
    turno: str
    status: str
    matched_animal_id: UUID | None
    batch_id: UUID | None
    created_at: datetime


class PendingRecordsResponse(BaseModel):
    items: list[ScaleDeviceRecordResponse]
    total: int
