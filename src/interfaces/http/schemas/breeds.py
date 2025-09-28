from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class BreedBase(BaseModel):
    name: str
    active: bool = True
    metadata: dict[str, Any] | None = None


class BreedCreate(BreedBase):
    pass


class BreedUpdate(BaseModel):
    name: str | None = None
    active: bool | None = None
    metadata: dict[str, Any] | None = None


class BreedResponse(BaseModel):
    id: str
    name: str
    code: str | None
    is_system_default: bool
    active: bool
    metadata: dict[str, Any] | None
