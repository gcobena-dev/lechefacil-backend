from __future__ import annotations

from pydantic import BaseModel, EmailStr


class AccessRequestPayload(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: str | None = None
    farm_name: str
    farm_location: str
    requested_role: str
    message: str | None = None


class AccessRequestResponse(BaseModel):
    status: str
