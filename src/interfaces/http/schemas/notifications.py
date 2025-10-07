from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    user_id: UUID
    type: str
    title: str
    message: str
    data: dict | None = None
    read: bool
    created_at: datetime
    read_at: datetime | None = None


class NotificationListResponse(BaseModel):
    notifications: list[NotificationSchema]
    total: int
    unread_count: int


class MarkAsReadRequest(BaseModel):
    notification_ids: list[UUID]


class MarkAsReadResponse(BaseModel):
    marked_count: int


class WebSocketNotificationMessage(BaseModel):
    """Message sent through WebSocket"""

    type: str = "notification"
    notification: NotificationSchema
