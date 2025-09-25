from __future__ import annotations
from enum import Enum

class AnimalStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SOLD = "sold"
    DEAD = "dead"