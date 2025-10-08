from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request

from src.application.errors import AuthError
from src.config.settings import Settings, get_settings
from src.infrastructure.auth.context import AuthContext
from src.infrastructure.auth.jwt_service import JWTService
from src.infrastructure.auth.password import PasswordHasher
from src.infrastructure.db.session import SQLAlchemyUnitOfWork
from src.infrastructure.push.fcm import FCMClient
from src.infrastructure.push.fcm_v1 import FCMv1Client
from src.infrastructure.repos.device_tokens_sqlalchemy import DeviceTokensSQLAlchemyRepository
from src.infrastructure.repos.notifications_sqlalchemy import NotificationsSQLAlchemyRepository
from src.infrastructure.services.notification_service import NotificationService
from src.infrastructure.websocket.connection_manager import ConnectionManager


async def get_auth_context(request: Request) -> AuthContext:
    context = getattr(request.state, "auth_context", None)
    if context is None:
        raise AuthError("Authentication required")
    return context


async def get_uow(request: Request) -> AsyncIterator[SQLAlchemyUnitOfWork]:
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        raise RuntimeError("Session factory not configured")
    uow = SQLAlchemyUnitOfWork(session_factory)
    async with uow:
        yield uow


def get_app_settings() -> Settings:
    return get_settings()


def get_password_hasher(request: Request) -> PasswordHasher:
    hasher = getattr(request.app.state, "password_hasher", None)
    if hasher is None:
        raise RuntimeError("Password hasher not configured")
    return hasher


def get_jwt_service(request: Request) -> JWTService:
    service = getattr(request.app.state, "jwt_service", None)
    if service is None:
        raise RuntimeError("JWT service not configured")
    return service


def get_connection_manager(request: Request) -> ConnectionManager:
    """Get the global WebSocket connection manager."""
    from src.interfaces.http.routers.notifications import connection_manager

    return connection_manager


async def get_notification_service(request: Request) -> AsyncIterator[NotificationService]:
    """Get NotificationService with dependencies."""
    from src.interfaces.http.routers.notifications import connection_manager

    # Create a new UoW
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        raise RuntimeError("Session factory not configured")

    # Open a transient session for the notification service
    async with session_factory() as session:
        notification_repo = NotificationsSQLAlchemyRepository(session)
        device_tokens_repo = DeviceTokensSQLAlchemyRepository(session)
        # Configure optional push sender (FCM) if server key is provided
        push_sender = None
        settings = get_settings()
        # Prefer HTTP v1 if configured (from direct json or file path/inline)
        sa_json = settings.get_fcm_service_account_json()
        if settings.fcm_project_id and sa_json:
            push_sender = FCMv1Client(
                project_id=settings.fcm_project_id, service_account_json=sa_json
            )
        elif settings.fcm_server_key:
            push_sender = FCMClient(settings.fcm_server_key.get_secret_value())
        yield NotificationService(
            notification_repo=notification_repo,
            connection_manager=connection_manager,
            device_tokens_repo=device_tokens_repo,
            push_sender=push_sender,
        )
