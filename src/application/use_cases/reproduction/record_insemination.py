from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from src.application.errors import NotFound, ValidationError
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.animal_event import AnimalEvent, AnimalEventType
from src.domain.models.insemination import Insemination, InseminationMethod


@dataclass(slots=True)
class RecordInseminationInput:
    animal_id: UUID
    service_date: datetime
    method: str
    sire_catalog_id: UUID | None = None
    semen_inventory_id: UUID | None = None
    technician: str | None = None
    straw_count: int = 1
    heat_detected: bool = False
    protocol: str | None = None
    notes: str | None = None


@dataclass(slots=True)
class RecordInseminationOutput:
    insemination: Insemination
    service_event: AnimalEvent


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    payload: RecordInseminationInput,
    actor_user_id: UUID | None = None,
) -> RecordInseminationOutput:
    # Validate method
    valid_methods = {m.value for m in InseminationMethod}
    if payload.method not in valid_methods:
        raise ValidationError(f"Invalid method. Must be one of: {', '.join(valid_methods)}")

    # Validate animal exists and is female
    animal = await uow.animals.get(tenant_id, payload.animal_id)
    if not animal:
        raise NotFound(f"Animal {payload.animal_id} not found")
    if animal.sex == "MALE":
        raise ValidationError("Cannot inseminate a male animal")
    if animal.disposition_at is not None:
        raise ValidationError("Cannot inseminate a disposed animal")

    # Validate sire if provided
    sire = None
    if payload.sire_catalog_id:
        sire = await uow.sire_catalog.get(tenant_id, payload.sire_catalog_id)
        if not sire:
            raise NotFound(f"Sire {payload.sire_catalog_id} not found")

    # If AI method and semen_inventory_id provided, decrement straws
    semen_inventory_id = payload.semen_inventory_id
    if payload.method in (InseminationMethod.AI.value, InseminationMethod.IATF.value):
        if semen_inventory_id:
            stock = await uow.semen_inventory.get(tenant_id, semen_inventory_id)
            if not stock:
                raise NotFound(f"Semen inventory {semen_inventory_id} not found")
            stock.use_straws(payload.straw_count)
            await uow.semen_inventory.update(stock)

            # Emit low stock alert if quantity dropped to 5 or below
            if stock.current_quantity <= 5 and actor_user_id:
                try:
                    from src.application.events.models import SemenStockLowEvent

                    sire_name_for_alert = sire.name if sire else "Desconocido"
                    uow.add_event(
                        SemenStockLowEvent(
                            tenant_id=tenant_id,
                            actor_user_id=actor_user_id,
                            sire_catalog_id=stock.sire_catalog_id,
                            sire_name=sire_name_for_alert,
                            current_quantity=stock.current_quantity,
                            batch_code=stock.batch_code,
                        )
                    )
                except Exception:
                    pass  # best-effort

    # Ensure service_date is tz-aware
    service_date = payload.service_date
    if service_date.tzinfo is None:
        service_date = service_date.replace(tzinfo=timezone.utc)

    # The SERVICE event marks the service on the animal timeline; the service
    # itself lives in `inseminations` and stays there. Nothing about the bull,
    # the method or the technician is copied into the event: a copy made here
    # cannot follow later edits of the insemination, and the timeline ended up
    # showing the technician the service was created with while /reproduction
    # showed the current one. `list_events` joins the two and reads the live
    # record instead. The only snapshots this app keeps are the ones the device
    # has to take while it is offline.
    event_data: dict[str, str] = {}

    # The push notification is a message written once, from the values in hand
    # right now — it is not a view of the record, so it is built from its own
    # dict and never from what the event stores.
    notification_data: dict[str, str] = {"method": payload.method}
    if sire:
        notification_data["sire_name"] = sire.name
        if sire.registry_code:
            notification_data["external_sire_code"] = sire.registry_code
    if payload.technician:
        notification_data["technician"] = payload.technician

    service_event = AnimalEvent.create(
        tenant_id=tenant_id,
        animal_id=payload.animal_id,
        type=AnimalEventType.SERVICE,
        occurred_at=service_date,
        data=event_data,
    )
    created_event = await uow.animal_events.add(service_event)

    # Create the insemination record
    insemination = Insemination.create(
        tenant_id=tenant_id,
        animal_id=payload.animal_id,
        service_date=service_date,
        method=payload.method,
        sire_catalog_id=payload.sire_catalog_id,
        semen_inventory_id=semen_inventory_id,
        service_event_id=created_event.id,
        technician=payload.technician,
        straw_count=payload.straw_count,
        heat_detected=payload.heat_detected,
        protocol=payload.protocol,
        notes=payload.notes,
    )
    created_insemination = await uow.inseminations.add(insemination)

    # Emit notification event
    if actor_user_id:
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
                    event_data=notification_data,
                )
            )
        except Exception:
            pass  # best-effort

    return RecordInseminationOutput(
        insemination=created_insemination,
        service_event=created_event,
    )
