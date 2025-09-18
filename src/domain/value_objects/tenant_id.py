from __future__ import annotations

from uuid import UUID


def parse_tenant_id(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)
