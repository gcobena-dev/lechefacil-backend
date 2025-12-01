from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status

from src.application.events.dispatcher import dispatch_events
from src.application.use_cases.animals import list_events, register_event
from src.infrastructure.auth.context import AuthContext
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.animal_events import (
    AnimalEventCreate,
    AnimalEventEffects,
    AnimalEventResponse,
    AnimalEventsListResponse,
)

router = APIRouter(tags=["animal-events"])


@router.post(
    "/animals/{animal_id}/events",
    status_code=status.HTTP_201_CREATED,
    response_model=AnimalEventEffects,
)
async def create_animal_event(
    animal_id: UUID,
    payload: AnimalEventCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AnimalEventEffects:
    """Register a new event for an animal.

    Event types:
    - CALVING: Closes current lactation and opens a new one, sets status to LACTATING
    - DRY_OFF: Closes current lactation, sets status to DRY
    - SALE/DEATH/CULL: Sets disposition fields and blocks future productions
    - SERVICE/EMBRYO_TRANSFER: Records breeding/service information
    - BIRTH: Creates calf and parentage records
    - ABORTION: Records pregnancy loss
    - TRANSFER: Records location/lot changes
    """
    input_data = register_event.RegisterEventInput(
        animal_id=animal_id,
        type=payload.type,
        occurred_at=payload.occurred_at,
        data=payload.data,
    )

    result = await register_event.execute(
        uow=uow,
        tenant_id=context.tenant_id,
        role=context.role,
        actor_user_id=context.user_id,
        payload=input_data,
    )

    # Get status code if new status was set
    status_code = None
    if result.new_status_id:
        async with uow:
            # Repo exposes get_by_id and get_by_code; use get_by_id here
            animal_status = await uow.animal_statuses.get_by_id(result.new_status_id)
            if animal_status:
                status_code = animal_status.code

    # Dispatch notifications in background (post-commit)
    events = uow.drain_events()
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory and events:
        background_tasks.add_task(dispatch_events, session_factory, events)

    return AnimalEventEffects(
        event=AnimalEventResponse.model_validate(result.event),
        lactation_opened=result.lactation_opened.id if result.lactation_opened else None,
        lactation_closed=result.lactation_closed.id if result.lactation_closed else None,
        new_status_id=result.new_status_id,
        new_status_code=status_code,
        calf_created=result.calf_created.id if result.calf_created else None,
        parentage_created=[p.id for p in result.parentage_created]
        if result.parentage_created
        else None,
        disposition_set=result.disposition_set,
        message=result.message,
    )


@router.get(
    "/animals/{animal_id}/events",
    response_model=AnimalEventsListResponse,
)
async def get_animal_events(
    animal_id: UUID,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AnimalEventsListResponse:
    """Get the timeline of events for an animal (paginated)."""
    # Optional: constrain per_page to frontend options 10,20,30,50 while allowing API flexibility
    if per_page not in (10, 20, 30, 50):
        per_page = 10

    result = await list_events.execute(
        uow=uow,
        tenant_id=context.tenant_id,
        role=context.role,
        animal_id=animal_id,
        page=page,
        per_page=per_page,
    )
    return AnimalEventsListResponse(
        items=[AnimalEventResponse.model_validate(e) for e in result.items],
        total=result.total,
        page=result.page,
        per_page=result.per_page,
    )
