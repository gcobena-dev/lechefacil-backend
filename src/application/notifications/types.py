from __future__ import annotations


class NotificationType:
    """Canonical notification type names used across backend/frontend."""

    DELIVERY_RECORDED = "delivery_recorded"
    PRODUCTION_RECORDED = "production_recorded"
    PRODUCTION_LOW = "production_low"
    PRODUCTION_BULK_RECORDED = "production_bulk_recorded"


ALL_TYPES = {
    NotificationType.DELIVERY_RECORDED,
    NotificationType.PRODUCTION_RECORDED,
    NotificationType.PRODUCTION_LOW,
    NotificationType.PRODUCTION_BULK_RECORDED,
}
