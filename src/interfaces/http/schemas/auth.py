from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from src.domain.value_objects.role import Role


class MembershipSchema(BaseModel):
    tenant_id: UUID
    role: Role


class MeResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    active_tenant: UUID
    active_role: Role
    memberships: list[MembershipSchema]
    claims: dict[str, Any]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: UUID | None = Field(default=None, description="Optional tenant to pin role claims")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: UUID
    email: EmailStr
    memberships: list[MembershipSchema]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: UUID
    role: Role
    is_active: bool = True


class RegisterResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    is_active: bool


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ChangePasswordResponse(BaseModel):
    status: str
