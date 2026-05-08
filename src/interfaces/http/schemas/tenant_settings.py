from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TenantBillingSettings(BaseModel):
    default_buyer_id: UUID | None = None
    default_density: Decimal = Decimal("1.03")
    default_delivery_input_unit: str = "l"
    default_production_input_unit: str = "lb"
    default_currency: str = "USD"
    default_price_per_l: Decimal | None = None


class TenantBillingResponse(TenantBillingSettings):
    model_config = ConfigDict(from_attributes=True)
    updated_at: datetime


class TenantIdentityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    location: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("name must not be blank")
        return v.strip() if v is not None else v


class TenantIdentityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tenant_id: UUID
    name: str
    location: str | None = None
