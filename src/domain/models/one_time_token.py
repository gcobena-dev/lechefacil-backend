from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(slots=True)
class OneTimeToken:
    """
    One-time use token for sensitive operations.
    Automatically invalidated after first use.
    Can have optional expiration (for password reset) or no expiration (for invitations).
    """

    id: UUID
    token: str  # The generated token (hash/UUID)
    user_id: UUID
    purpose: str  # 'set_password', 'reset_password', 'verify_email', etc.
    is_used: bool = False
    used_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None  # None = no expiration
    extra_data: dict | None = None  # Additional data (tenant_id, role, etc.)

    @classmethod
    def create(
        cls,
        *,
        token: str,
        user_id: UUID,
        purpose: str,
        expires_in_minutes: int | None = None,
        extra_data: dict | None = None,
    ) -> OneTimeToken:
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        expires_at = None
        if expires_in_minutes is not None:
            expires_at = now + timedelta(minutes=expires_in_minutes)

        return cls(
            id=uuid4(),
            token=token,
            user_id=user_id,
            purpose=purpose,
            is_used=False,
            used_at=None,
            created_at=now,
            expires_at=expires_at,
            extra_data=extra_data or {},
        )

    def mark_as_used(self) -> None:
        """Mark the token as used"""
        self.is_used = True
        self.used_at = datetime.now(timezone.utc)

    def is_valid(self) -> bool:
        """Check if the token is valid for use (not used and not expired)"""
        if self.is_used:
            return False

        # Check expiration if it has one
        if self.expires_at is not None:
            now = datetime.now(timezone.utc)
            if now > self.expires_at:
                return False

        return True

    def is_expired(self) -> bool:
        """Check if the token has expired"""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
