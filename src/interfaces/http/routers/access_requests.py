from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from src.application.errors import NotFound, ValidationError
from src.application.use_cases.access_requests import approve, reject, submit
from src.config.settings import Settings
from src.domain.models.one_time_token import OneTimeToken
from src.domain.value_objects.access_request_status import AccessRequestStatus
from src.infrastructure.auth.jwt_service import JWTService
from src.infrastructure.auth.password import PasswordHasher
from src.infrastructure.auth.super_admin import SuperAdminContext, get_super_admin_context
from src.infrastructure.email.models import EmailMessage, EmailService
from src.infrastructure.email.renderer.engine import EmailTemplateRenderer
from src.interfaces.http.deps import get_app_settings, get_password_hasher, get_uow
from src.interfaces.http.schemas.access_requests import (
    AccessRequestDecisionPayload,
    AccessRequestDetail,
    AccessRequestList,
    AccessRequestPayload,
    AccessRequestSubmitResponse,
)

router = APIRouter(prefix="/access-requests", tags=["access-requests"])
logger = logging.getLogger(__name__)


def _resolve_app_base_url(settings: Settings, request: Request) -> str:
    base = settings.app_base_url or settings.email_reset_url_base
    if base:
        return base.rstrip("/")
    return str(request.base_url).rstrip("/")


def _resolve_api_base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _try_extract_user_id(request: Request) -> UUID | None:
    auth = request.headers.get("Authorization") or request.headers.get("authorization")
    if not auth:
        return None
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    jwt_service: JWTService | None = getattr(request.app.state, "jwt_service", None)
    if jwt_service is None:
        return None
    try:
        claims = jwt_service.decode(token)
    except Exception:
        return None
    sub = claims.get("sub")
    try:
        return UUID(str(sub)) if sub else None
    except ValueError:
        return None


async def _create_magic_tokens(uow, request_id: UUID) -> tuple[str, str]:
    # Sentinel user_id for non-user-bound tokens (magic-link approvals).
    # The OneTimeToken model requires user_id; we never query by it for these.
    sentinel_user = UUID(int=0)
    approve_token = secrets.token_urlsafe(32)
    reject_token = secrets.token_urlsafe(32)
    await uow.one_time_tokens.add(
        OneTimeToken.create(
            token=approve_token,
            user_id=sentinel_user,
            purpose="approve_access_request",
            expires_in_minutes=60 * 24 * 7,
            extra_data={"request_id": str(request_id)},
        )
    )
    await uow.one_time_tokens.add(
        OneTimeToken.create(
            token=reject_token,
            user_id=sentinel_user,
            purpose="reject_access_request",
            expires_in_minutes=60 * 24 * 7,
            extra_data={"request_id": str(request_id)},
        )
    )
    await uow.commit()
    return approve_token, reject_token


async def _send_admin_notification(
    *,
    request: Request,
    settings: Settings,
    access_request,
    approve_token: str,
    reject_token: str,
    api_base: str,
    app_base: str,
) -> None:
    renderer: EmailTemplateRenderer | None = getattr(request.app.state, "email_renderer", None)
    email_svc: EmailService | None = getattr(request.app.state, "email_service", None)
    if renderer is None or email_svc is None:
        logger.warning("Email components not configured; skipping admin notification")
        return

    approve_link = (
        f"{api_base}/api/v1/access-requests/{access_request.id}/approve?token={approve_token}"
    )
    reject_link = (
        f"{api_base}/api/v1/access-requests/{access_request.id}/reject?token={reject_token}"
    )
    detail_link = f"{app_base}/admin/requests/{access_request.id}"

    msg = renderer.render(
        template_key="access_request",
        settings=settings,
        context={
            "full_name": access_request.full_name,
            "email": access_request.email,
            "phone_number": access_request.phone_number,
            "farm_name": access_request.farm_name,
            "farm_location": access_request.farm_location,
            "requested_role": access_request.requested_role,
            "message": access_request.message,
            "approve_link": approve_link,
            "reject_link": reject_link,
            "detail_link": detail_link,
        },
        locale=settings.email_default_locale,
    )
    to = settings.email_admin_recipients_list
    await email_svc.send(
        EmailMessage(
            subject=msg.subject,
            to=to,
            text=msg.text,
            html=msg.html,
            from_email=settings.email_from_address,
            from_name=settings.email_from_name,
        )
    )


