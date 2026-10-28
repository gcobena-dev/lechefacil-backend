from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from src.application.errors import NotFound, PermissionDenied, ValidationError
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.animal import Animal
from src.domain.models.animal_event import AnimalEvent, AnimalEventType
from src.domain.models.animal_parentage import AnimalParentage, ParentageRelation
from src.domain.models.insemination import Insemination
from src.domain.models.lactation import Lactation
from src.domain.value_objects.role import Role
from src.utils.datetime_tz import local_date

# Window (in days between service and calving) within which a service can be
# credited with having produced that calving. Bovine gestation averages ~283
# days; the range is deliberately wide to also cover early/late calvings.
MIN_GESTATION_DAYS = 240
MAX_GESTATION_DAYS = 310

# A heifer or dry cow shows her pregnancy in her status; a lactating cow keeps
# LACTATING and her pregnancy is tracked by the reproduction module.
PREGNANT_STATUS_BY_OPEN = {"HEIFER": "PREGNANT_HEIFER", "DRY": "PREGNANT_DRY"}
OPEN_STATUS_BY_PREGNANT = {v: k for k, v in PREGNANT_STATUS_BY_OPEN.items()}
PREGNANT_STATUS_CODES = frozenset(OPEN_STATUS_BY_PREGNANT)


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


async def _close_open_lactation(
    uow: UnitOfWork,
    tenant_id: UUID,
    animal_id: UUID,
    end_date: date,
) -> Lactation | None:
    """Close the currently-open lactation for an animal, if there is one.

    Validates that the closing date is not earlier than the lactation's start
    date. An earlier date means the events were registered out of chronological
    order (e.g. a calving registered before the previous lactation's dry-off),
    which would otherwise persist a lactation with a negative days-in-milk.
    """
    open_lactation = await uow.lactations.get_open(tenant_id, animal_id)
    if not open_lactation:
        return None

    if end_date < open_lactation.start_date:
        raise ValidationError(
            f"No se puede cerrar la lactancia #{open_lactation.number} con fecha "
            f"{end_date.isoformat()}: es anterior a su fecha de inicio "
            f"({open_lactation.start_date.isoformat()}). Revisa el orden "
            f"cronológico de los eventos: el secado debe registrarse antes del parto."
        )

    open_lactation.close(end_date=end_date)
    return await uow.lactations.update(open_lactation)


async def _resolve_inseminations_on_calving(
    uow: UnitOfWork,
    tenant_id: UUID,
    animal: Animal,
    event: AnimalEvent,
) -> Insemination | None:
    """Settle the services that preceded a calving.

    A calving ends the reproductive cycle that produced it. Without this, a
    service whose pregnancy check was never registered stays PENDING forever and
    the cow keeps showing up as "Inseminada" long after she has calved.

    The most recent service compatible with the gestation length is credited
    with the pregnancy (CONFIRMED and linked to the calving event); any earlier
    service still pending is closed as OPEN, since it clearly did not take.

    Returns the service credited with the calving, if any: its bull is the
    calf's sire.
    """
    calving_at = event.occurred_at

    # An already-CONFIRMED service is the pregnancy on record: just link it.
    confirmed = await uow.inseminations.get_latest_confirmed(tenant_id, animal.id)
    if confirmed:
        confirmed.calving_event_id = event.id
        confirmed.bump_version()
        await uow.inseminations.update(confirmed)

    pending = await uow.inseminations.list_pending_before(tenant_id, animal.id, calving_at)
    credited = confirmed
    for insemination in pending:
        gestation_days = (local_date(calving_at) - local_date(insemination.service_date)).days
        if credited is None and MIN_GESTATION_DAYS <= gestation_days <= MAX_GESTATION_DAYS:
            insemination.confirm_pregnancy(check_date=calving_at)
            insemination.calving_event_id = event.id
            credited = insemination
        else:
            insemination.mark_open(check_date=calving_at)
        await uow.inseminations.update(insemination)
    return credited


