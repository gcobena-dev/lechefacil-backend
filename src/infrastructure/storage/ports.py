from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class PresignedUpload:
    upload_url: str
    storage_key: str
    fields: dict[str, str] | None = None


class StorageService(Protocol):
    async def get_presigned_upload(
        self, key: str, content_type: str, *, expires_seconds: int = 600
    ) -> PresignedUpload: ...

    async def get_public_url(self, key: str) -> str: ...

    async def put_object(self, key: str, data: bytes, content_type: str) -> None: ...