async def _send_approved_email(
    *,
    request: Request,
    settings: Settings,
    access_request,
    set_password_link: str | None,
    app_base: str,
) -> None:
    renderer: EmailTemplateRenderer | None = getattr(request.app.state, "email_renderer", None)
    email_svc: EmailService | None = getattr(request.app.state, "email_service", None)
    if renderer is None or email_svc is None:
        logger.warning("Email components not configured; skipping approved email")
        return
    msg = renderer.render(
        template_key="access_request_approved",
        settings=settings,
        context={
            "full_name": access_request.full_name,
            "tenant_name": access_request.farm_name,
            "farm_name": access_request.farm_name,
            "set_password_link": set_password_link,
            "login_link": f"{app_base}/login",
        },
        locale=settings.email_default_locale,
    )
    await email_svc.send(
        EmailMessage(
            subject=msg.subject,
            to=[access_request.email],
            text=msg.text,
            html=msg.html,
            from_email=settings.email_from_address,
            from_name=settings.email_from_name,
        )
    )


async def _send_rejected_email(*, request: Request, settings: Settings, access_request) -> None:
    renderer: EmailTemplateRenderer | None = getattr(request.app.state, "email_renderer", None)
    email_svc: EmailService | None = getattr(request.app.state, "email_service", None)
    if renderer is None or email_svc is None:
        logger.warning("Email components not configured; skipping rejected email")
        return
    msg = renderer.render(
        template_key="access_request_rejected",
        settings=settings,
        context={
            "full_name": access_request.full_name,
            "farm_name": access_request.farm_name,
            "decision_notes": access_request.decision_notes,
        },
        locale=settings.email_default_locale,
    )
    await email_svc.send(
        EmailMessage(
            subject=msg.subject,
            to=[access_request.email],
            text=msg.text,
            html=msg.html,
            from_email=settings.email_from_address,
            from_name=settings.email_from_name,
        )
    )


def _is_token_valid_for(record, request_id: UUID, purpose: str) -> bool:
    if record is None or record.is_used:
        return False
    if record.purpose != purpose:
        return False
    if (record.extra_data or {}).get("request_id") != str(request_id):
        return False
    if record.expires_at is not None and record.expires_at < datetime.now(timezone.utc):
        return False
    return True


_HTML_STYLE = (
    "body{font-family:system-ui,sans-serif;max-width:520px;margin:80px auto;"
    "padding:24px;text-align:center;color:#111827}"
    "h1{font-size:22px;margin:0 0 8px 0}"
    "p{font-size:14px;line-height:1.6;color:#4b5563}"
)


def _html_response(title: str, body: str, *, status_code: int = 200) -> Response:
    html = (
        "<!doctype html>"
        '<html lang="es"><head><meta charset="utf-8">'
        f"<title>{title}</title>"
        f"<style>{_HTML_STYLE}</style>"
        f"</head><body><h1>{title}</h1><p>{body}</p></body></html>"
    )
    return Response(content=html, media_type="text/html", status_code=status_code)


_MAGIC_LINK_INVALID_MSG = (
    "El enlace ya fue usado, expiró o no es válido. "
    "Si la solicitud sigue pendiente, ábrela en el panel de administración."
)
_APPROVED_VIA_LINK_MSG = (
    "La solicitud fue aprobada y se envió correo al solicitante. " "Ya puedes cerrar esta pestaña."
)
_REJECTED_VIA_LINK_MSG = (
    "La solicitud fue rechazada y se notificó al solicitante. " "Ya puedes cerrar esta pestaña."
)


