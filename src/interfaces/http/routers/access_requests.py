from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from src.config.settings import Settings
from src.infrastructure.email.models import EmailMessage, EmailService
from src.infrastructure.email.renderer.engine import EmailTemplateRenderer
from src.interfaces.http.deps import get_app_settings
from src.interfaces.http.schemas.access_requests import AccessRequestPayload, AccessRequestResponse

router = APIRouter(prefix="/access-requests", tags=["access-requests"])


@router.post("/", response_model=AccessRequestResponse)
async def submit_access_request(
    payload: AccessRequestPayload,
    request: Request,
    settings: Settings = Depends(get_app_settings),
) -> AccessRequestResponse:
    # Compose email via templates
    renderer: EmailTemplateRenderer | None = getattr(request.app.state, "email_renderer", None)
    if renderer is None:
        raise RuntimeError("Email renderer not configured")
    msg = renderer.render(
        template_key="access_request",
        settings=settings,
        context={
            "full_name": payload.full_name,
            "email": payload.email,
            "phone_number": payload.phone_number,
            "farm_name": payload.farm_name,
            "farm_location": payload.farm_location,
            "requested_role": payload.requested_role,
            "message": payload.message,
        },
        locale=settings.email_default_locale,
    )
    to = settings.email_admin_recipients_list
    from_email = settings.email_from_address
    from_name = settings.email_from_name
    email_svc: EmailService | None = getattr(request.app.state, "email_service", None)
    if email_svc is None:
        raise RuntimeError("Email service not configured")
    await email_svc.send(
        EmailMessage(
            subject=msg.subject,
            to=to,
            text=msg.text,
            html=msg.html,
            from_email=from_email,
            from_name=from_name,
        )
    )
    return AccessRequestResponse(status="sent")
