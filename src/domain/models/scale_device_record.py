from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass(slots=True)
class ScaleDeviceRecord:
    id: UUID
    tenant_id: UUID
    device_id: UUID
    device_record_id: int
    codigo: str
    peso: Decimal
    fecha: str
    hora: str
    turno: str
    status: str  # pending | imported | rejected
    matched_animal_id: UUID | None = None
    milk_production_id: UUID | None = None
    batch_id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        device_id: UUID,
        device_record_id: int,
        codigo: str,
        peso: Decimal,
        fecha: str,
        hora: str,
        turno: str,
        batch_id: UUID,
    ) -> ScaleDeviceRecord:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            device_id=device_id,
            device_record_id=device_record_id,
            codigo=codigo,
            peso=peso,
            fecha=fecha,
            hora=hora,
            turno=turno,
            status="pending",
            batch_id=batch_id,
            created_at=now,
            updated_at=now,
        )