async def _maybe_generate_set_password_link(
    *, uow, request: Request, settings: Settings, approve_result
) -> str | None:
    if approve_result.was_already_decided:
        return None
    if not approve_result.bootstrap.created_user:
        return None
    token_value = secrets.token_urlsafe(32)
    await uow.one_time_tokens.add(
        OneTimeToken.create(
            token=token_value,
            user_id=approve_result.bootstrap.user_id,
            purpose="set_password",
            extra_data={
                "tenant_id": str(approve_result.bootstrap.tenant_id),
                "role": "ADMIN",
                "created_via": "access_request_approval",
            },
        )
    )
    await uow.commit()
    app_base = _resolve_app_base_url(settings, request)
    return f"{app_base}/set-password?token={token_value}"


@router.post("/", response_model=AccessRequestSubmitResponse)
async def submit_access_request(
    payload: AccessRequestPayload,
    request: Request,
    settings: Settings = Depends(get_app_settings),
    uow=Depends(get_uow),
) -> AccessRequestSubmitResponse:
    requester_user_id = _try_extract_user_id(request)
    result = await submit.execute(
        uow=uow,
        payload=submit.SubmitAccessRequestInput(
            full_name=payload.full_name,
            email=payload.email,
            farm_name=payload.farm_name,
            requested_role=payload.requested_role,
            phone_number=payload.phone_number,
            farm_location=payload.farm_location,
            message=payload.message,
            requester_user_id=requester_user_id,
        ),
    )
    try:
        approve_token, reject_token = await _create_magic_tokens(uow, result.id)
        await _send_admin_notification(
            request=request,
            settings=settings,
            access_request=result,
            approve_token=approve_token,
            reject_token=reject_token,
            api_base=_resolve_api_base_url(request),
            app_base=_resolve_app_base_url(settings, request),
        )
    except Exception as exc:
        logger.warning(f"Failed to send admin notification email: {exc}")
    return AccessRequestSubmitResponse(id=result.id, status=result.status.value)


@router.get("/", response_model=AccessRequestList)
async def list_access_requests(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    super_admin: SuperAdminContext = Depends(get_super_admin_context),
    uow=Depends(get_uow),
) -> AccessRequestList:
    status_enum: AccessRequestStatus | None = None
    if status:
        try:
            status_enum = AccessRequestStatus(status.lower())
        except ValueError as exc:
            raise ValidationError(f"Invalid status filter: {status}") from exc
    rows, total = await uow.access_requests.list(status=status_enum, limit=limit, offset=offset)
    return AccessRequestList(
        items=[AccessRequestDetail.model_validate(r) for r in rows],
        total=total,
    )


@router.get("/{request_id}", response_model=AccessRequestDetail)
async def get_access_request(
    request_id: UUID,
    super_admin: SuperAdminContext = Depends(get_super_admin_context),
    uow=Depends(get_uow),
) -> AccessRequestDetail:
    row = await uow.access_requests.get(request_id)
    if row is None:
        raise NotFound("Access request not found")
    return AccessRequestDetail.model_validate(row)


@router.post("/{request_id}/approve", response_model=AccessRequestDetail)
async def approve_access_request_endpoint(
    request_id: UUID,
    request: Request,
    payload: AccessRequestDecisionPayload | None = None,
    super_admin: SuperAdminContext = Depends(get_super_admin_context),
    uow=Depends(get_uow),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    settings: Settings = Depends(get_app_settings),
) -> AccessRequestDetail:
    notes = payload.notes if payload else None
    result = await approve.execute(
        uow=uow,
        payload=approve.ApproveAccessRequestInput(
            request_id=request_id,
            decided_by_user_id=super_admin.user_id,
            decision_notes=notes,
        ),
        password_hasher=password_hasher,
    )
    set_password_link = await _maybe_generate_set_password_link(
        uow=uow, request=request, settings=settings, approve_result=result
    )
    if not result.was_already_decided:
        try:
            await _send_approved_email(
                request=request,
                settings=settings,
                access_request=result.request,
                set_password_link=set_password_link,
                app_base=_resolve_app_base_url(settings, request),
            )
        except Exception as exc:
            logger.warning(f"Failed to send approved email: {exc}")
    return AccessRequestDetail.model_validate(result.request)