async def _status_code(uow: UnitOfWork, animal: Animal) -> str | None:
    if not animal.status_id:
        return None
    status = await uow.animal_statuses.get_by_id(animal.status_id)
    return status.code if status else None


async def _status_id(uow: UnitOfWork, tenant_id: UUID, code: str) -> UUID | None:
    status = await uow.animal_statuses.get_by_code(tenant_id, code)
    return status.id if status else None


async def _is_pregnant(uow: UnitOfWork, tenant_id: UUID, animal: Animal) -> bool:
    """Whether the animal carries a pregnancy that has not ended yet.

    Either a confirmed service not yet linked to a calving (and done after her
    last calving), or a "pregnant" status set by hand, e.g. for natural service
    that was never recorded.
    """
    if await _status_code(uow, animal) in PREGNANT_STATUS_CODES:
        return True
    return await has_confirmed_pregnancy(uow, tenant_id, animal)


async def has_confirmed_pregnancy(uow: UnitOfWork, tenant_id: UUID, animal: Animal) -> bool:
    """A confirmed service that is still ongoing (no calving after it)."""
    confirmed = await uow.inseminations.get_latest_confirmed(tenant_id, animal.id)
    if not confirmed:
        return False
    lactations = await uow.lactations.list_by_animal(tenant_id, animal.id)
    last_calving = max((lac.start_date for lac in lactations), default=None)
    return last_calving is None or local_date(confirmed.service_date) > last_calving


async def apply_pregnancy_status(
    uow: UnitOfWork, tenant_id: UUID, animal: Animal, pregnant: bool
) -> UUID | None:
    """Move HEIFER/DRY to their pregnant status and back.

    A lactating cow keeps LACTATING while pregnant: her pregnancy is tracked by
    the reproduction module and only shows in her status once she is dried off.
    Returns the new status id, or None when the status does not change.
    """
    code = await _status_code(uow, animal)
    mapping = PREGNANT_STATUS_BY_OPEN if pregnant else OPEN_STATUS_BY_PREGNANT
    target = mapping.get(code or "")
    if not target:
        return None
    new_status_id = await _status_id(uow, tenant_id, target)
    if new_status_id:
        await uow.animals.update(
            tenant_id=tenant_id,
            animal_id=animal.id,
            data={"status_id": new_status_id, "updated_at": datetime.now(UTC)},
            expected_version=animal.version,
        )
    return new_status_id


async def _lot_fields(uow: UnitOfWork, tenant_id: UUID, lot_id: UUID | str | None) -> dict:
    """`current_lot_id` plus the lot name stored beside it, for an update."""
    if not lot_id:
        return {}
    lot = await uow.lots.get(tenant_id, UUID(str(lot_id)))
    if not lot or not lot.active:
        raise ValidationError("El lote seleccionado no existe o está inactivo")
    return {"current_lot_id": lot.id, "lot": lot.name}


async def _sire_from_service(
    uow: UnitOfWork, tenant_id: UUID, service: Insemination | None
) -> dict:
    """Sire fields for the calf, from the bull of the service that produced it."""
    if not service or not service.sire_catalog_id:
        return {}
    sire = await uow.sire_catalog.get(tenant_id, service.sire_catalog_id)
    if not sire:
        return {}
    return {"sire_catalog_id": sire.id, "sire_id": sire.animal_id}


