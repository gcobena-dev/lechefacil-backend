from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.notifications.factory import build_notification
from src.application.notifications.types import NotificationType
from src.config.settings import get_settings
from src.infrastructure.db.orm.insemination import InseminationORM
from src.infrastructure.db.session import SQLAlchemyUnitOfWork
from src.infrastructure.push.fcm import FCMClient
from src.infrastructure.push.fcm_v1 import FCMv1Client
from src.infrastructure.repos.device_tokens_sqlalchemy import DeviceTokensSQLAlchemyRepository
from src.infrastructure.repos.notifications_sqlalchemy import NotificationsSQLAlchemyRepository
from src.infrastructure.repos.users_sqlalchemy import UsersSQLAlchemyRepository
from src.infrastructure.services.notification_service import NotificationService
from src.interfaces.http.routers.notifications import connection_manager

logger = logging.getLogger(__name__)


def _build_notification_service(session: AsyncSession) -> NotificationService:
    settings = get_settings()
    notification_repo = NotificationsSQLAlchemyRepository(session)
    device_tokens_repo = DeviceTokensSQLAlchemyRepository(session)
    push_sender = None
    sa_json = settings.get_fcm_service_account_json()
    if settings.fcm_project_id and sa_json:
        push_sender = FCMv1Client(project_id=settings.fcm_project_id, service_account_json=sa_json)
    elif settings.fcm_server_key:
        push_sender = FCMClient(settings.fcm_server_key.get_secret_value())
    return NotificationService(
        notification_repo=notification_repo,
        connection_manager=connection_manager,
        device_tokens_repo=device_tokens_repo,
        push_sender=push_sender,
    )


async def check_pending_pregnancy_checks(session_factory) -> None:
    """Find inseminations PENDING between 35-50 days and notify each tenant once."""
    now = datetime.now(timezone.utc)
    min_date = now - timedelta(days=50)
    max_date = now - timedelta(days=35)

    try:
        async with session_factory() as session:
            stmt = (
                select(InseminationORM.tenant_id, InseminationORM.id)
                .where(InseminationORM.pregnancy_status == "PENDING")
                .where(InseminationORM.service_date >= min_date)
                .where(InseminationORM.service_date <= max_date)
                .where(InseminationORM.deleted_at.is_(None))
            )
            result = await session.execute(stmt)
            rows = result.all()

            if not rows:
                return

            # Group by tenant
            tenant_counts: dict = {}
            for tenant_id, _ in rows:
                tenant_counts[tenant_id] = tenant_counts.get(tenant_id, 0) + 1

            uow = SQLAlchemyUnitOfWork(lambda: session)
            uow.users = UsersSQLAlchemyRepository(session)
            notification_service = _build_notification_service(session)

            for tenant_id, count in tenant_counts.items():
                built = build_notification(
                    NotificationType.PREGNANCY_CHECK_DUE,
                    count=count,
                )
                users_with_roles, _ = await uow.users.list_by_tenant(tenant_id, page=1, limit=1000)
                for uwr in users_with_roles:
                    try:
                        await notification_service.send_notification(
                            tenant_id=tenant_id,
                            user_id=uwr.user.id,
                            type=built.type,
                            title=built.title,
                            message=built.message,
                            data=built.data,
                        )
                    except Exception as exc:
                        logger.error(
                            "Failed sending pregnancy check due to user %s: %s",
                            uwr.user.id,
                            exc,
                        )

            logger.info("Pregnancy check due: notified %d tenants", len(tenant_counts))
    except Exception as exc:
        logger.error("check_pending_pregnancy_checks failed: %s", exc, exc_info=True)


async def check_expected_calvings(session_factory, days_ahead: int = 7) -> None:
    """Find CONFIRMED inseminations with expected_calving_date within N days and notify."""
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)

    try:
        async with session_factory() as session:
            stmt = (
                select(InseminationORM.tenant_id, InseminationORM.id)
                .where(InseminationORM.pregnancy_status == "CONFIRMED")
                .where(InseminationORM.expected_calving_date.isnot(None))
                .where(InseminationORM.expected_calving_date >= today)
                .where(InseminationORM.expected_calving_date <= cutoff)
                .where(InseminationORM.calving_event_id.is_(None))
                .where(InseminationORM.deleted_at.is_(None))
            )
            result = await session.execute(stmt)
            rows = result.all()

            if not rows:
                return

            # Group by tenant
            tenant_counts: dict = {}
            for tenant_id, _ in rows:
                tenant_counts[tenant_id] = tenant_counts.get(tenant_id, 0) + 1

            uow = SQLAlchemyUnitOfWork(lambda: session)
            uow.users = UsersSQLAlchemyRepository(session)
            notification_service = _build_notification_service(session)

            for tenant_id, count in tenant_counts.items():
                built = build_notification(
                    NotificationType.CALVING_EXPECTED_SOON,
                    count=count,
                    days=days_ahead,
                )
                users_with_roles, _ = await uow.users.list_by_tenant(tenant_id, page=1, limit=1000)
                for uwr in users_with_roles:
                    try:
                        await notification_service.send_notification(
                            tenant_id=tenant_id,
                            user_id=uwr.user.id,
                            type=built.type,
                            title=built.title,
                            message=built.message,
                            data=built.data,
                        )
                    except Exception as exc:
                        logger.error(
                            "Failed sending calving expected to user %s: %s",
                            uwr.user.id,
                            exc,
                        )

            logger.info("Calving expected soon: notified %d tenants", len(tenant_counts))
    except Exception as exc:
        logger.error("check_expected_calvings failed: %s", exc, exc_info=True)
