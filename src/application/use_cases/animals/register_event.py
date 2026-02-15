from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from src.application.errors import NotFound, PermissionDenied, ValidationError
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.animal import Animal
from src.domain.models.animal_event import AnimalEvent, AnimalEventType
from src.domain.models.animal_parentage import AnimalParentage, ParentageRelation
from src.domain.models.lactation import Lactation
from src.domain.value_objects.role import Role


@dataclass(slots=True)
class RegisterEventInput:
    animal_id: UUID
    type: str
    occurred_at: datetime
    data: dict | None = None


@dataclass(slots=True)
class RegisterEventOutput:
    event: AnimalEvent
    lactation_opened: Lactation | None = None
    lactation_closed: Lactation | None = None
    new_status_id: UUID | None = None
    calf_created: Animal | None = None
    parentage_created: list[AnimalParentage] | None = None
    disposition_set: bool = False
    message: str | None = None


def ensure_can_register_event(role: Role) -> None:
    if not role.can_update():
        raise PermissionDenied("Role not allowed to register events")


async def _handle_calving_event(
    uow: UnitOfWork,
    tenant_id: UUID,
    animal: Animal,
    event: AnimalEvent,
) -> RegisterEventOutput:
    """Handle CALVING event: close open lactation, open new one, set status to LACTATING."""

    # Validate: only females can calve
    if animal.sex == "MALE":
        raise ValidationError("Male animals cannot have calving events")

    # Validate: event cannot be in the future
    if event.occurred_at > datetime.now(timezone.utc):
        raise ValidationError("Event cannot be in the future")

    lactation_closed = None

    # Close any open lactation
    open_lactation = await uow.lactations.get_open(tenant_id, animal.id)
    if open_lactation:
        open_lactation.close(end_date=event.occurred_at.date())
        lactation_closed = await uow.lactations.update(open_lactation)

    # Get last lactation number
    last_number = await uow.lactations.get_last_number(tenant_id, animal.id)
    new_number = last_number + 1

    # Create new lactation
    new_lactation = Lactation.create(
        tenant_id=tenant_id,
        animal_id=animal.id,
        number=new_number,
        start_date=event.occurred_at.date(),
        calving_event_id=event.id,
    )
    lactation_opened = await uow.lactations.add(new_lactation)

    # Get LACTATING status
    lactating_status = await uow.animal_statuses.get_by_code(tenant_id, "LACTATING")
    new_status_id = lactating_status.id if lactating_status else None

    # Update animal status
    if new_status_id:
        await uow.animals.update(
            tenant_id=tenant_id,
            animal_id=animal.id,
            data={"status_id": new_status_id, "updated_at": datetime.now(timezone.utc)},
            expected_version=animal.version,
        )

    # Link the most recent CONFIRMED insemination to this calving event
    try:
        confirmed_insemination = await uow.inseminations.get_latest_confirmed(tenant_id, animal.id)
        if confirmed_insemination:
            confirmed_insemination.calving_event_id = event.id
            confirmed_insemination.bump_version()
            await uow.inseminations.update(confirmed_insemination)
    except Exception:
        pass  # best-effort; don't block calving on insemination linkage

    return RegisterEventOutput(
        event=event,
        lactation_opened=lactation_opened,
        lactation_closed=lactation_closed,
        new_status_id=new_status_id,
        message=f"Lactation #{new_number} started",
    )


async def _handle_dry_off_event(
    uow: UnitOfWork,
    tenant_id: UUID,
    animal: Animal,
    event: AnimalEvent,
) -> RegisterEventOutput:
    """Handle DRY_OFF event: close open lactation, set status to DRY."""

    # Validate: only females can be dried off
    if animal.sex == "MALE":
        raise ValidationError("Male animals cannot have dry-off events")

    # Validate: must have an open lactation
    open_lactation = await uow.lactations.get_open(tenant_id, animal.id)
    if not open_lactation:
        raise ValidationError("No open lactation to close")

    # Close the lactation
    open_lactation.close(end_date=event.occurred_at.date())
    lactation_closed = await uow.lactations.update(open_lactation)

    # Get DRY status
    dry_status = await uow.animal_statuses.get_by_code(tenant_id, "DRY")
    new_status_id = dry_status.id if dry_status else None

    # Update animal status
    if new_status_id:
        await uow.animals.update(
            tenant_id=tenant_id,
            animal_id=animal.id,
            data={"status_id": new_status_id, "updated_at": datetime.now(timezone.utc)},
            expected_version=animal.version,
        )

    return RegisterEventOutput(
        event=event,
        lactation_closed=lactation_closed,
        new_status_id=new_status_id,
        message="Animal dried off",
    )


