from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories.access_requests import AccessRequestsRepository
from src.domain.models.access_request import AccessRequest
from src.domain.value_objects.access_request_status import AccessRequestStatus
from src.infrastructure.db.orm.access_request import AccessRequestORM


class AccessRequestsSQLAlchemyRepository(AccessRequestsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: AccessRequestORM) -> AccessRequest:
        return AccessRequest(
            id=orm.id,
            requester_user_id=orm.requester_user_id,
            full_name=orm.full_name,
            email=orm.email,
            phone_number=orm.phone_number,
            farm_name=orm.farm_name,
            farm_location=orm.farm_location,
            requested_role=orm.requested_role,
            message=orm.message,
            status=AccessRequestStatus(orm.status),
            decided_by_user_id=orm.decided_by_user_id,
            decided_at=orm.decided_at,
            decision_notes=orm.decision_notes,
            created_tenant_id=orm.created_tenant_id,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def add(self, request: AccessRequest) -> AccessRequest:
        orm = AccessRequestORM(
            id=request.id,
            requester_user_id=request.requester_user_id,
            full_name=request.full_name,
            email=request.email,
            phone_number=request.phone_number,
            farm_name=request.farm_name,
            farm_location=request.farm_location,
            requested_role=request.requested_role,
            message=request.message,
            status=request.status.value,
            decided_by_user_id=request.decided_by_user_id,
            decided_at=request.decided_at,
            decision_notes=request.decision_notes,
            created_tenant_id=request.created_tenant_id,
        )
        self.session.add(orm)
        await self.session.flush()
        await self.session.refresh(orm)
        return self._to_domain(orm)

    async def get(self, request_id: UUID) -> AccessRequest | None:
        stmt = select(AccessRequestORM).where(AccessRequestORM.id == request_id)
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def find_open_by_email(self, email: str) -> AccessRequest | None:
        stmt = select(AccessRequestORM).where(
            AccessRequestORM.email == email.lower(),
            AccessRequestORM.status == AccessRequestStatus.PENDING.value,
        )
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list(
        self,
        *,
        status: AccessRequestStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AccessRequest], int]:
        base = select(AccessRequestORM)
        count_stmt = select(func.count()).select_from(AccessRequestORM)
        if status is not None:
            base = base.where(AccessRequestORM.status == status.value)
            count_stmt = count_stmt.where(AccessRequestORM.status == status.value)
        base = base.order_by(desc(AccessRequestORM.created_at)).limit(limit).offset(offset)
        rows = (await self.session.execute(base)).scalars().all()
        total = (await self.session.execute(count_stmt)).scalar_one()
        return [self._to_domain(r) for r in rows], int(total)

    async def update(self, request: AccessRequest) -> AccessRequest:
        orm = await self.session.get(AccessRequestORM, request.id)
        if orm is None:
            raise ValueError(f"AccessRequest {request.id} not found")
        orm.status = request.status.value
        orm.decided_by_user_id = request.decided_by_user_id
        orm.decided_at = request.decided_at
        orm.decision_notes = request.decision_notes
        orm.created_tenant_id = request.created_tenant_id
        await self.session.flush()
        await self.session.refresh(orm)
        return self._to_domain(orm)
