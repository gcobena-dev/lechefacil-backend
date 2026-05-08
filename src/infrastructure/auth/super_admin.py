from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Request

from src.application.errors import AuthError, PermissionDenied
from src.domain.models.user import User
from src.infrastructure.auth.jwt_service import JWTService
from src.interfaces.http.deps import get_uow


@dataclass(slots=True)
class SuperAdminContext:
    user_id: UUID
    email: str
    user: User


async def get_super_admin_context(request: Request, uow=Depends(get_uow)) -> SuperAdminContext:
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise AuthError("Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthError("Invalid Authorization header")

    jwt_service: JWTService | None = getattr(request.app.state, "jwt_service", None)
    if jwt_service is None:
        raise RuntimeError("JWT service not configured")
    claims = jwt_service.decode(token)
    subject = claims.get("sub")
    if not subject:
        raise AuthError("Token missing subject")

    user_id = UUID(str(subject))
    user = await uow.users.get(user_id)
    if not user or not user.is_active:
        raise AuthError("Inactive or missing user")
    if not getattr(user, "is_super_admin", False):
        raise PermissionDenied("Super admin privileges required")
    return SuperAdminContext(user_id=user.id, email=user.email, user=user)
