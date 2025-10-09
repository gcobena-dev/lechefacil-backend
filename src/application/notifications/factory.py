from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any
from zoneinfo import ZoneInfo

from .types import NotificationType


@dataclass
class BuiltNotification:
    type: str
    title: str
    message: str
    data: dict[str, Any]


def _fmt(value: Any, decimals: int = 1) -> str:
    """Format numeric-like values to a string with N decimals (default 2).
    Falls back to str(value) if not numeric.
    """
    try:
        from decimal import Decimal

        if isinstance(value, (int, float)):
            return f"{value:.{decimals}f}"
        d = Decimal(str(value))
        return f"{d:.{decimals}f}"
    except Exception:
        return str(value)


_DOW_ES = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
_MON_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
_DEFAULT_TZ = ZoneInfo("America/Guayaquil")


def _format_day_date(
    d: date | datetime | None,
    *,
    include_time: bool = False,
    t: time | None = None,
    tz: ZoneInfo | None = _DEFAULT_TZ,
) -> str:
    """Return 'vie 05/oct' or with time 'vie 05/oct hh:mm' in es-ES style."""
    if d is None:
        return ""
    if isinstance(d, datetime):
        dt = d
        if tz is not None:
            # Normalize: assume UTC if naive, then convert to tz
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt = dt.astimezone(tz)
    else:
        dt = datetime.combine(d, time(0, 0))
    dow = _DOW_ES[dt.weekday()]
    mon = _MON_ES[dt.month - 1]
    day_str = f"{dt.day:02d}/{mon}"
    if include_time:
        hhmm = t.strftime("%H:%M") if t else dt.strftime("%H:%M")
        return f"{dow} {day_str} {hhmm}"
    return f"{dow} {day_str}"


def build_notification(ntype: str, **kwargs: Any) -> BuiltNotification:
    """
    Central place to build notification title/message/data from templates.
    Keep strings easy to find and translate.
    """
    if ntype == NotificationType.DELIVERY_RECORDED:
        buyer_name: str = kwargs.get("buyer_name", "Comprador")
        volume_l: str | float | int = kwargs.get("volume_l", "0")
        amount: str | float | int = kwargs.get("amount", "0")
        currency: str = kwargs.get("currency", "USD")
        delivery_id = kwargs.get("delivery_id")
        buyer_id = kwargs.get("buyer_id")
        d = kwargs.get("date")
        title_suffix = _format_day_date(d)
        title = f"Entrega registrada {title_suffix}"
        message = f"Se entregaron {_fmt(volume_l)}L por {currency} {_fmt(amount, 2)}"
        data = {
            "delivery_id": str(delivery_id) if delivery_id is not None else None,
            "buyer_id": str(buyer_id) if buyer_id is not None else None,
            "buyer_name": buyer_name,
            "volume_l": str(volume_l),
            "amount": str(amount),
            "currency": currency,
            "date": str(d) if d is not None else None,
        }
        return BuiltNotification(ntype, title, message, data)

    if ntype == NotificationType.PRODUCTION_RECORDED:
        animal_label: str = kwargs.get("animal_label", "Animal")
        animal_name: str = kwargs.get("animal_name", "")
        short_name = (
            (animal_name[:18] + "...") if animal_name and len(animal_name) > 21 else animal_name
        )
        volume_l: str | float | int = kwargs.get("volume_l", "0")
        shift: str = kwargs.get("shift", "AM")
        animal_id = kwargs.get("animal_id")
        production_id = kwargs.get("production_id")
        d = kwargs.get("date")
        title_date = _format_day_date(d)
        title = f"Producción registrada: {animal_label}" + (
            f" - {short_name}" if short_name else ""
        )
        message = f"Se registró {_fmt(volume_l)}L de leche - {title_date} {shift}"
        data = {
            "animal_id": str(animal_id) if animal_id is not None else None,
            "production_id": str(production_id) if production_id is not None else None,
            "volume_l": str(volume_l),
            "shift": shift,
            "date": str(d) if d is not None else None,
        }
        return BuiltNotification(ntype, title, message, data)

    if ntype == NotificationType.PRODUCTION_LOW:
        animal_label: str = kwargs.get("animal_label", "Animal")
        animal_name: str = kwargs.get("animal_name", "")
        short_name = (
            (animal_name[:18] + "...") if animal_name and len(animal_name) > 21 else animal_name
        )
        volume_l: str | float | int = kwargs.get("volume_l", "0")
        avg_hist: str | float | int = kwargs.get("avg_hist", "0")
        shift: str = kwargs.get("shift", "AM")
        animal_id = kwargs.get("animal_id")
        production_id = kwargs.get("production_id")
        d = kwargs.get("date")
        date_str = _format_day_date(d)
        title = f"⚠️ Producción baja: {animal_label}" + (f" - {short_name}" if short_name else "")
        message = f"{_fmt(volume_l)}L vs prom. {_fmt(avg_hist)}L - {date_str} {shift}"
        data = {
            "animal_id": str(animal_id) if animal_id is not None else None,
            "production_id": str(production_id) if production_id is not None else None,
            "volume_l": str(volume_l),
            "avg_hist": str(avg_hist),
            "shift": shift,
            "date": str(d) if d is not None else None,
        }
        return BuiltNotification(ntype, title, message, data)

    if ntype == NotificationType.PRODUCTION_BULK_RECORDED:
        count: int = int(kwargs.get("count", 0) or 0)
        total_volume_l: str | float | int = kwargs.get("total_volume_l", "0")
        shift: str = kwargs.get("shift", "AM")
        d = kwargs.get("date")
        title_date = _format_day_date(d)
        title = f"Registro masivo completado - {title_date} {shift}"
        message = f"Se registraron {count} animales con {_fmt(total_volume_l)}L totales"
        data = {
            "count": int(count),
            "total_volume_l": str(total_volume_l),
            "shift": shift,
            "date": str(d) if d is not None else None,
        }
        return BuiltNotification(ntype, title, message, data)

    # Fallback to pass-through
    return BuiltNotification(
        ntype,
        title=str(kwargs.get("title", "Notificación")),
        message=str(kwargs.get("message", "")),
        data=dict(kwargs.get("data", {})),
    )