async def _create_calf(
    uow: UnitOfWork,
    tenant_id: UUID,
    dam: Animal,
    event: AnimalEvent,
    calf_data: dict,
    sire: dict,
) -> tuple[Animal, list[AnimalParentage]]:
    """Create the calf of `dam` with its dam/sire genealogy.

    `sire` may hold `sire_id` (herd bull), `sire_catalog_id` (reproduction
    catalog) and/or `external_sire_code`/`external_sire_registry` (free text).
    """
    tag = calf_data.get("tag")
    sex = calf_data.get("sex")
    if not tag or not sex:
        raise ValidationError("La cría requiere arete y sexo")
    if sex not in ("MALE", "FEMALE"):
        raise ValidationError("calf_sex must be MALE or FEMALE")

    lot = await _lot_fields(uow, tenant_id, calf_data.get("lot_id"))
    birth_date = local_date(event.occurred_at)
    calf = Animal.create(
        tenant_id=tenant_id,
        tag=tag,
        name=calf_data.get("name"),
        sex=sex,
        birth_date=birth_date,
        dam_id=dam.id,
        status_id=await _status_id(uow, tenant_id, "CALF"),
        breed=calf_data.get("breed"),
        breed_variant=calf_data.get("breed_variant"),
        breed_id=calf_data.get("breed_id"),
        lot=lot.get("lot"),
        current_lot_id=lot.get("current_lot_id"),
        sire_id=sire.get("sire_id"),
        sire_catalog_id=sire.get("sire_catalog_id"),
        external_sire_code=sire.get("external_sire_code"),
        external_sire_registry=sire.get("external_sire_registry"),
    )
    calf = await uow.animals.add(calf)

    parentage = [
        await uow.animal_parentage.add(
            AnimalParentage.create(
                tenant_id=tenant_id,
                child_id=calf.id,
                relation=ParentageRelation.DAM,
                parent_animal_id=dam.id,
                source="event",
                effective_from=birth_date,
            )
        )
    ]
    external_code = sire.get("external_sire_code")
    if sire.get("sire_catalog_id") and not sire.get("sire_id") and not external_code:
        catalog_sire = await uow.sire_catalog.get(tenant_id, sire["sire_catalog_id"])
        external_code = catalog_sire.name if catalog_sire else None
    if sire.get("sire_id") or external_code:
        parentage.append(
            await uow.animal_parentage.add(
                AnimalParentage.create(
                    tenant_id=tenant_id,
                    child_id=calf.id,
                    relation=ParentageRelation.SIRE,
                    parent_animal_id=sire.get("sire_id"),
                    external_code=None if sire.get("sire_id") else external_code,
                    external_registry=sire.get("external_sire_registry"),
                    source="event",
                    effective_from=birth_date,
                )
            )
        )
    return calf, parentage


async def _handle_calving_event(
    uow: UnitOfWork,
    tenant_id: UUID,
    animal: Animal,
    event: AnimalEvent,
) -> RegisterEventOutput:
    """Handle CALVING: the cow calves and, optionally, her calf is registered.

    - closes the open lactation and opens the next one;
    - sets the cow to LACTATING (she is no longer pregnant);
    - settles her services, crediting the one that produced this calving;
    - optionally moves her to `data.mother_lot_id` (farms move fresh cows to
      different lots, so there is no fixed destination);
    - optionally creates `data.calf` ({tag, sex, name?, birth_weight?, breed?,
      breed_id?, breed_variant?, lot_id?}), whose sire is the bull of the
      credited service unless the form gives one.
    """
    if animal.sex == "MALE":
        raise ValidationError("Male animals cannot have calving events")
    if event.occurred_at > datetime.now(UTC):
        raise ValidationError("Event cannot be in the future")

    data = event.data or {}
    calving_date = local_date(event.occurred_at)
    mother_lot = await _lot_fields(uow, tenant_id, data.get("mother_lot_id"))

    lactation_closed = await _close_open_lactation(uow, tenant_id, animal.id, calving_date)
    new_number = await uow.lactations.get_last_number(tenant_id, animal.id) + 1
    lactation_opened = await uow.lactations.add(
        Lactation.create(
            tenant_id=tenant_id,
            animal_id=animal.id,
            number=new_number,
            start_date=calving_date,
            calving_event_id=event.id,
        )
    )

    new_status_id = await _status_id(uow, tenant_id, "LACTATING")
    updates: dict = {**mother_lot}
    if new_status_id:
        updates["status_id"] = new_status_id
    if updates:
        updates["updated_at"] = datetime.now(UTC)
        await uow.animals.update(
            tenant_id=tenant_id,
            animal_id=animal.id,
            data=updates,
            expected_version=animal.version,
        )

    # Close out the reproductive cycle this calving ends
    credited = None
    try:
        credited = await _resolve_inseminations_on_calving(uow, tenant_id, animal, event)
    except Exception:
        pass  # best-effort; don't block calving on insemination linkage

    calf_created = None
    parentage_created = None
    calf_data = data.get("calf")
    if calf_data:
        sire = {
            k: calf_data[k]
            for k in ("sire_id", "sire_catalog_id", "external_sire_code", "external_sire_registry")
            if calf_data.get(k)
        } or await _sire_from_service(uow, tenant_id, credited)
        calf_created, parentage_created = await _create_calf(
            uow, tenant_id, animal, event, calf_data, sire
        )

    message = f"Lactation #{new_number} started"
    if calf_created:
        message += f", calf {calf_created.tag} created"
    return RegisterEventOutput(
        event=event,
        lactation_opened=lactation_opened,
        lactation_closed=lactation_closed,
        new_status_id=new_status_id,
        calf_created=calf_created,
        parentage_created=parentage_created,
        message=message,
    )


