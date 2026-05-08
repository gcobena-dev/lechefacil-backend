from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from src.application.errors import NotFound
from src.application.interfaces.unit_of_work import UnitOfWork
from src.application.use_cases.auth import bootstrap_tenant
from src.domain.models.access_request import AccessRequest
from src.domain.value_objects.access_request_status import AccessRequestStatus
from src.infrastructure.auth.password import PasswordHasher


@dataclass(slots=True)
class ApproveAccessRequestInput:
    request_id: UUID
    decided_by_user_id: UUID | None = None
    decision_notes: str | None = None


@dataclass(slots=True)
class ApproveAccessRequestResult:
    request: AccessRequest
    bootstrap: bootstrap_tenant.RegisterTenantResult
    was_already_decided: bool


async def execute(
    *,
    uow: UnitOfWork,
    payload: ApproveAccessRequestInput,
    password_hasher: PasswordHasher,
) -> ApproveAccessRequestResult:
    request = await uow.access_requests.get(payload.request_id)
    if request is None:
        raise NotFound("Access request not found")

    if request.status != AccessRequestStatus.PENDING:
        # Idempotent: return current state
        return ApproveAccessRequestResult(
            request=request,
            bootstrap=bootstrap_tenant.RegisterTenantResult(
                user_id=request.requester_user_id or UUID(int=0),
                tenant_id=request.created_tenant_id or UUID(int=0),
                email=request.email,
                created_user=False,
            ),
            was_already_decided=True,
        )

    # Random temp password — only used if the User has to be created. Existing users
    # keep their password. The set-password OneTimeToken is generated at the endpoint
    # layer and emailed separately.
    boot = await bootstrap_tenant.execute(
        uow=uow,
        payload=bootstrap_tenant.RegisterTenantInput(
            email=request.email,
            password=secrets.token_urlsafe(32),
            name=request.farm_name,
            location=request.farm_location,
        ),
        password_hasher=password_hasher,
    )

    request.status = AccessRequestStatus.APPROVED
    request.decided_by_user_id = payload.decided_by_user_id
    request.decided_at = datetime.now(timezone.utc)
    request.decision_notes = payload.decision_notes
    request.created_tenant_id = boot.tenant_id
    saved = await uow.access_requests.update(request)
    await uow.commit()
    return ApproveAccessRequestResult(request=saved, bootstrap=boot, was_already_decided=False)
