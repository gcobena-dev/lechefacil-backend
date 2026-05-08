from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AccessRequestPayload(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone_number: str | None = Field(default=None, max_length=50)
    farm_name: str = Field(min_length=1, max_length=120)
    farm_location: str | None = Field(default=None, max_length=255)
    requested_role: str = Field(min_length=1, max_length=50)
    message: str | None = None


class AccessRequestSubmitResponse(BaseModel):
    id: UUID
    status: str = "pending"


class AccessRequestResponse(BaseModel):
    """Legacy response (kept for backwards compat with old clients)."""

    status: str


class AccessRequestDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    full_name: str
    email: EmailStr
    phone_number: str | None
    farm_name: str
    farm_location: str | None
    requested_role: str
    message: str | None
    status: str
    requester_user_id: UUID | None
    decided_by_user_id: UUID | None
    decided_at: datetime | None
    decision_notes: str | None
    created_tenant_id: UUID | None
    created_at: datetime
    updated_at: datetime


class AccessRequestList(BaseModel):
    items: list[AccessRequestDetail]
    total: int


class AccessRequestDecisionPayload(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)
