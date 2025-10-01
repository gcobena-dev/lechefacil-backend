from __future__ import annotations

from enum import Enum


class OwnerType(str, Enum):
    ANIMAL = "animal"
    HEALTH_EVENT = "health_event"
    MILK_PRODUCTION_OCR = "milk_production_ocr"
