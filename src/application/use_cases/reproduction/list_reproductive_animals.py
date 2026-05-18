from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork

VALID_FILTERS = {"alertas", "inseminadas", "prenadas", "vacias", "sin_inseminar", "todas"}
VALID_SORTS = {"postpartum", "tag", "name"}


@dataclass(slots=True)
class ReproductiveAnimalRow:
    animal_id: UUID
    tag: str
    name: str | None
    days_postpartum: int | None
    last_calving_date: date | None
    alert_level: str  # optimal | warning | critical | none
    bucket: str  # prenadas | inseminadas | vacias | sin_inseminar
    situation_label: str  # human-friendly
    last_event_type: str | None  # calving | insemination | check
    last_event_date: date | None
    last_insemination_id: UUID | None
    last_insemination_status: str | None


@dataclass(slots=True)
class BucketCounts:
    alertas: int = 0
    inseminadas: int = 0
    prenadas: int = 0
    vacias: int = 0
    sin_inseminar: int = 0
    todas: int = 0


@dataclass(slots=True)
class ListReproductiveAnimalsOutput:
    items: list[ReproductiveAnimalRow] = field(default_factory=list)
    total: int = 0
    bucket_counts: BucketCounts = field(default_factory=BucketCounts)


def _bucket_for(status: str | None) -> str:
    if status is None:
        return "sin_inseminar"
    if status == "PENDING":
        return "inseminadas"
    if status == "CONFIRMED":
        return "prenadas"
    if status in ("OPEN", "LOST"):
        return "vacias"
    return "sin_inseminar"


def _alert_level(days_postpartum: int | None) -> str:
    if days_postpartum is None:
        return "none"
    if days_postpartum < 90:
        return "optimal"
    if days_postpartum <= 120:
        return "warning"
    return "critical"


def _situation_label(bucket: str, days_postpartum: int | None) -> str:
    # When the cow is alerted (high postpartum) but also has insemination history,
    # combine the labels — matches mockup "Inseminada · Vacía" etc.
    is_alerted = days_postpartum is not None and days_postpartum >= 90
    base = {
        "prenadas": "Preñada",
        "inseminadas": "Inseminada",
        "vacias": "Inseminada · Vacía",
        "sin_inseminar": "Sin inseminar",
    }.get(bucket, "—")
    if is_alerted and bucket == "inseminadas":
        # No real "vacía" yet, but alert + pending: just "Inseminada · Pendiente"
        return "Inseminada · Pendiente"
    return base


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    *,
    filter: str = "todas",
    sort: str = "postpartum",
    sort_dir: str = "desc",
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ListReproductiveAnimalsOutput:
    if filter not in VALID_FILTERS:
        filter = "todas"
    if sort not in VALID_SORTS:
        sort = "postpartum"
    if sort_dir not in ("asc", "desc"):
        sort_dir = "desc"

    # Pull data
    animals_result = await uow.animals.list(tenant_id, is_active=True)
    # animals.list() may return a plain list OR (items, next_cursor) depending on pagination args
    animals = animals_result[0] if isinstance(animals_result, tuple) else animals_result
    open_lactations = await uow.lactations.list_open_with_animal(tenant_id)
    latest_ins = await uow.inseminations.get_latest_per_animal(tenant_id)

    last_calving_by_animal: dict[UUID, date] = {
        lac["animal_id"]: lac["start_date"] for lac in open_lactations
    }

    today = datetime.now(timezone.utc).date()

    # Only female reproductively-eligible animals are considered.
    eligible = [a for a in animals if (a.sex or "").upper() == "FEMALE"]

    rows: list[ReproductiveAnimalRow] = []
    for animal in eligible:
        calving = last_calving_by_animal.get(animal.id)
        days_pp = (today - calving).days if calving else None
        ins = latest_ins.get(animal.id)
        status = ins["pregnancy_status"] if ins else None
        bucket = _bucket_for(status)
        alert = _alert_level(days_pp)

        # Determine last event: pick most recent of (calving, insemination, check)
        candidates: list[tuple[date, str]] = []
        if calving:
            candidates.append((calving, "calving"))
        if ins:
            sd = ins["service_date"]
            sd_date = sd.date() if isinstance(sd, datetime) else sd
            candidates.append((sd_date, "insemination"))
            check = ins["pregnancy_check_date"]
            if check:
                check_date = check.date() if isinstance(check, datetime) else check
                candidates.append((check_date, "check"))
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            last_event_date, last_event_type = candidates[0]
        else:
            last_event_date, last_event_type = None, None

        rows.append(
            ReproductiveAnimalRow(
                animal_id=animal.id,
                tag=animal.tag,
                name=animal.name,
                days_postpartum=days_pp,
                last_calving_date=calving,
                alert_level=alert,
                bucket=bucket,
                situation_label=_situation_label(bucket, days_pp),
                last_event_type=last_event_type,
                last_event_date=last_event_date,
                last_insemination_id=ins["insemination_id"] if ins else None,
                last_insemination_status=status,
            )
        )

    # Bucket counts (computed against the full eligible set)
    counts = BucketCounts(todas=len(rows))
    for r in rows:
        if r.bucket == "prenadas":
            counts.prenadas += 1
        elif r.bucket == "inseminadas":
            counts.inseminadas += 1
        elif r.bucket == "vacias":
            counts.vacias += 1
        elif r.bucket == "sin_inseminar":
            counts.sin_inseminar += 1
        # Alertas: high postpartum AND not confirmed (overlaps the others)
        if (
            r.days_postpartum is not None
            and r.days_postpartum >= 90
            and r.last_insemination_status != "CONFIRMED"
        ):
            counts.alertas += 1

    # Filter
    if filter == "alertas":
        filtered = [
            r for r in rows
            if r.days_postpartum is not None
            and r.days_postpartum >= 90
            and r.last_insemination_status != "CONFIRMED"
        ]
    elif filter == "todas":
        filtered = rows
    else:
        filtered = [r for r in rows if r.bucket == filter]

    if search:
        s = search.lower()
        filtered = [
            r for r in filtered
            if s in (r.tag or "").lower() or s in (r.name or "").lower()
        ]

    # Sort
    reverse = sort_dir == "desc"
    if sort == "postpartum":
        # Animals without postpartum at the end regardless of direction
        filtered.sort(
            key=lambda r: (r.days_postpartum is None, r.days_postpartum or 0),
            reverse=reverse,
        )
    elif sort == "tag":
        filtered.sort(key=lambda r: (r.tag or ""), reverse=reverse)
    elif sort == "name":
        filtered.sort(key=lambda r: (r.name or "").lower(), reverse=reverse)

    total = len(filtered)
    page = filtered[offset : offset + limit] if limit else filtered

    return ListReproductiveAnimalsOutput(items=page, total=total, bucket_counts=counts)
