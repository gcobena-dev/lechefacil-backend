from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.utils.datetime_tz import format_day_date

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


def _short_label(s: str | None, *, max_len: int = 16) -> str | None:
    """Shorten labels like actor name to a safe length with ellipsis.

    Keeps UI tidy on mobile; 16 chars balances readability and space.
    """
    if not s:
        return s
    s = str(s)
    return s if len(s) <= max_len else (s[: max(0, max_len - 1)] + "…")


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
        d = kwargs.get("date_time")
        title_suffix = format_day_date(d)
        actor: str | None = _short_label(kwargs.get("actor_label"))
        title = f"🚚 Entrega registrada {title_suffix}"
        message = f"Se entregaron {_fmt(volume_l)}L por {currency} {_fmt(amount, 2)}"
        if actor:
            message += f" • por {actor}"
        data = {
            "delivery_id": str(delivery_id) if delivery_id is not None else None,
            "buyer_id": str(buyer_id) if buyer_id is not None else None,
            "buyer_name": buyer_name,
            "volume_l": str(volume_l),
            "amount": str(amount),
            "currency": currency,
            "date": str(d) if d is not None else None,
            "actor": actor,
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
        d = kwargs.get("date_time")
        title_date = format_day_date(d)
        actor: str | None = _short_label(kwargs.get("actor_label"))
        title = f"🥛 Producción registrada: {animal_label}" + (
            f" - {short_name}" if short_name else ""
        )
        message = f"Se registró {_fmt(volume_l)}L de leche - {title_date} {shift}"
        if actor:
            message += f" • por {actor}"
        data = {
            "animal_id": str(animal_id) if animal_id is not None else None,
            "production_id": str(production_id) if production_id is not None else None,
            "volume_l": str(volume_l),
            "shift": shift,
            "date": str(d) if d is not None else None,
            "actor": actor,
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
        d = kwargs.get("date_time")
        date_str = format_day_date(d)
        actor: str | None = _short_label(kwargs.get("actor_label"))
        title = f"⚠️ Producción baja: {animal_label}" + (f" - {short_name}" if short_name else "")
        message = f"{_fmt(volume_l)}L vs prom. {_fmt(avg_hist)}L - {date_str} {shift}"
        if actor:
            message += f" • por {actor}"
        data = {
            "animal_id": str(animal_id) if animal_id is not None else None,
            "production_id": str(production_id) if production_id is not None else None,
            "volume_l": str(volume_l),
            "avg_hist": str(avg_hist),
            "shift": shift,
            "date": str(d) if d is not None else None,
            "actor": actor,
        }
        return BuiltNotification(ntype, title, message, data)

    if ntype == NotificationType.PRODUCTION_BULK_RECORDED:
        count: int = int(kwargs.get("count", 0) or 0)
        total_volume_l: str | float | int = kwargs.get("total_volume_l", "0")
        shift: str = kwargs.get("shift", "AM")
        d = kwargs.get("date_time")
        title_date = format_day_date(d)
        actor: str | None = _short_label(kwargs.get("actor_label"))
        title = f"🥛📦 Registro masivo completado - {title_date} {shift}"
        message = f"Se registraron {count} animales con {_fmt(total_volume_l)}L totales"
        if actor:
            message += f" • por {actor}"
        data = {
            "count": int(count),
            "total_volume_l": str(total_volume_l),
            "shift": shift,
            "date": str(d) if d is not None else None,
            "actor": actor,
        }
        return BuiltNotification(ntype, title, message, data)

    if ntype == NotificationType.ANIMAL_CREATED:
        tag: str = kwargs.get("tag", "Animal")
        name: str | None = kwargs.get("name")
        actor: str | None = _short_label(kwargs.get("actor_label"))
        title = "🐄 Nueva vaca registrada"
        message = f"Se creó la vaca {tag}" + (f" {name}" if name else "")
        if actor:
            message += f" • por {actor}"
        data = {
            "animal_id": str(kwargs.get("animal_id")) if kwargs.get("animal_id") else None,
            "tag": tag,
            "name": name,
            "actor": actor,
        }
        return BuiltNotification(ntype, title, message, data)

    if ntype == NotificationType.ANIMAL_UPDATED:
        tag: str = kwargs.get("tag", "Animal")
        name: str | None = kwargs.get("name")
        changed_fields = kwargs.get("changed_fields") or []
        actor: str | None = _short_label(kwargs.get("actor_label"))
        title = "🔄🐄 Vaca actualizada"
        message = f"Se actualizó la vaca {tag}" + (f" {name}" if name else "")
        if actor:
            message += f" • por {actor}"
        data = {
            "animal_id": str(kwargs.get("animal_id")) if kwargs.get("animal_id") else None,
            "tag": tag,
            "name": name,
            "changed_fields": changed_fields,
            "actor": actor,
        }
        return BuiltNotification(ntype, title, message, data)

    if ntype == NotificationType.ANIMAL_EVENT_CREATED:
        tag: str = kwargs.get("tag", "Animal")
        name: str | None = kwargs.get("name")
        event_name: str = kwargs.get("event_name", "Evento")
        category: str = kwargs.get("category", "Evento")
        date_str: str | None = kwargs.get("date")
        actor: str | None = _short_label(kwargs.get("actor_label"))
        cat_lower = category.lower()
        if any(x in cat_lower for x in ["birth", "nacimiento", "calf", "parto"]):
            icon = "🐣"
        elif any(
            x in cat_lower
            for x in ["health", "salud", "sick", "enfermo", "vacuna", "medication", "treatment"]
        ):
            icon = "🩺"
        elif any(
            x in cat_lower
            for x in ["breeding", "insemin", "servicio", "mating", "gest", "gestation"]
        ):
            icon = "❤️"
        else:
            icon = "🐾"
        title = f"{icon} Evento de vaca: {category}"
        message = f"{category}: {event_name} para {tag}" + (f" {name}" if name else "")
        if date_str:
            message += f" • {date_str}"
        if actor:
            message += f" • por {actor}"
        data = {
            "animal_id": str(kwargs.get("animal_id")) if kwargs.get("animal_id") else None,
            "event_id": str(kwargs.get("event_id")) if kwargs.get("event_id") else None,
            "category": category,
            "event_name": event_name,
            "date": date_str,
            "tag": tag,
            "name": name,
            "actor": actor,
        }
        return BuiltNotification(ntype, title, message, data)

    # Fallback to pass-through
    return BuiltNotification(
        ntype,
        title=str(kwargs.get("title", "Notificación")),
        message=str(kwargs.get("message", "")),
        data=dict(kwargs.get("data", {})),
    )