async def _handle_disposition_event(
    uow: UnitOfWork,
    tenant_id: UUID,
    animal: Animal,
    event: AnimalEvent,
    status_code: str,
) -> RegisterEventOutput:
    """Handle SALE/DEATH/CULL events: set disposition and status."""

    # Get the corresponding status
    status = await uow.animal_statuses.get_by_code(tenant_id, status_code)
    new_status_id = status.id if status else None

    # Extract reason from data
    reason = None
    if event.data:
        reason = event.data.get("reason") or event.data.get("cause")

    # Update animal with disposition info
    update_data = {
        "status_id": new_status_id,
        "disposition_at": event.occurred_at,
        "disposition_reason": reason,
        "updated_at": datetime.now(timezone.utc),
    }

    await uow.animals.update(
        tenant_id=tenant_id,
        animal_id=animal.id,
        data=update_data,
        expected_version=animal.version,
    )

    # Close any open lactation
    lactation_closed = None
    open_lactation = await uow.lactations.get_open(tenant_id, animal.id)
    if open_lactation:
        open_lactation.close(end_date=event.occurred_at.date())
        lactation_closed = await uow.lactations.update(open_lactation)

    return RegisterEventOutput(
        event=event,
        lactation_closed=lactation_closed,
        new_status_id=new_status_id,
        disposition_set=True,
        message=f"Animal marked as {status_code.lower()}",
    )


async def _handle_service_event(
    uow: UnitOfWork,
    tenant_id: UUID,
    animal: Animal,
    event: AnimalEvent,
) -> RegisterEventOutput:
    """Handle SERVICE/EMBRYO_TRANSFER events: record sire parentage."""

    if event.data:
        event.data.get("sire_id")
        event.data.get("external_sire_code")
        event.data.get("external_sire_registry")

        # Only create parentage if we have sire information
        # This will be used when a calf is born from this service
        # For now, we just record it in the event data
        # Actual parentage will be created during BIRTH event

    return RegisterEventOutput(
        event=event,
        message="Service recorded",
    )


async def _handle_abortion_event(
    uow: UnitOfWork,
    tenant_id: UUID,
    animal: Animal,
    event: AnimalEvent,
) -> RegisterEventOutput:
    """Handle ABORTION event: mark the most recent CONFIRMED insemination as LOST."""

    # Best-effort: find the latest CONFIRMED insemination and mark it LOST
    try:
        confirmed = await uow.inseminations.get_latest_confirmed(tenant_id, animal.id)
        if confirmed:
            confirmed.mark_lost(
                check_date=event.occurred_at,
                checked_by=event.data.get("checked_by") if event.data else None,
            )
            await uow.inseminations.update(confirmed)
    except Exception:
        pass  # best-effort; don't block abortion event on insemination linkage

    return RegisterEventOutput(
        event=event,
        message="Abortion recorded",
    )


