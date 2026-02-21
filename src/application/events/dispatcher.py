from __future__ import annotations

import logging
from typing import Iterable

from src.application.events.models import (
    AnimalCreatedEvent,
    AnimalEventCreatedEvent,
    AnimalUpdatedEvent,
    DeliveryRecordedEvent,
    PregnancyCheckRecordedEvent,
    ProductionBulkRecordedEvent,
    ProductionLowEvent,
    ProductionRecordedEvent,
    SemenStockLowEvent,
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
                elif isinstance(event, AnimalCreatedEvent):
                    await _handle_animal_created(uow, notification_service, event)
                elif isinstance(event, AnimalUpdatedEvent):
                    await _handle_animal_updated(uow, notification_service, event)
                elif isinstance(event, AnimalEventCreatedEvent):
                    await _handle_animal_event_created(uow, notification_service, event)
                elif isinstance(event, PregnancyCheckRecordedEvent):
                    await _handle_pregnancy_check_recorded(uow, notification_service, event)
                elif isinstance(event, SemenStockLowEvent):
                    await _handle_semen_stock_low(uow, notification_service, event)
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


async def _send_to_all_users(uow: SQLAlchemyUnitOfWork, tenant_id, send_cb):
    """Broadcast to ALL users in the tenant (including actor). Used for system alerts."""
    users_with_roles, _total = await uow.users.list_by_tenant(tenant_id, page=1, limit=1000)
    for uwr in users_with_roles:
        await send_cb(uwr.user.id)


async def _handle_delivery_recorded(
    uow: SQLAlchemyUnitOfWork, notification_service: NotificationService, e: DeliveryRecordedEvent
):
    buyer = await uow.buyers.get(e.tenant_id, e.buyer_id)
    buyer_name = buyer.name if buyer else "Comprador"
    # Resolve actor label from user
    actor_user = await uow.users.get(e.actor_user_id)
    actor_label = None
    if actor_user:
        actor_label = (actor_user.email.split("@")[0]) if actor_user.email else None
    built = build_notification(
        NotificationType.DELIVERY_RECORDED,
        buyer_name=buyer_name,
        volume_l=e.volume_l,
        amount=e.amount,
        currency=e.currency,
        delivery_id=e.delivery_id,
        buyer_id=e.buyer_id,
        date_time=(e.date_time.isoformat() if getattr(e, "date_time", None) else None),
        actor_label=actor_label,
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


async def _handle_animal_created(
    uow: SQLAlchemyUnitOfWork, notification_service: NotificationService, e: AnimalCreatedEvent
):
    actor_user = await uow.users.get(e.actor_user_id)
    actor_label = (actor_user.email.split("@")[0]) if actor_user and actor_user.email else None
    built = build_notification(
        NotificationType.ANIMAL_CREATED,
        animal_id=e.animal_id,
        tag=e.tag,
        name=e.name,
        actor_label=actor_label,
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


async def _handle_animal_updated(
    uow: SQLAlchemyUnitOfWork, notification_service: NotificationService, e: AnimalUpdatedEvent
):
    actor_user = await uow.users.get(e.actor_user_id)
    actor_label = (actor_user.email.split("@")[0]) if actor_user and actor_user.email else None
    built = build_notification(
        NotificationType.ANIMAL_UPDATED,
        animal_id=e.animal_id,
        tag=e.tag,
        name=e.name,
        changed_fields=e.changed_fields,
        actor_label=actor_label,
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


async def _handle_animal_event_created(
    uow: SQLAlchemyUnitOfWork,
    notification_service: NotificationService,
    e: AnimalEventCreatedEvent,
):
    actor_user = await uow.users.get(e.actor_user_id)
    actor_label = (actor_user.email.split("@")[0]) if actor_user and actor_user.email else None
    # Try to resolve animal if tag/name missing
    tag = e.tag
    name = e.name
    if not tag or not name:
        animal = await uow.animals.get(e.tenant_id, e.animal_id)
        if animal:
            tag = tag or animal.tag
            name = name or animal.name

    # Get event data and enrich with sire name if applicable
    event_data = dict(e.event_data) if e.event_data else {}
    if event_data.get("sire_id"):
        try:
            sire = await uow.animals.get(e.tenant_id, event_data["sire_id"])
            if sire:
                event_data["sire_name"] = f"{sire.tag}" + (f" {sire.name}" if sire.name else "")
        except Exception:
            pass

    built = build_notification(
        NotificationType.ANIMAL_EVENT_CREATED,
        animal_id=e.animal_id,
        event_id=e.event_id,
        category=e.event_type,
        event_name=e.event_type,
        date=e.occurred_at,
        tag=tag,
        name=name,
        actor_label=actor_label,
        event_data=event_data,
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
    actor_user = await uow.users.get(e.actor_user_id)
    actor_label = (actor_user.email.split("@")[0]) if actor_user and actor_user.email else None
    built = build_notification(
        NotificationType.PRODUCTION_RECORDED,
        animal_label=animal_label,
        animal_name=animal_name,
        volume_l=e.volume_l,
        shift=e.shift,
        date_time=(e.date_time.isoformat() if getattr(e, "date_time", None) else None),
        animal_id=e.animal_id,
        production_id=e.production_id,
        actor_label=actor_label,
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
    actor_user = await uow.users.get(e.actor_user_id)
    actor_label = (actor_user.email.split("@")[0]) if actor_user and actor_user.email else None
    built = build_notification(
        NotificationType.PRODUCTION_LOW,
        animal_label=animal_label,
        animal_name=animal_name,
        volume_l=e.volume_l,
        avg_hist=e.avg_hist,
        shift=e.shift,
        date_time=(e.date_time.isoformat() if getattr(e, "date_time", None) else None),
        animal_id=e.animal_id,
        production_id=e.production_id,
        actor_label=actor_label,
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


async def _handle_pregnancy_check_recorded(
    uow: SQLAlchemyUnitOfWork,
    notification_service: NotificationService,
    e: PregnancyCheckRecordedEvent,
):
    actor_user = await uow.users.get(e.actor_user_id)
    actor_label = (actor_user.email.split("@")[0]) if actor_user and actor_user.email else None
    built = build_notification(
        NotificationType.PREGNANCY_CHECK_RECORDED,
        insemination_id=e.insemination_id,
        animal_id=e.animal_id,
        result=e.result,
        tag=e.tag,
        name=e.name,
        checked_by=e.checked_by,
        expected_calving_date=e.expected_calving_date,
        actor_label=actor_label,
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


async def _handle_semen_stock_low(
    uow: SQLAlchemyUnitOfWork,
    notification_service: NotificationService,
    e: SemenStockLowEvent,
):
    built = build_notification(
        NotificationType.SEMEN_STOCK_LOW,
        sire_catalog_id=e.sire_catalog_id,
        sire_name=e.sire_name,
        current_quantity=e.current_quantity,
        batch_code=e.batch_code,
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

    # System alert: broadcast to ALL users including actor
    await _send_to_all_users(uow, e.tenant_id, send)


async def _handle_production_bulk_recorded(
    uow: SQLAlchemyUnitOfWork,
    notification_service: NotificationService,
    e: ProductionBulkRecordedEvent,
):
    actor_user = await uow.users.get(e.actor_user_id)
    actor_label = (actor_user.email.split("@")[0]) if actor_user and actor_user.email else None
    built = build_notification(
        NotificationType.PRODUCTION_BULK_RECORDED,
        count=e.count,
        total_volume_l=e.total_volume_l,
        shift=e.shift,
        date_time=(e.date_time.isoformat() if getattr(e, "date_time", None) else None),
        actor_label=actor_label,
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
