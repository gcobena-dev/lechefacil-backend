from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class AnimalStatusResponse(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    is_system_default: bool
    # False for SOLD / DEAD / CULLED: animals out of the herd
    is_active: bool = True
