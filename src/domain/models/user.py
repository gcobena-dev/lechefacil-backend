from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(slots=True)
class User:
    id: UUID
    email: str
    hashed_password: str
    is_active: bool = True
    must_change_password: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        email: str,
        hashed_password: str,
        *,
        is_active: bool = True,
        must_change_password: bool = False,
    ) -> User:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            email=email.lower(),
            hashed_password=hashed_password,
            is_active=is_active,
            must_change_password=must_change_password,
            created_at=now,
            updated_at=now,
        )
