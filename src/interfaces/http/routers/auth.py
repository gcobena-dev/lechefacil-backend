from __future__ import annotations

from fastapi import APIRouter, Depends

from src.application.use_cases.auth import get_me
from src.infrastructure.auth.context import AuthContext
from src.interfaces.http.deps import get_auth_context
from src.interfaces.http.schemas.auth import MembershipSchema, MeResponse

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.get("/me", response_model=MeResponse)
async def read_me(context: AuthContext = Depends(get_auth_context)) -> MeResponse:
    result = await get_me.execute(
        user_id=context.user_id,
        active_tenant=context.tenant_id,
        active_role=context.role,
        memberships=context.memberships,
        claims=context.claims,
    )
    memberships = [MembershipSchema(tenant_id=m.tenant_id, role=m.role) for m in result.memberships]
    return MeResponse(
        user_id=result.user_id,
        active_tenant=result.active_tenant,
        active_role=result.active_role,
        memberships=memberships,
        claims=result.claims,
    )
