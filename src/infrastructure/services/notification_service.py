from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from src.domain.models.notification import Notification
from src.infrastructure.repos.device_tokens_sqlalchemy import DeviceTokensSQLAlchemyRepository
from src.infrastructure.repos.notifications_sqlalchemy import NotificationsSQLAlchemyRepository
from src.infrastructure.websocket.connection_manager import ConnectionManager
from src.interfaces.http.schemas.notifications import (
    NotificationSchema,
    WebSocketNotificationMessage,
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for creating and sending notifications with persistence."""

    def __init__(
        self,
        notification_repo: NotificationsSQLAlchemyRepository,
        connection_manager: ConnectionManager,
        device_tokens_repo: DeviceTokensSQLAlchemyRepository | None = None,
        push_sender: object | None = None,
    ) -> None:
        self.notification_repo = notification_repo
        self.connection_manager = connection_manager
        self.device_tokens_repo = device_tokens_repo
        self.push_sender = push_sender

    async def send_notification(
        self,
        tenant_id: UUID,
        user_id: UUID,
        type: str,
        title: str,
        message: str,
        data: dict | None = None,
    ) -> Notification:
        """
        Create a notification and send it via WebSocket if user is connected.
        The notification is always persisted in the database.
        """
        # Create and persist notification
        notification = Notification.create(
            tenant_id=tenant_id,
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            data=data,
        )

        saved_notification = await self.notification_repo.add(notification)
        # Ensure persistence even when running from background dispatcher
        try:
            await self.notification_repo.session.commit()
        except Exception:
            # In case the session is managed by an outer UoW, ignore commit errors here
            pass
        logger.info(
            f"Notification created: id={saved_notification.id} "
            f"tenant={tenant_id} user={user_id} type={type}"
        )

        # Try to send via WebSocket if user is connected
        if self.connection_manager.is_connected(tenant_id, user_id):
            await self._send_via_websocket(saved_notification)
        else:
            logger.debug(
                f"User not connected, notification will be retrieved later: "
                f"tenant={tenant_id} user={user_id}"
            )

        # Also attempt push delivery if configured
        await self._send_via_push(saved_notification)

        return saved_notification

    async def _send_via_websocket(self, notification: Notification) -> None:
        """Send notification through WebSocket."""
        try:
            # Convert to schema
            notification_schema = NotificationSchema(
                id=notification.id,
                tenant_id=notification.tenant_id,
                user_id=notification.user_id,
                type=notification.type,
                title=notification.title,
                message=notification.message,
                data=notification.data,
                read=notification.read,
                created_at=notification.created_at,
                read_at=notification.read_at,
            )

            # Wrap in WebSocket message
            ws_message = WebSocketNotificationMessage(
                type="notification", notification=notification_schema
            )

            # Send to user
            success = await self.connection_manager.send_to_user(
                tenant_id=notification.tenant_id,
                user_id=notification.user_id,
                message=ws_message.model_dump_json(),
            )

            if success:
                logger.info(f"Notification sent via WebSocket: id={notification.id}")
            else:
                logger.warning(f"Failed to send notification via WebSocket: id={notification.id}")

        except Exception as e:
            logger.error(f"Error sending notification via WebSocket: {e}", exc_info=True)

    async def _send_via_push(self, notification: Notification) -> None:
        if not self.push_sender or not self.device_tokens_repo:
            return
        try:
            tokens = [
                dt.token
                for dt in await self.device_tokens_repo.list_for_user(user_id=notification.user_id)
                if not dt.disabled
            ]
            if not tokens:
                return
            data = {
                "notification_id": str(notification.id),
                "type": notification.type,
                "tenant_id": str(notification.tenant_id),
                "user_id": str(notification.user_id),
            }
            attempts = 3
            delay = 2
            for attempt in range(1, attempts + 1):
                try:
                    invalid_tokens = await self.push_sender.send_to_tokens(
                        tokens=tokens,
                        title=notification.title,
                        body=notification.message,
                        data=data,
                    )
                    if invalid_tokens:
                        try:
                            disabled = await self.device_tokens_repo.disable_tokens(invalid_tokens)
                            logger.info(
                                "Disabled %s invalid push tokens (notification id=%s)",
                                disabled,
                                notification.id,
                            )
                        except Exception as disable_err:
                            logger.error(
                                "Error disabling invalid tokens %s: %s",
                                invalid_tokens,
                                disable_err,
                                exc_info=True,
                            )
                    logger.info(
                        "Notification sent via Push: id=%s tokens=%s attempt=%s",
                        notification.id,
                        len(tokens),
                        attempt,
                    )
                    break
                except Exception as e:
                    if attempt == attempts:
                        logger.error(
                            "Error sending notification via Push after %s attempts: %s",
                            attempt,
                            e,
                            exc_info=True,
                        )
                    else:
                        logger.warning(
                            "Push send attempt %s failed (%s), retrying in %ss",
                            attempt,
                            e,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.error("Error preparing push notification: %s", e, exc_info=True)
