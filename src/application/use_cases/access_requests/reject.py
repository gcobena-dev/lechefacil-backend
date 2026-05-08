from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from src.application.errors import NotFound
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.access_request import AccessRequest
from src.domain.value_objects.access_request_status import AccessRequestStatus


@dataclass(slots=True)
class RejectAccessRequestInput:
    request_id: UUID
    decided_by_user_id: UUID | None = None
    decision_notes: str | None = None


@dataclass(slots=True)
class RejectAccessRequestResult:
    request: AccessRequest
    was_already_decided: bool


async def execute(
    *, uow: UnitOfWork, payload: RejectAccessRequestInput
) -> RejectAccessRequestResult:
    request = await uow.access_requests.get(payload.request_id)
    if request is None:
        raise NotFound("Access request not found")

    if request.status != AccessRequestStatus.PENDING:
        return RejectAccessRequestResult(request=request, was_already_decided=True)

    request.status = AccessRequestStatus.REJECTED
    request.decided_by_user_id = payload.decided_by_user_id
    request.decided_at = datetime.now(timezone.utc)
    request.decision_notes = payload.decision_notes
    saved = await uow.access_requests.update(request)
    await uow.commit()
    return RejectAccessRequestResult(request=saved, was_already_decided=False)
