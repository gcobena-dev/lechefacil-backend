from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(slots=True)
class Notification:
    id: UUID
    tenant_id: UUID
    user_id: UUID
    type: str
    title: str
    message: str
    data: dict | None = None
    read: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    read_at: datetime | None = None

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        user_id: UUID,
        type: str,
        title: str,
        message: str,
        data: dict | None = None,
    ) -> Notification:
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            data=data,
            read=False,
            created_at=datetime.now(timezone.utc),
            read_at=None,
        )

    def mark_as_read(self) -> None:
        if not self.read:
            self.read = True
            self.read_at = datetime.now(timezone.utc)
