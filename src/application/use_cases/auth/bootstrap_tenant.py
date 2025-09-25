from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from src.application.errors import ConflictError
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.membership import Membership
from src.domain.models.tenant_config import TenantConfig
from src.domain.models.user import User
from src.domain.value_objects.role import Role
from src.infrastructure.auth.password import PasswordHasher


@dataclass(slots=True)
class RegisterTenantInput:
    email: str
    password: str
    tenant_id: UUID | None = None


@dataclass(slots=True)
class RegisterTenantResult:
    user_id: UUID
    tenant_id: UUID
    email: str


async def execute(
    *, uow: UnitOfWork, payload: RegisterTenantInput, password_hasher: PasswordHasher
) -> RegisterTenantResult:
    existing = await uow.users.get_by_email(payload.email)
    if existing:
        raise ConflictError("Email already registered")

    tenant_id = payload.tenant_id or uuid4()
    hashed = password_hasher.hash(payload.password)
    user = User.create(email=payload.email, hashed_password=hashed, is_active=True)
    created = await uow.users.add(user)
    membership = Membership(user_id=created.id, tenant_id=tenant_id, role=Role.ADMIN)
    await uow.memberships.add(membership)

    # Ensure tenant config exists with defaults
    cfg = await uow.tenant_config.get(tenant_id)
    if not cfg:
        cfg = TenantConfig(tenant_id=tenant_id)
        await uow.tenant_config.upsert(cfg)

    await uow.commit()
    return RegisterTenantResult(user_id=created.id, tenant_id=tenant_id, email=created.email)

