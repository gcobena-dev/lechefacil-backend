from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.errors import ConflictError
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.access_request import AccessRequest


@dataclass(slots=True)
class SubmitAccessRequestInput:
    full_name: str
    email: str
    farm_name: str
    requested_role: str
    phone_number: str | None = None
    farm_location: str | None = None
    message: str | None = None
    requester_user_id: UUID | None = None


async def execute(*, uow: UnitOfWork, payload: SubmitAccessRequestInput) -> AccessRequest:
    existing = await uow.access_requests.find_open_by_email(payload.email)
    if existing is not None:
        raise ConflictError("Ya tienes una solicitud de acceso pendiente con este correo")

    request = AccessRequest.create(
        full_name=payload.full_name,
        email=payload.email,
        farm_name=payload.farm_name,
        requested_role=payload.requested_role,
        phone_number=payload.phone_number,
        farm_location=payload.farm_location,
        message=payload.message,
        requester_user_id=payload.requester_user_id,
    )
    saved = await uow.access_requests.add(request)
    await uow.commit()
    return saved
