from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.domain.value_objects.access_request_status import AccessRequestStatus


@dataclass(slots=True)
class AccessRequest:
    id: UUID
    full_name: str
    email: str
    farm_name: str
    requested_role: str
    status: AccessRequestStatus = AccessRequestStatus.PENDING
    requester_user_id: UUID | None = None
    phone_number: str | None = None
    farm_location: str | None = None
    message: str | None = None
    decided_by_user_id: UUID | None = None
    decided_at: datetime | None = None
    decision_notes: str | None = None
    created_tenant_id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        *,
        full_name: str,
        email: str,
        farm_name: str,
        requested_role: str,
        requester_user_id: UUID | None = None,
        phone_number: str | None = None,
        farm_location: str | None = None,
        message: str | None = None,
    ) -> AccessRequest:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            full_name=full_name.strip(),
            email=email.strip().lower(),
            farm_name=farm_name.strip(),
            requested_role=requested_role,
            status=AccessRequestStatus.PENDING,
            requester_user_id=requester_user_id,
            phone_number=phone_number,
            farm_location=farm_location.strip() if farm_location else None,
            message=message,
            created_at=now,
            updated_at=now,
        )
