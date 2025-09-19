from __future__ import annotations

from typing import Iterable
from uuid import UUID

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.application.errors import AuthError, PermissionDenied
from src.config.settings import Settings
from src.infrastructure.auth.context import (
    AuthContext,
    fetch_memberships,
    fetch_user,
    select_active_role,
)

PUBLIC_PATHS: Iterable[str] = (
    "/api/v1/health",
    "/api/v1/auth/login",
    "/docs",
    "/openapi.json",
    "/redoc",
)


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next) -> Response:
        if any(request.url.path.startswith(path) for path in PUBLIC_PATHS):
            return await call_next(request)
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise AuthError("Missing Authorization header")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AuthError("Invalid Authorization header")
        tenant_value = request.headers.get(self.settings.tenant_header)
        if not tenant_value:
            raise PermissionDenied("Missing tenant header")
        try:
            tenant_id = UUID(tenant_value)
        except ValueError as exc:
            raise PermissionDenied("Invalid tenant identifier") from exc
        jwks_client = getattr(request.app.state, "jwks_client", None)
        jwt_service = getattr(request.app.state, "jwt_service", None)
        if jwks_client is None:
            raise RuntimeError("JWKS client not configured")

        claims = None
        try:
            claims = await jwks_client.decode_token(
                token,
                issuer=str(self.settings.oidc_issuer),
                audience=self.settings.oidc_audience,
            )
        except AuthError:
            if jwt_service is None:
                raise
            try:
                claims = jwt_service.decode(token)
            except AuthError as exc:
                raise exc
        if claims is None:
            raise AuthError("Token validation failed")

        subject = claims.get("sub")
        if not subject:
            raise AuthError("Token missing subject")
        try:
            user_id = UUID(str(subject))
        except ValueError as exc:
            raise AuthError("Token subject is not a valid UUID") from exc
        session_factory = getattr(request.app.state, "session_factory", None)
        if session_factory is None:
            raise RuntimeError("Session factory not configured")
        async with session_factory() as session:
            user = await fetch_user(session, user_id)
            if not user or not user.is_active:
                raise AuthError("Inactive or missing user")
            memberships = await fetch_memberships(session, user_id)
        role = select_active_role(memberships, tenant_id)
        request.state.auth_context = AuthContext(
            user_id=user_id,
            email=user.email,
            tenant_id=tenant_id,
            role=role,
            memberships=memberships,
            claims=claims,
        )
        return await call_next(request)
