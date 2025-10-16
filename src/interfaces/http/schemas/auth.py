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
    must_change_password: bool
    memberships: list[MembershipSchema]
    # Optional: included for mobile flows when requested or when using Authorization-based refresh
    refresh_token: str | None = None


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


class RegisterTenantRequest(BaseModel):
    email: EmailStr
    password: str | None = None  # Optional: if not provided, generates one-time token
    tenant_id: UUID | None = None


class RegisterTenantResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    tenant_id: UUID


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ChangePasswordResponse(BaseModel):
    status: str


class AddMembershipRequest(BaseModel):
    tenant_id: UUID
    role: Role
    email: EmailStr | None = None
    user_id: UUID | None = None
    create_if_missing: bool = False
    initial_password: str | None = None


class AddMembershipResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    tenant_id: UUID
    role: Role
    created_user: bool
    generated_password: str | None = None


# Self-registration (no tenant)
class SelfRegisterRequest(BaseModel):
    email: EmailStr
    password: str


class SelfRegisterResponse(BaseModel):
    user_id: UUID
    email: EmailStr


class UserListResponse(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    role: Role
    is_active: bool
    created_at: str
    last_login: str | None = None


class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int
    pages: int


class UsersListResponse(BaseModel):
    users: list[UserListResponse]
    pagination: PaginationInfo


class RemoveMembershipRequest(BaseModel):
    reason: str | None = None


class RemoveMembershipResponse(BaseModel):
    message: str
    user_id: UUID
    tenant_id: UUID
    removed_at: str


# Password reset (forgot password)
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    status: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ResetPasswordResponse(BaseModel):
    status: str


# Set password with one-time token
class SetPasswordRequest(BaseModel):
    token: str
    new_password: str


class SetPasswordResponse(BaseModel):
    status: str
    message: str
