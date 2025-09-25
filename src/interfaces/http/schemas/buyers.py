from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BuyerCreate(BaseModel):
    name: str
    code: str | None = None
    contact: str | None = None
    is_active: bool = True


class BuyerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str | None
    contact: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
