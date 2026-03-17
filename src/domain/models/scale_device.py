from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(slots=True)
class ScaleDevice:
    id: UUID
    tenant_id: UUID
    name: str
    api_key: str
    wifi_ssid: str | None = None
    wifi_password: str | None = None
    is_active: bool = True
    last_seen_at: datetime | None = None
    firmware_version: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        name: str,
        wifi_ssid: str | None = None,
        wifi_password: str | None = None,
    ) -> ScaleDevice:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            api_key=secrets.token_hex(32),
            wifi_ssid=wifi_ssid,
            wifi_password=wifi_password,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