async def _handle_dry_off_event(
    uow: UnitOfWork,
    tenant_id: UUID,
    animal: Animal,
    event: AnimalEvent,
) -> RegisterEventOutput:
    """Handle DRY_OFF: close the open lactation, set DRY or PREGNANT_DRY.

    Cows are usually dried off two months before calving, so a cow that got
    pregnant while in milk goes to "Seca y gestante", not to "Seca".
    """
    if animal.sex == "MALE":
        raise ValidationError("Male animals cannot have dry-off events")

    lactation_closed = await _close_open_lactation(
        uow, tenant_id, animal.id, local_date(event.occurred_at)
    )

    code = "PREGNANT_DRY" if await _is_pregnant(uow, tenant_id, animal) else "DRY"
    new_status_id = await _status_id(uow, tenant_id, code)
    if new_status_id:
        await uow.animals.update(
            tenant_id=tenant_id,
            animal_id=animal.id,
            data={"status_id": new_status_id, "updated_at": datetime.now(UTC)},
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
        "updated_at": datetime.now(UTC),
    }

    await uow.animals.update(
        tenant_id=tenant_id,
        animal_id=animal.id,
        data=update_data,
        expected_version=animal.version,
    )

    # Close any open lactation
    lactation_closed = await _close_open_lactation(
        uow, tenant_id, animal.id, local_date(event.occurred_at)
    )

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
    """Handle ABORTION: the pregnancy is lost.

    Marks the confirmed service as LOST and takes a pregnant heifer or dry cow
    back to HEIFER/DRY. A lactating cow stays LACTATING.
    """
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

    new_status_id = await apply_pregnancy_status(uow, tenant_id, animal, pregnant=False)

    return RegisterEventOutput(
        event=event,
        new_status_id=new_status_id,
        message="Abortion recorded",
    )


async def _handle_birth_event(
    uow: UnitOfWork,
    tenant_id: UUID,
    animal: Animal,
    event: AnimalEvent,
) -> RegisterEventOutput:
    """Handle BIRTH: create the calf only, the mother is not touched.

    The app registers calvings with CALVING (which can also create the calf);
    BIRTH stays for app builds older than 0.0.987.
    """
    if not event.data:
        raise ValidationError("BIRTH event requires data with calf information")
    data = event.data
    if not data.get("calf_tag") or not data.get("calf_sex"):
        raise ValidationError("BIRTH event requires calf_tag and calf_sex")

    calf_data = {
        "tag": data.get("calf_tag"),
        "sex": data.get("calf_sex"),
        "name": data.get("calf_name"),
        "breed": data.get("breed"),
        "breed_variant": data.get("breed_variant"),
        "breed_id": data.get("breed_id"),
        "lot_id": data.get("current_lot_id"),
    }
    sire = {
        k: data[k]
        for k in ("sire_id", "sire_catalog_id", "external_sire_code", "external_sire_registry")
        if data.get(k)
    }
    calf, parentage = await _create_calf(uow, tenant_id, animal, event, calf_data, sire)

    return RegisterEventOutput(
        event=event,
        calf_created=calf,
        parentage_created=parentage,
        message=f"Calf {calf.tag} created",
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
