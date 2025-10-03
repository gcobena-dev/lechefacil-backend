from __future__ import annotations

from typing import Iterable
from uuid import UUID

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

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
    "/api/v1/auth/signin",
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
    "/api/v1/auth/my-tenants",
    "/api/v1/access-requests",
    "/api/v1/mobile",  # Mobile update endpoints (no auth required)
    # memberships is admin-only and requires tenant header; do not list here
    "/docs",
    "/openapi.json",
    "/redoc",
)


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next) -> Response:
        # Let CORS preflight pass without auth checks
        if request.method == "OPTIONS":
            return await call_next(request)
        if any(request.url.path.startswith(path) for path in PUBLIC_PATHS):
            return await call_next(request)

        try:
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
            jwt_service = getattr(request.app.state, "jwt_service", None)
            if jwt_service is None:
                raise RuntimeError("JWT service not configured")
            claims = jwt_service.decode(token)

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
        except (AuthError, PermissionDenied) as exc:
            payload = {"code": exc.code, "message": exc.message}
            if hasattr(exc, "details") and exc.details is not None:
                payload["details"] = exc.details
            return JSONResponse(status_code=exc.status_code, content=payload)
