from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request, Response

from src.application.use_cases.auth import (
    bootstrap_tenant,
    change_password,
    get_me,
    list_tenant_users,
    login_user,
    manage_membership,
    register_account,
    register_user,
    remove_membership,
    update_membership_role,
)
from src.infrastructure.auth.context import AuthContext
from src.infrastructure.auth.jwt_service import JWTService
from src.infrastructure.auth.password import PasswordHasher
from src.interfaces.http.deps import (
    get_app_settings,
    get_auth_context,
    get_jwt_service,
    get_password_hasher,
    get_uow,
)
from src.interfaces.http.schemas.auth import (
    AddMembershipRequest,
    AddMembershipResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    MembershipSchema,
    MeResponse,
    PaginationInfo,
    RegisterRequest,
    RegisterResponse,
    RegisterTenantRequest,
    RegisterTenantResponse,
    RemoveMembershipRequest,
    RemoveMembershipResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SelfRegisterRequest,
    SelfRegisterResponse,
    SetPasswordRequest,
    SetPasswordResponse,
    UpdateMembershipRoleRequest,
    UpdateMembershipRoleResponse,
    UserListResponse,
    UsersListResponse,
)

router = APIRouter(prefix="", tags=["auth"])
logger = logging.getLogger(__name__)


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
    response: Response,
    request: Request,
    uow=Depends(get_uow),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    jwt_service: JWTService = Depends(get_jwt_service),
    settings=Depends(get_app_settings),
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
    # Issue refresh token cookie
    refresh = jwt_service.create_refresh_token(subject=result.user_id)
    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        path="/",
    )
    # Include refresh_token in body for mobile clients that request it
    include_refresh = (
        request.headers.get("X-Mobile-Client") == "1"
        or request.headers.get("X-Return-Refresh") == "1"
    )
    return LoginResponse(
        access_token=result.access_token,
        token_type=result.token_type,
        user_id=result.user_id,
        email=result.email,
        must_change_password=result.must_change_password,
        memberships=memberships,
        refresh_token=refresh if include_refresh else None,
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


@router.post("/auth/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password_endpoint(
    payload: ForgotPasswordRequest,
    request: Request,
    uow=Depends(get_uow),
    settings=Depends(get_app_settings),
) -> ForgotPasswordResponse:
    # Always respond OK to avoid email enumeration
    try:
        import secrets

        from src.domain.models.one_time_token import OneTimeToken

        async with uow:
            user = await uow.users.get_by_email(payload.email)

            if user and user.is_active:
                # Generate one-time token with 30 minute expiration
                token_value = secrets.token_urlsafe(32)
                one_time_token = OneTimeToken.create(
                    token=token_value,
                    user_id=user.id,
                    purpose="reset_password",
                    expires_in_minutes=30,  # Expires in 30 minutes
                    extra_data={"email": user.email},
                )

                await uow.one_time_tokens.add(one_time_token)
                await uow.commit()

                # Build reset link: prefer configured frontend base
                reset_base = getattr(settings, "email_reset_url_base", None)
                if reset_base:
                    base = reset_base.rstrip("/")
                else:
                    base = str(request.base_url).rstrip("/")
                reset_link = f"{base}/reset-password?token={token_value}"

                # Render and send email
                renderer = getattr(request.app.state, "email_renderer", None)
                email_svc = getattr(request.app.state, "email_service", None)
                if renderer and email_svc:
                    msg_tpl = renderer.render(
                        template_key="password_reset",
                        settings=settings,
                        context={
                            "email": user.email,
                            "reset_link": reset_link,
                            "expires_minutes": 30,
                            "token": token_value,
                        },
                    )
                    msg_tpl.to = [user.email]
                    msg_tpl.from_email = settings.email_from_address
                    msg_tpl.from_name = settings.email_from_name
                    await email_svc.send(msg_tpl)
                    logger.info(f"Password reset email sent to {user.email} with one-time token")
                else:
                    logger.info("Email components not configured; skipping reset email")
    except Exception as exc:  # pragma: no cover - best effort, do not leak errors
        logger.warning("forgot_password failed silently: %s", exc)
    return ForgotPasswordResponse(status="ok")


@router.post("/auth/reset-password", response_model=ResetPasswordResponse)
async def reset_password_endpoint(
    payload: ResetPasswordRequest,
    uow=Depends(get_uow),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> ResetPasswordResponse:
    """
    Resetea la contraseña usando un token de un solo uso con expiración de 30 minutos.
    El token se invalida después del primer uso exitoso.
    """
    from src.application.errors import AuthError

    async with uow:
        # Buscar el token
        token = await uow.one_time_tokens.get_by_token(payload.token)
        if not token:
            raise AuthError("Invalid or expired token")

        # Check if the token is valid (not used and not expired)
        if not token.is_valid():
            if token.is_used:
                raise AuthError("Token has already been used")
            elif token.is_expired():
                raise AuthError("Token has expired")
            else:
                raise AuthError("Invalid token")

        # Verify that the purpose is reset_password
        if token.purpose != "reset_password":
            raise AuthError("Invalid token purpose")

        # Get the user
        user = await uow.users.get(token.user_id)
        if not user or not user.is_active:
            raise AuthError("User not found or inactive")

        # Change the password
        hashed = password_hasher.hash(payload.new_password)
        await uow.users.update_password(token.user_id, hashed)

        # Mark the token as used
        await uow.one_time_tokens.mark_as_used(token.id)

        await uow.commit()

        logger.info(f"Password reset successfully for user {user.email} using one-time token")

    return ResetPasswordResponse(status="password_reset")


@router.post("/auth/set-password", response_model=SetPasswordResponse)
async def set_password_endpoint(
    payload: SetPasswordRequest,
    uow=Depends(get_uow),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> SetPasswordResponse:
    """
    Set a password using a one-time token (no expiration).
    The token is invalidated after the first successful use.
    Used for invitations and tenant creation.
    """

    from src.application.errors import AuthError

    async with uow:
        # Find the token
        token = await uow.one_time_tokens.get_by_token(payload.token)
        if not token:
            raise AuthError("Invalid or expired token")

        # Check if the token is valid (not used)
        if not token.is_valid():
            raise AuthError("Token has already been used")

        # Verify that the purpose is set_password
        if token.purpose != "set_password":
            raise AuthError("Invalid token purpose")

        # Get the user
        user = await uow.users.get(token.user_id)
        if not user or not user.is_active:
            raise AuthError("User not found or inactive")

        # Change the password
        hashed = password_hasher.hash(payload.new_password)
        await uow.users.update_password(token.user_id, hashed)

        # Mark the token as used
        await uow.one_time_tokens.mark_as_used(token.id)

        await uow.commit()

        logger.info(f"Password set successfully for user {user.email} using one-time token")

    return SetPasswordResponse(
        status="password_set", message="Password has been set successfully. You can now login."
    )


@router.post("/auth/register-tenant", response_model=RegisterTenantResponse, status_code=201)
async def register_tenant_endpoint(
    payload: RegisterTenantRequest,
    request: Request,
    uow=Depends(get_uow),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    settings=Depends(get_app_settings),
) -> RegisterTenantResponse:
    import secrets

    from src.application.errors import PermissionDenied
    from src.domain.models.one_time_token import OneTimeToken

    # Verify bootstrap API key for tenant creation
    api_key = request.headers.get("X-Bootstrap-Key")
    if not settings.bootstrap_secret_key:
        raise PermissionDenied("Tenant creation is disabled")
    if api_key != settings.bootstrap_secret_key.get_secret_value():
        raise PermissionDenied("Invalid bootstrap key")

    # Check if user already exists
    existing_user = await uow.users.get_by_email(payload.email)
    created_user = existing_user is None

    # Determine if we should generate a one-time token:
    # - Always for new users
    # - For existing users if no password is provided
    should_generate_token = created_user or payload.password is None

    # Use temporary password if we're generating token, otherwise use provided password
    temp_password = secrets.token_urlsafe(32) if should_generate_token else payload.password

    result = await bootstrap_tenant.execute(
        uow=uow,
        payload=bootstrap_tenant.RegisterTenantInput(
            email=payload.email,
            password=temp_password,
            tenant_id=payload.tenant_id,
        ),
        password_hasher=password_hasher,
    )

    # If we should generate token, create one-time token and send email
    if should_generate_token:
        # Generate one-time token
        token_value = secrets.token_urlsafe(32)
        one_time_token = OneTimeToken.create(
            token=token_value,
            user_id=result.user_id,
            purpose="set_password",
            extra_data={"tenant_id": str(result.tenant_id), "role": "ADMIN", "created_via": "api"},
        )

        async with uow:
            await uow.one_time_tokens.add(one_time_token)
            await uow.commit()

        # Send email with password setup link
        renderer = getattr(request.app.state, "email_renderer", None)
        email_svc = getattr(request.app.state, "email_service", None)

        if renderer and email_svc:
            # Build link for setting password
            set_password_base = getattr(settings, "email_reset_url_base", None)
            if set_password_base:
                base = set_password_base.rstrip("/")
            else:
                base = str(request.base_url).rstrip("/")
            set_password_link = f"{base}/set-password?token={token_value}"

            try:
                rendered = renderer.render(
                    template_key="membership_invite",
                    settings=settings,
                    context={
                        "user_email": payload.email,
                        "tenant_name": "LecheFácil",
                        "role": "ADMIN",
                        "is_new_user": True,
                        "set_password_link": set_password_link,
                        "login_link": f"{base}/login",
                    },
                )
                rendered.to = [payload.email]
                rendered.from_email = settings.email_from_address
                rendered.from_name = settings.email_from_name

                await email_svc.send(rendered)
                logger.info(f"Tenant creation email sent to {payload.email}")
            except Exception as exc:
                logger.warning(f"Failed to send tenant creation email: {exc}")

    return RegisterTenantResponse(
        user_id=result.user_id, email=result.email, tenant_id=result.tenant_id
    )


@router.get("/auth/my-tenants", response_model=list[MembershipSchema])
async def my_tenants(request: Request, uow=Depends(get_uow)) -> list[MembershipSchema]:
    from src.application.errors import AuthError

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
    from uuid import UUID

    user_id = UUID(str(subject))
    memberships = await uow.memberships.list_for_user(user_id)
    return [MembershipSchema(tenant_id=m.tenant_id, role=m.role) for m in memberships]


@router.post("/auth/memberships", response_model=AddMembershipResponse)
async def add_membership_endpoint(
    payload: AddMembershipRequest,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    request: Request = None,  # type: ignore[assignment]
    settings=Depends(get_app_settings),
) -> AddMembershipResponse:
    # Only ADMINs of the tenant in header can manage users for that tenant
    if not context.role.can_manage_users():
        from src.application.errors import PermissionDenied

        raise PermissionDenied("Only admins can manage memberships")
    if payload.tenant_id != context.tenant_id:
        from src.application.errors import PermissionDenied

        raise PermissionDenied("Cannot manage memberships for a different tenant")
    result = await manage_membership.execute(
        uow=uow,
        payload=manage_membership.AddMembershipInput(
            tenant_id=payload.tenant_id,
            role=payload.role,
            email=payload.email,
            user_id=payload.user_id,
            create_if_missing=payload.create_if_missing,
            initial_password=None,  # We don't use temporary password, we use token
        ),
        password_hasher=password_hasher,
    )

    # If a new user was created, generate one-time token and send email
    if result.created_user:
        import secrets

        from src.domain.models.one_time_token import OneTimeToken

        # Generate secure one-time token
        token_value = secrets.token_urlsafe(32)
        one_time_token = OneTimeToken.create(
            token=token_value,
            user_id=result.user_id,
            purpose="set_password",
            extra_data={"tenant_id": str(result.tenant_id), "role": result.role.value},
        )

        async with uow:
            await uow.one_time_tokens.add(one_time_token)
            await uow.commit()

        # Send email with password setup link
        renderer = getattr(request.app.state, "email_renderer", None)
        email_svc = getattr(request.app.state, "email_service", None)

        if renderer and email_svc:
            # Build link for setting password
            set_password_base = getattr(settings, "email_reset_url_base", None)
            if set_password_base:
                base = set_password_base.rstrip("/")
            else:
                base = str(request.base_url).rstrip("/")
            set_password_link = f"{base}/set-password?token={token_value}"

            try:
                msg_tpl = renderer.render(
                    template_key="membership_invite",
                    settings=settings,
                    context={
                        "email": result.email,
                        "tenant_id": str(result.tenant_id),
                        "role": result.role.value,
                        "set_password_link": set_password_link,
                        "is_new_user": True,
                    },
                )
                msg_tpl.to = [result.email]
                msg_tpl.from_email = settings.email_from_address
                msg_tpl.from_name = settings.email_from_name
                await email_svc.send(msg_tpl)
                logger.info(
                    f"Membership invitation email sent to " f"{result.email} with one-time token"
                )
            except Exception as exc:
                logger.warning(f"Failed to send membership invitation email: {exc}")
        else:
            logger.warning("Email components not configured; skipping membership invitation email")

    # Si es un usuario existente, solo notificar que fue agregado al tenant
    else:
        renderer = getattr(request.app.state, "email_renderer", None)
        email_svc = getattr(request.app.state, "email_service", None)

        if renderer and email_svc:
            set_password_base = getattr(settings, "email_reset_url_base", None)
            if set_password_base:
                base = set_password_base.rstrip("/")
            else:
                base = str(request.base_url).rstrip("/")
            login_link = f"{base}/login"

            try:
                msg_tpl = renderer.render(
                    template_key="membership_invite",
                    settings=settings,
                    context={
                        "email": result.email,
                        "tenant_id": str(result.tenant_id),
                        "role": result.role.value,
                        "login_link": login_link,
                        "is_new_user": False,
                    },
                )
                msg_tpl.to = [result.email]
                msg_tpl.from_email = settings.email_from_address
                msg_tpl.from_name = settings.email_from_name
                await email_svc.send(msg_tpl)
                logger.info(f"Membership notification email sent to {result.email}")
            except Exception as exc:
                logger.warning(f"Failed to send membership notification email: {exc}")

    return AddMembershipResponse(
        user_id=result.user_id,
        email=result.email,
        tenant_id=result.tenant_id,
        role=result.role,
        created_user=result.created_user,
        generated_password=None,  # We no longer return password, we use token
    )


@router.post("/auth/refresh", response_model=LoginResponse)
async def refresh_token(
    request: Request, response: Response, uow=Depends(get_uow), settings=Depends(get_app_settings)
) -> LoginResponse:
    jwt_service: JWTService | None = getattr(request.app.state, "jwt_service", None)
    if jwt_service is None:
        raise RuntimeError("JWT service not configured")
    # Accept refresh from cookie, Authorization Bearer, or JSON body
    token = request.cookies.get("refresh_token")
    if not token:
        # Try Authorization header
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth_header:
            scheme, _, bearer = auth_header.partition(" ")
            if scheme.lower() == "bearer" and bearer:
                token = bearer.strip()
        # Try JSON body
        if not token:
            try:
                body = await request.json()
                if isinstance(body, dict):
                    candidate = body.get("refresh_token")
                    if isinstance(candidate, str) and candidate:
                        token = candidate
            except Exception:
                pass
    if not token:
        from src.application.errors import AuthError

        raise AuthError("Missing refresh token")
    claims = jwt_service.decode_refresh(token)
    from uuid import UUID as _UUID

    user_id = _UUID(str(claims.get("sub")))
    # Load user and memberships to return same shape as login
    async with uow:
        user = await uow.users.get(user_id)
        if not user or not user.is_active:
            from src.application.errors import AuthError

            raise AuthError("Inactive or missing user")
        memberships = await uow.memberships.list_for_user(user_id)
    access = jwt_service.create_access_token(subject=user_id)
    # Optionally rotate refresh
    new_refresh = jwt_service.create_refresh_token(subject=user_id)
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        path="/",
    )
    include_refresh = (
        bool(request.headers.get("Authorization") or request.headers.get("authorization"))
        or request.headers.get("X-Mobile-Client") == "1"
        or request.headers.get("X-Return-Refresh") == "1"
    )
    return LoginResponse(
        access_token=access,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        must_change_password=user.must_change_password,
        memberships=[MembershipSchema(tenant_id=m.tenant_id, role=m.role) for m in memberships],
        refresh_token=new_refresh if include_refresh else None,
    )


@router.post("/auth/logout")
async def logout_endpoint(response: Response) -> dict[str, str]:
    response.delete_cookie(key="refresh_token", path="/")
    return {"status": "ok"}


@router.post("/auth/signin", response_model=SelfRegisterResponse, status_code=201)
async def self_register_endpoint(
    payload: SelfRegisterRequest,
    uow=Depends(get_uow),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> SelfRegisterResponse:
    result = await register_account.execute(
        uow=uow,
        payload=register_account.SelfRegisterInput(email=payload.email, password=payload.password),
        password_hasher=password_hasher,
    )
    # Cast to expected types
    from uuid import UUID

    return SelfRegisterResponse(user_id=UUID(result.user_id), email=result.email)


@router.get("/tenants/{tenant_id}/users", response_model=UsersListResponse)
async def list_tenant_users_endpoint(
    tenant_id: str,
    page: int = 1,
    limit: int = 10,
    role: str | None = None,
    search: str | None = None,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> UsersListResponse:
    from uuid import UUID

    from src.domain.value_objects.role import Role

    tenant_uuid = UUID(tenant_id)

    # Check if user has access to this tenant
    if context.tenant_id != tenant_uuid:
        from src.application.errors import PermissionDenied

        raise PermissionDenied("Cannot access users from a different tenant")

    role_filter = None
    if role:
        try:
            role_filter = Role(role.upper())
        except ValueError as e:
            from src.application.errors import ValidationError

            raise ValidationError(f"Invalid role: {role}") from e

    result = await list_tenant_users.execute(
        uow=uow,
        payload=list_tenant_users.ListTenantUsersInput(
            tenant_id=tenant_uuid,
            page=page,
            limit=limit,
            role_filter=role_filter,
            search=search,
        ),
    )

    user_responses = []
    for user in result.users:
        user_responses.append(
            UserListResponse(
                id=user.id,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at,
                last_login=user.last_login,
            )
        )

    total_pages = (result.total + result.limit - 1) // result.limit

    return UsersListResponse(
        users=user_responses,
        pagination=PaginationInfo(
            page=result.page,
            limit=result.limit,
            total=result.total,
            pages=total_pages,
        ),
    )


@router.patch(
    "/tenants/{tenant_id}/users/{user_id}/membership",
    response_model=UpdateMembershipRoleResponse,
)
async def update_membership_role_endpoint(
    tenant_id: str,
    user_id: str,
    payload: UpdateMembershipRoleRequest,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> UpdateMembershipRoleResponse:
    from uuid import UUID

    tenant_uuid = UUID(tenant_id)
    user_uuid = UUID(user_id)

    if context.tenant_id != tenant_uuid:
        from src.application.errors import PermissionDenied

        raise PermissionDenied("Cannot manage memberships for a different tenant")

    result = await update_membership_role.execute(
        uow=uow,
        requester_id=context.user_id,
        requester_role=context.role,
        payload=update_membership_role.UpdateMembershipRoleInput(
            user_id=user_uuid,
            tenant_id=tenant_uuid,
            new_role=payload.role,
        ),
    )

    return UpdateMembershipRoleResponse(
        message=result.message,
        user_id=result.user_id,
        tenant_id=result.tenant_id,
        role=result.new_role,
        updated_at=result.updated_at,
    )


@router.delete(
    "/tenants/{tenant_id}/users/{user_id}/membership", response_model=RemoveMembershipResponse
)
async def remove_membership_endpoint(
    tenant_id: str,
    user_id: str,
    payload: RemoveMembershipRequest,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> RemoveMembershipResponse:
    from uuid import UUID

    tenant_uuid = UUID(tenant_id)
    user_uuid = UUID(user_id)

    # Check if user has access to this tenant
    if context.tenant_id != tenant_uuid:
        from src.application.errors import PermissionDenied

        raise PermissionDenied("Cannot manage memberships for a different tenant")

    result = await remove_membership.execute(
        uow=uow,
        requester_id=context.user_id,
        requester_role=context.role,
        payload=remove_membership.RemoveMembershipInput(
            user_id=user_uuid,
            tenant_id=tenant_uuid,
            reason=payload.reason,
        ),
    )

    return RemoveMembershipResponse(
        message=result.message,
        user_id=result.user_id,
        tenant_id=result.tenant_id,
        removed_at=result.removed_at,
    )
