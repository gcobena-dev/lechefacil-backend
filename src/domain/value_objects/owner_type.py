from __future__ import annotations

from enum import Enum


class OwnerType(str, Enum):
    ANIMAL = "animal"
    HEALTH_EVENT = "health_event"
    MILK_PRODUCTION_OCR = "milk_production_ocr"
    #: Scans of the paper certificate. Its own owner type, like the OCR photos
    #: above, so it shares the attachment machinery without ever turning up in
    #: the animal's photo gallery, its photo count or the herd report.
    ANIMAL_CERTIFICATE = "animal_certificate"