async def _handle_birth_event(
    uow: UnitOfWork,
    tenant_id: UUID,
    animal: Animal,
    event: AnimalEvent,
) -> RegisterEventOutput:
    """Handle BIRTH event: create calf and set parentage."""

    if not event.data:
        raise ValidationError("BIRTH event requires data with calf information")

    calf_tag = event.data.get("calf_tag")
    calf_sex = event.data.get("calf_sex")

    if not calf_tag or not calf_sex:
        raise ValidationError("BIRTH event requires calf_tag and calf_sex")

    # Validate sex
    if calf_sex not in ["MALE", "FEMALE"]:
        raise ValidationError("calf_sex must be MALE or FEMALE")

    # Get CALF status or use provided status_id
    calf_status = await uow.animal_statuses.get_by_code(tenant_id, "CALF")
    calf_status_id = calf_status.id if calf_status else None

    # Create the calf with breed information
    calf = Animal.create(
        tenant_id=tenant_id,
        tag=calf_tag,
        name=event.data.get("calf_name"),
        sex=calf_sex,
        birth_date=event.occurred_at.date(),
        dam_id=animal.id,  # Mother is the animal that had the birth event
        status_id=calf_status_id,
        breed=event.data.get("breed"),
        breed_variant=event.data.get("breed_variant"),
        breed_id=event.data.get("breed_id"),
        current_lot_id=event.data.get("current_lot_id"),
    )

    calf_created = await uow.animals.add(calf)

    # Create dam parentage record
    parentage_records = []
    dam_parentage = AnimalParentage.create(
        tenant_id=tenant_id,
        child_id=calf.id,
        relation=ParentageRelation.DAM,
        parent_animal_id=animal.id,
        source="event",
        effective_from=event.occurred_at.date(),
    )
    parentage_records.append(await uow.animal_parentage.add(dam_parentage))

    # Add sire parentage if provided
    sire_id = event.data.get("sire_id")
    external_sire_code = event.data.get("external_sire_code")
    external_sire_registry = event.data.get("external_sire_registry")

    if sire_id or external_sire_code:
        sire_parentage = AnimalParentage.create(
            tenant_id=tenant_id,
            child_id=calf.id,
            relation=ParentageRelation.SIRE,
            parent_animal_id=sire_id,
            external_code=external_sire_code,
            external_registry=external_sire_registry,
            source="event",
            effective_from=event.occurred_at.date(),
        )
        parentage_records.append(await uow.animal_parentage.add(sire_parentage))

        # Update calf with sire info
        await uow.animals.update(
            tenant_id=tenant_id,
            animal_id=calf.id,
            data={
                "sire_id": sire_id,
                "external_sire_code": external_sire_code,
                "external_sire_registry": external_sire_registry,
                "updated_at": datetime.now(timezone.utc),
            },
            expected_version=calf.version,
        )

    return RegisterEventOutput(
        event=event,
        calf_created=calf_created,
        parentage_created=parentage_records,
        message=f"Calf {calf_tag} created",
    )


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    role: Role,
    actor_user_id: UUID,
    payload: RegisterEventInput,
) -> RegisterEventOutput:
    """Register an animal event and apply its effects."""

    ensure_can_register_event(role)

    # Get the animal
    animal = await uow.animals.get(tenant_id, payload.animal_id)
    if not animal:
        raise NotFound(f"Animal {payload.animal_id} not found")

    # Check if animal is disposed
    if animal.disposition_at is not None:
        raise ValidationError(
            f"Cannot register events for disposed animals (disposed at {animal.disposition_at})"
        )

    # Create the event
    event = AnimalEvent.create(
        tenant_id=tenant_id,
        animal_id=payload.animal_id,
        type=payload.type,
        occurred_at=payload.occurred_at,
        data=payload.data,
    )

    # Save the event
    created_event = await uow.animal_events.add(event)

    # Handle event based on type
    output: RegisterEventOutput

    if payload.type == AnimalEventType.CALVING:
        output = await _handle_calving_event(uow, tenant_id, animal, created_event)
    elif payload.type == AnimalEventType.DRY_OFF:
        output = await _handle_dry_off_event(uow, tenant_id, animal, created_event)
    elif payload.type == AnimalEventType.SALE:
        output = await _handle_disposition_event(uow, tenant_id, animal, created_event, "SOLD")
    elif payload.type == AnimalEventType.DEATH:
        output = await _handle_disposition_event(uow, tenant_id, animal, created_event, "DEAD")
    elif payload.type == AnimalEventType.CULL:
        output = await _handle_disposition_event(uow, tenant_id, animal, created_event, "CULLED")
    elif payload.type == AnimalEventType.SERVICE or payload.type == AnimalEventType.EMBRYO_TRANSFER:
        output = await _handle_service_event(uow, tenant_id, animal, created_event)
    elif payload.type == AnimalEventType.BIRTH:
        output = await _handle_birth_event(uow, tenant_id, animal, created_event)
    elif payload.type == AnimalEventType.ABORTION:
        output = await _handle_abortion_event(uow, tenant_id, animal, created_event)
    else:
        # For other event types (TRANSFER, etc.), just record the event
        output = RegisterEventOutput(
            event=created_event,
            message=f"{payload.type} event recorded",
        )

    # Emit event for notifications
    try:
        from src.application.events.models import AnimalEventCreatedEvent

        uow.add_event(
            AnimalEventCreatedEvent(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                animal_id=animal.id,
                event_id=created_event.id,
                event_type=created_event.type,
                occurred_at=created_event.occurred_at,
                tag=animal.tag,
                name=animal.name,
                event_data=created_event.data,
            )
        )
    except Exception:
        pass

    await uow.commit()
    return output
