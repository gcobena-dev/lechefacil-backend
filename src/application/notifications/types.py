from __future__ import annotations


class NotificationType:
    """Canonical notification type names used across backend/frontend."""

    DELIVERY_RECORDED = "delivery_recorded"
    PRODUCTION_RECORDED = "production_recorded"
    PRODUCTION_LOW = "production_low"
    PRODUCTION_BULK_RECORDED = "production_bulk_recorded"
    ANIMAL_CREATED = "animal_created"
    ANIMAL_UPDATED = "animal_updated"
    ANIMAL_EVENT_CREATED = "animal_event_created"


ALL_TYPES = {
    NotificationType.DELIVERY_RECORDED,
    NotificationType.PRODUCTION_RECORDED,
    NotificationType.PRODUCTION_LOW,
    NotificationType.PRODUCTION_BULK_RECORDED,
    NotificationType.ANIMAL_CREATED,
    NotificationType.ANIMAL_UPDATED,
    NotificationType.ANIMAL_EVENT_CREATED,
}
