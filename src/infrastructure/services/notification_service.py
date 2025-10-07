from __future__ import annotations

import logging
from uuid import UUID

from src.domain.models.notification import Notification
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
    ) -> None:
        self.notification_repo = notification_repo
        self.connection_manager = connection_manager

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
