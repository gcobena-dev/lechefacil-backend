from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from src.infrastructure.auth.context import AuthContext
from src.infrastructure.db.session import SQLAlchemyUnitOfWork
from src.infrastructure.repos.notifications_sqlalchemy import NotificationsSQLAlchemyRepository
from src.infrastructure.websocket.connection_manager import ConnectionManager
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.notifications import (
    MarkAsReadRequest,
    MarkAsReadResponse,
    NotificationListResponse,
    NotificationSchema,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])
logger = logging.getLogger(__name__)


# Singleton connection manager (shared across all requests)
connection_manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    tenant_id: str | None = None,
) -> None:
    """
    WebSocket endpoint for real-time notifications.
    Requires JWT token as query parameter: /ws?token=<jwt_token>&tenant_id=<uuid>
    """
    from src.config.settings import get_settings

    # Authenticate using JWT token
    try:
        # Get JWT service from app state (WebSocket has app attribute like Request)
        jwt_service = getattr(websocket.app.state, "jwt_service", None)
        if jwt_service is None:
            raise RuntimeError("JWT service not configured")

        # Use JWT service to decode and validate token
        claims = jwt_service.decode(token)
        if claims.get("typ") != "access":
            raise ValueError("Invalid token type for WebSocket connection")

        user_id = UUID(claims.get("sub"))

        # Get tenant_id from query param, or fallback to header
        if tenant_id:
            tenant_uuid = UUID(tenant_id)
        else:
            settings = get_settings()
            tenant_header = websocket.headers.get(settings.tenant_header)
            if not tenant_header:
                raise ValueError(
                    f"Missing tenant_id query param or {settings.tenant_header} header"
                )
            tenant_uuid = UUID(tenant_header)

    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}", exc_info=True)
        await websocket.close(code=1008, reason="Authentication failed")
        return

    # Connect
    await connection_manager.connect(tenant_uuid, user_id, websocket)

    try:
        # Keep connection alive and listen for ping/pong
        while True:
            # Wait for any message (usually ping from client)
            data = await websocket.receive_text()
            # Optional: respond to ping
            if data == "ping":
                await websocket.send_text("pong")
            else:
                # Ignore other messages
                pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: tenant={tenant_uuid} user={user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        connection_manager.disconnect(tenant_uuid, user_id, websocket)


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    context: AuthContext = Depends(get_auth_context),
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> NotificationListResponse:
    """Get user's notifications."""
    repo = NotificationsSQLAlchemyRepository(uow.session)

    notifications = await repo.list_by_user(
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )

    unread_count = await repo.count_unread(
        tenant_id=context.tenant_id,
        user_id=context.user_id,
    )

    notification_schemas = [
        NotificationSchema(
            id=n.id,
            tenant_id=n.tenant_id,
            user_id=n.user_id,
            type=n.type,
            title=n.title,
            message=n.message,
            data=n.data,
            read=n.read,
            created_at=n.created_at,
            read_at=n.read_at,
        )
        for n in notifications
    ]

    return NotificationListResponse(
        notifications=notification_schemas,
        total=len(notifications),
        unread_count=unread_count,
    )


@router.patch("/mark-read", response_model=MarkAsReadResponse)
async def mark_notifications_as_read(
    payload: MarkAsReadRequest,
    context: AuthContext = Depends(get_auth_context),
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> MarkAsReadResponse:
    """Mark specific notifications as read."""
    repo = NotificationsSQLAlchemyRepository(uow.session)
    marked_count = await repo.mark_as_read(payload.notification_ids)
    await uow.session.commit()

    return MarkAsReadResponse(marked_count=marked_count)


@router.post("/mark-all-read", response_model=MarkAsReadResponse)
async def mark_all_notifications_as_read(
    context: AuthContext = Depends(get_auth_context),
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> MarkAsReadResponse:
    """Mark all user's notifications as read."""
    repo = NotificationsSQLAlchemyRepository(uow.session)
    marked_count = await repo.mark_all_as_read(
        tenant_id=context.tenant_id,
        user_id=context.user_id,
    )
    await uow.session.commit()

    return MarkAsReadResponse(marked_count=marked_count)


def get_connection_manager() -> ConnectionManager:
    """Dependency to get the global connection manager."""
    return connection_manager
