from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories.attachments import AttachmentsRepository
from src.domain.models.attachment import Attachment
from src.domain.value_objects.owner_type import OwnerType
from src.infrastructure.db.orm.attachment import AttachmentORM


class AttachmentsSQLAlchemyRepository(AttachmentsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: AttachmentORM) -> Attachment:
        return Attachment(
            id=orm.id,
            tenant_id=orm.tenant_id,
            owner_type=orm.owner_type,
            owner_id=orm.owner_id,
            kind=orm.kind,
            title=orm.title,
            description=orm.description,
            storage_key=orm.storage_key,
            mime_type=orm.mime_type,
            size_bytes=orm.size_bytes,
            checksum=orm.checksum,
            width=orm.width,
            height=orm.height,
            is_primary=orm.is_primary,
            position=orm.position,
            deleted_at=orm.deleted_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            version=orm.version,
        )

    async def add(self, attachment: Attachment) -> Attachment:
        orm = AttachmentORM(
            id=attachment.id,
            tenant_id=attachment.tenant_id,
            owner_type=attachment.owner_type,
            owner_id=attachment.owner_id,
            kind=attachment.kind,
            title=attachment.title,
            description=attachment.description,
            storage_key=attachment.storage_key,
            mime_type=attachment.mime_type,
            size_bytes=attachment.size_bytes,
            checksum=attachment.checksum,
            width=attachment.width,
            height=attachment.height,
            is_primary=attachment.is_primary,
            position=attachment.position,
            deleted_at=attachment.deleted_at,
            created_at=attachment.created_at,
            updated_at=attachment.updated_at,
            version=attachment.version,
        )
        self.session.add(orm)
        await self.session.flush()
        return self._to_domain(orm)

    async def list_for_owner(
        self, tenant_id: UUID, owner_type: OwnerType, owner_id: UUID
    ) -> list[Attachment]:
        stmt = (
            select(AttachmentORM)
            .where(
                AttachmentORM.tenant_id == tenant_id,
                AttachmentORM.owner_type == owner_type,
                AttachmentORM.owner_id == owner_id,
                AttachmentORM.deleted_at.is_(None),
            )
            .order_by(AttachmentORM.position, AttachmentORM.created_at)
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def get(self, tenant_id: UUID, attachment_id: UUID) -> Attachment | None:
        stmt = select(AttachmentORM).where(
            AttachmentORM.tenant_id == tenant_id,
            AttachmentORM.id == attachment_id,
            AttachmentORM.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def set_primary(
        self, tenant_id: UUID, owner_type: OwnerType, owner_id: UUID, attachment_id: UUID
    ) -> None:
        # Unset existing primaries
        await self.session.execute(
            update(AttachmentORM)
            .where(
                AttachmentORM.tenant_id == tenant_id,
                AttachmentORM.owner_type == owner_type,
                AttachmentORM.owner_id == owner_id,
                AttachmentORM.is_primary.is_(True),
            )
            .values(is_primary=False)
        )
        # Set new primary
        await self.session.execute(
            update(AttachmentORM)
            .where(
                AttachmentORM.tenant_id == tenant_id,
                AttachmentORM.id == attachment_id,
                AttachmentORM.deleted_at.is_(None),
            )
            .values(is_primary=True)
        )

    async def update_metadata(
        self,
        tenant_id: UUID,
        attachment_id: UUID,
        *,
        title: str | None = None,
        description: str | None = None,
        position: int | None = None,
        is_primary: bool | None = None,
    ) -> Attachment | None:
        values: dict = {"updated_at": datetime.utcnow()}
        if title is not None:
            values["title"] = title
        if description is not None:
            values["description"] = description
        if position is not None:
            values["position"] = position
        if is_primary is not None:
            values["is_primary"] = is_primary
        stmt = (
            update(AttachmentORM)
            .where(AttachmentORM.tenant_id == tenant_id, AttachmentORM.id == attachment_id)
            .values(**values)
            .returning(AttachmentORM)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def soft_delete(self, tenant_id: UUID, attachment_id: UUID) -> bool:
        stmt = (
            update(AttachmentORM)
            .where(AttachmentORM.tenant_id == tenant_id, AttachmentORM.id == attachment_id)
            .values(deleted_at=func.now())
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def count_for_owner(self, tenant_id: UUID, owner_type: OwnerType, owner_id: UUID) -> int:
        stmt = select(func.count(AttachmentORM.id)).where(
            and_(
                AttachmentORM.tenant_id == tenant_id,
                AttachmentORM.owner_type == owner_type,
                AttachmentORM.owner_id == owner_id,
                AttachmentORM.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_primary_for_owner(
        self, tenant_id: UUID, owner_type: OwnerType, owner_id: UUID
    ) -> Attachment | None:
        stmt = select(AttachmentORM).where(
            AttachmentORM.tenant_id == tenant_id,
            AttachmentORM.owner_type == owner_type,
            AttachmentORM.owner_id == owner_id,
            AttachmentORM.is_primary.is_(True),
            AttachmentORM.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None
