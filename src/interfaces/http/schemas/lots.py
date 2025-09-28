from __future__ import annotations

from pydantic import BaseModel


class LotBase(BaseModel):
    name: str
    active: bool = True
    notes: str | None = None


class LotCreate(LotBase):
    pass


class LotUpdate(BaseModel):
    name: str | None = None
    active: bool | None = None
    notes: str | None = None


class LotResponse(BaseModel):
    id: str
    name: str
    active: bool
    notes: str | None
