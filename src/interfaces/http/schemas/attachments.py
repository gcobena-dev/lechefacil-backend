from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PresignUploadRequest(BaseModel):
    content_type: str = Field(examples=["image/jpeg", "image/png"])


class PresignUploadResponse(BaseModel):
    upload_url: str
    storage_key: str
    fields: dict[str, str] | None = None


class CreatePhotoRequest(BaseModel):
    storage_key: str
    mime_type: str
    size_bytes: int | None = None
    title: str | None = None
    description: str | None = None
    is_primary: bool = False
    position: int = 0


class AttachmentResponse(BaseModel):
    id: UUID
    url: str
    title: str | None
    description: str | None
    is_primary: bool
    position: int
    mime_type: str
    size_bytes: int | None
    created_at: datetime
