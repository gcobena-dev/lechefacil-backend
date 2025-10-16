from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.errors import ConflictError, NotFound
from src.domain.models.one_time_token import OneTimeToken
from src.infrastructure.db.orm.one_time_token import OneTimeTokenORM


class OneTimeTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: OneTimeTokenORM) -> OneTimeToken:
        return OneTimeToken(
            id=orm.id,
            token=orm.token,
            user_id=orm.user_id,
            purpose=orm.purpose,
            is_used=orm.is_used,
            used_at=orm.used_at,
            created_at=orm.created_at,
            expires_at=orm.expires_at,
            extra_data=orm.extra_data,
        )

    async def add(self, token: OneTimeToken) -> OneTimeToken:
        orm = OneTimeTokenORM(
            id=token.id,
            token=token.token,
            user_id=token.user_id,
            purpose=token.purpose,
            is_used=token.is_used,
            used_at=token.used_at,
            created_at=token.created_at,
            expires_at=token.expires_at,
            extra_data=token.extra_data,
        )
        self.session.add(orm)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError("Token already exists") from exc
        return self._to_domain(orm)

    async def get_by_token(self, token: str) -> OneTimeToken | None:
        """Obtiene un token por su valor"""
        stmt = select(OneTimeTokenORM).where(OneTimeTokenORM.token == token)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_user_and_purpose(
        self, user_id: UUID, purpose: str, only_unused: bool = True
    ) -> list[OneTimeToken]:
        """Obtiene tokens de un usuario para un propósito específico"""
        stmt = select(OneTimeTokenORM).where(
            OneTimeTokenORM.user_id == user_id, OneTimeTokenORM.purpose == purpose
        )
        if only_unused:
            stmt = stmt.where(OneTimeTokenORM.is_used == False)  # noqa: E712
        result = await self.session.execute(stmt)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]

    async def mark_as_used(self, token_id: UUID) -> None:
        """Marca un token como usado"""
        from datetime import datetime, timezone

        stmt = (
            update(OneTimeTokenORM)
            .where(OneTimeTokenORM.id == token_id)
            .values(is_used=True, used_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(stmt)
        if result.rowcount == 0:
            raise NotFound("Token not found")

    async def invalidate_all_for_purpose(self, user_id: UUID, purpose: str) -> None:
        """Invalida todos los tokens no usados de un usuario para un propósito específico"""
        from datetime import datetime, timezone

        stmt = (
            update(OneTimeTokenORM)
            .where(
                OneTimeTokenORM.user_id == user_id,
                OneTimeTokenORM.purpose == purpose,
                OneTimeTokenORM.is_used == False,  # noqa: E712
            )
            .values(is_used=True, used_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
