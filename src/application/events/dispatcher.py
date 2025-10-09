from __future__ import annotations

import logging
from typing import Iterable

from src.application.events.models import (
    DeliveryRecordedEvent,
    ProductionBulkRecordedEvent,
    ProductionLowEvent,
    ProductionRecordedEvent,
)
from src.application.notifications.factory import build_notification
from src.application.notifications.types import NotificationType
from src.config.settings import get_settings
from src.infrastructure.db.session import SQLAlchemyUnitOfWork
from src.infrastructure.push.fcm import FCMClient
from src.infrastructure.push.fcm_v1 import FCMv1Client
from src.infrastructure.repos.device_tokens_sqlalchemy import DeviceTokensSQLAlchemyRepository
from src.infrastructure.repos.notifications_sqlalchemy import NotificationsSQLAlchemyRepository
from src.infrastructure.services.notification_service import NotificationService
from src.interfaces.http.routers.notifications import connection_manager

logger = logging.getLogger(__name__)


async def dispatch_events(session_factory, events: Iterable[object]) -> None:
    """
    Dispatch events post-commit. Uses a transient session for reads and sending notifications.
    Safe to call in a background task.
    """
    events = list(events)
    if not events:
        return

    settings = get_settings()

    async with session_factory() as session:
        uow = SQLAlchemyUnitOfWork(lambda: session)
        # Wire repos manually since we're wrapping an existing session
        from src.infrastructure.repos.animals_sqlalchemy import AnimalsSQLAlchemyRepository
        from src.infrastructure.repos.buyers_sqlalchemy import BuyersSQLAlchemyRepository
        from src.infrastructure.repos.users_sqlalchemy import UsersSQLAlchemyRepository

        uow.users = UsersSQLAlchemyRepository(session)
        uow.animals = AnimalsSQLAlchemyRepository(session)
        uow.buyers = BuyersSQLAlchemyRepository(session)

        # Build NotificationService on same session
        notification_repo = NotificationsSQLAlchemyRepository(session)
        device_tokens_repo = DeviceTokensSQLAlchemyRepository(session)
        push_sender = None
        sa_json = settings.get_fcm_service_account_json()
        if settings.fcm_project_id and sa_json:
            push_sender = FCMv1Client(
                project_id=settings.fcm_project_id, service_account_json=sa_json
            )
        elif settings.fcm_server_key:
            push_sender = FCMClient(settings.fcm_server_key.get_secret_value())
        notification_service = NotificationService(
            notification_repo=notification_repo,
            connection_manager=connection_manager,
            device_tokens_repo=device_tokens_repo,
            push_sender=push_sender,
        )

        for event in events:
            try:
                if isinstance(event, DeliveryRecordedEvent):
                    await _handle_delivery_recorded(uow, notification_service, event)
                elif isinstance(event, ProductionLowEvent):
                    await _handle_production_low(uow, notification_service, event)
                elif isinstance(event, ProductionRecordedEvent):
                    await _handle_production_recorded(uow, notification_service, event)
                elif isinstance(event, ProductionBulkRecordedEvent):
                    await _handle_production_bulk_recorded(uow, notification_service, event)
            except Exception as e:
                logger.error(
                    "Error dispatching event %s: %s", type(event).__name__, e, exc_info=True
                )


async def _send_to_all_users_except_actor(
    uow: SQLAlchemyUnitOfWork, tenant_id, actor_user_id, send_cb
):
    users_with_roles, _total = await uow.users.list_by_tenant(tenant_id, page=1, limit=1000)
    for uwr in users_with_roles:
        if uwr.user.id == actor_user_id:
            continue
        await send_cb(uwr.user.id)


async def _handle_delivery_recorded(
    uow: SQLAlchemyUnitOfWork, notification_service: NotificationService, e: DeliveryRecordedEvent
):
    buyer = await uow.buyers.get(e.tenant_id, e.buyer_id)
    buyer_name = buyer.name if buyer else "Comprador"
    built = build_notification(
        NotificationType.DELIVERY_RECORDED,
        buyer_name=buyer_name,
        volume_l=e.volume_l,
        amount=e.amount,
        currency=e.currency,
        delivery_id=e.delivery_id,
        buyer_id=e.buyer_id,
        date=e.date,
    )

    async def send(user_id):
        await notification_service.send_notification(
            tenant_id=e.tenant_id,
            user_id=user_id,
            type=built.type,
            title=built.title,
            message=built.message,
            data=built.data,
        )

    await _send_to_all_users_except_actor(uow, e.tenant_id, e.actor_user_id, send)


async def _handle_production_recorded(
    uow: SQLAlchemyUnitOfWork, notification_service: NotificationService, e: ProductionRecordedEvent
):
    animal = await uow.animals.get(e.tenant_id, e.animal_id)
    animal_label = animal.tag if animal else "Animal"
    animal_name = animal.name if animal and animal.name else ""
    built = build_notification(
        NotificationType.PRODUCTION_RECORDED,
        animal_label=animal_label,
        animal_name=animal_name,
        volume_l=e.volume_l,
        shift=e.shift,
        animal_id=e.animal_id,
        production_id=e.production_id,
        date=e.date,
    )

    async def send(user_id):
        await notification_service.send_notification(
            tenant_id=e.tenant_id,
            user_id=user_id,
            type=built.type,
            title=built.title,
            message=built.message,
            data=built.data,
        )

    await _send_to_all_users_except_actor(uow, e.tenant_id, e.actor_user_id, send)


async def _handle_production_low(
    uow: SQLAlchemyUnitOfWork, notification_service: NotificationService, e: ProductionLowEvent
):
    animal = await uow.animals.get(e.tenant_id, e.animal_id)
    animal_label = animal.tag if animal else "Animal"
    animal_name = animal.name if animal and animal.name else ""
    built = build_notification(
        NotificationType.PRODUCTION_LOW,
        animal_label=animal_label,
        animal_name=animal_name,
        volume_l=e.volume_l,
        avg_hist=e.avg_hist,
        shift=e.shift,
        animal_id=e.animal_id,
        production_id=e.production_id,
        date=e.date,
    )

    async def send(user_id):
        await notification_service.send_notification(
            tenant_id=e.tenant_id,
            user_id=user_id,
            type=built.type,
            title=built.title,
            message=built.message,
            data=built.data,
        )

    await _send_to_all_users_except_actor(uow, e.tenant_id, e.actor_user_id, send)


async def _handle_production_bulk_recorded(
    uow: SQLAlchemyUnitOfWork,
    notification_service: NotificationService,
    e: ProductionBulkRecordedEvent,
):
    built = build_notification(
        NotificationType.PRODUCTION_BULK_RECORDED,
        count=e.count,
        total_volume_l=e.total_volume_l,
        shift=e.shift,
        date=e.date,
    )

    async def send(user_id):
        await notification_service.send_notification(
            tenant_id=e.tenant_id,
            user_id=user_id,
            type=built.type,
            title=built.title,
            message=built.message,
            data=built.data,
        )

    await _send_to_all_users_except_actor(uow, e.tenant_id, e.actor_user_id, send)
