from __future__ import annotations

from fastapi import APIRouter, Depends

from src.application.use_cases.auth import change_password, get_me, login_user, register_user
from src.infrastructure.auth.context import AuthContext
from src.infrastructure.auth.jwt_service import JWTService
from src.infrastructure.auth.password import PasswordHasher
from src.interfaces.http.deps import get_auth_context, get_jwt_service, get_password_hasher, get_uow
from src.interfaces.http.schemas.auth import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginRequest,
    LoginResponse,
    MembershipSchema,
    MeResponse,
    RegisterRequest,
    RegisterResponse,
)

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.get("/me", response_model=MeResponse)
async def read_me(context: AuthContext = Depends(get_auth_context)) -> MeResponse:
    result = await get_me.execute(
        user_id=context.user_id,
        email=context.email,
        active_tenant=context.tenant_id,
        active_role=context.role,
        memberships=context.memberships,
        claims=context.claims,
    )
    memberships = [MembershipSchema(tenant_id=m.tenant_id, role=m.role) for m in result.memberships]
    return MeResponse(
        user_id=result.user_id,
        email=result.email,
        active_tenant=result.active_tenant,
        active_role=result.active_role,
        memberships=memberships,
        claims=result.claims,
    )


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    uow=Depends(get_uow),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> LoginResponse:
    result = await login_user.execute(
        uow=uow,
        payload=login_user.LoginInput(
            email=payload.email,
            password=payload.password,
            tenant_id=payload.tenant_id,
        ),
        password_hasher=password_hasher,
        jwt_service=jwt_service,
    )
    memberships = [MembershipSchema(**m) for m in result.memberships]
    return LoginResponse(
        access_token=result.access_token,
        token_type=result.token_type,
        user_id=result.user_id,
        email=result.email,
        memberships=memberships,
    )


@router.post("/auth/register", response_model=RegisterResponse, status_code=201)
async def register_user_endpoint(
    payload: RegisterRequest,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> RegisterResponse:
    user = await register_user.execute(
        uow=uow,
        requester_role=context.role,
        payload=register_user.RegisterUserInput(
            email=payload.email,
            password=payload.password,
            tenant_id=payload.tenant_id,
            role=payload.role,
            is_active=payload.is_active,
        ),
        password_hasher=password_hasher,
    )
    return RegisterResponse(user_id=user.id, email=user.email, is_active=user.is_active)


@router.post("/auth/change-password", response_model=ChangePasswordResponse)
async def change_password_endpoint(
    payload: ChangePasswordRequest,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> ChangePasswordResponse:
    await change_password.execute(
        uow=uow,
        requester_id=context.user_id,
        requester_role=context.role,
        payload=change_password.ChangePasswordInput(
            user_id=context.user_id,
            current_password=payload.current_password,
            new_password=payload.new_password,
        ),
        password_hasher=password_hasher,
    )
    return ChangePasswordResponse(status="password_changed")
