from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(slots=True)
class User:
    id: UUID
    email: str
    hashed_password: str
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool = True
    must_change_password: bool = False
    is_super_admin: bool = False
    last_login: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        email: str,
        hashed_password: str,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        is_active: bool = True,
        must_change_password: bool = False,
        is_super_admin: bool = False,
    ) -> User:
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            email=email.lower(),
            hashed_password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
            must_change_password=must_change_password,
            is_super_admin=is_super_admin,
            created_at=now,
            updated_at=now,
        )