@router.post("/{request_id}/reject", response_model=AccessRequestDetail)
async def reject_access_request_endpoint(
    request_id: UUID,
    request: Request,
    payload: AccessRequestDecisionPayload | None = None,
    super_admin: SuperAdminContext = Depends(get_super_admin_context),
    uow=Depends(get_uow),
    settings: Settings = Depends(get_app_settings),
) -> AccessRequestDetail:
    notes = payload.notes if payload else None
    result = await reject.execute(
        uow=uow,
        payload=reject.RejectAccessRequestInput(
            request_id=request_id,
            decided_by_user_id=super_admin.user_id,
            decision_notes=notes,
        ),
    )
    if not result.was_already_decided:
        try:
            await _send_rejected_email(
                request=request, settings=settings, access_request=result.request
            )
        except Exception as exc:
            logger.warning(f"Failed to send rejected email: {exc}")
    return AccessRequestDetail.model_validate(result.request)


@router.get("/{request_id}/approve", include_in_schema=False)
async def approve_access_request_via_link(
    request_id: UUID,
    token: str,
    request: Request,
    uow=Depends(get_uow),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    settings: Settings = Depends(get_app_settings),
) -> Response:
    record = await uow.one_time_tokens.get_by_token(token)
    if not _is_token_valid_for(record, request_id, "approve_access_request"):
        return _html_response("Enlace inválido", _MAGIC_LINK_INVALID_MSG, status_code=403)

    result = await approve.execute(
        uow=uow,
        payload=approve.ApproveAccessRequestInput(
            request_id=request_id,
            decided_by_user_id=None,
            decision_notes=None,
        ),
        password_hasher=password_hasher,
    )
    set_password_link = await _maybe_generate_set_password_link(
        uow=uow, request=request, settings=settings, approve_result=result
    )
    if not result.was_already_decided:
        try:
            await _send_approved_email(
                request=request,
                settings=settings,
                access_request=result.request,
                set_password_link=set_password_link,
                app_base=_resolve_app_base_url(settings, request),
            )
        except Exception as exc:
            logger.warning(f"Failed to send approved email: {exc}")
    await uow.one_time_tokens.mark_as_used(record.id)
    await uow.commit()
    return _html_response("Solicitud aprobada", _APPROVED_VIA_LINK_MSG)


@router.get("/{request_id}/reject", include_in_schema=False)
async def reject_access_request_via_link(
    request_id: UUID,
    token: str,
    request: Request,
    uow=Depends(get_uow),
    settings: Settings = Depends(get_app_settings),
) -> Response:
    record = await uow.one_time_tokens.get_by_token(token)
    if not _is_token_valid_for(record, request_id, "reject_access_request"):
        return _html_response("Enlace inválido", _MAGIC_LINK_INVALID_MSG, status_code=403)

    result = await reject.execute(
        uow=uow,
        payload=reject.RejectAccessRequestInput(
            request_id=request_id,
            decided_by_user_id=None,
            decision_notes=None,
        ),
    )
    if not result.was_already_decided:
        try:
            await _send_rejected_email(
                request=request, settings=settings, access_request=result.request
            )
        except Exception as exc:
            logger.warning(f"Failed to send rejected email: {exc}")
    await uow.one_time_tokens.mark_as_used(record.id)
    await uow.commit()
    return _html_response("Solicitud rechazada", _REJECTED_VIA_LINK_MSG)
