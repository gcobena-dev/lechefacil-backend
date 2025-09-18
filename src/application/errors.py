from __future__ import annotations

from typing import Any, Mapping


class AppError(Exception):
    code = "app_error"
    status_code = 400

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class AuthError(AppError):
    code = "auth_error"
    status_code = 401


class PermissionDenied(AppError):
    code = "forbidden"
    status_code = 403


class NotFound(AppError):
    code = "not_found"
    status_code = 404


class ValidationError(AppError):
    code = "validation_error"
    status_code = 422


class ConflictError(AppError):
    code = "conflict"
    status_code = 409


class InfrastructureError(AppError):
    code = "infrastructure_error"
    status_code = 500
