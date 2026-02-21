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
        d = kwargs.get("date")
        event_data: dict = kwargs.get("event_data") or {}
        actor: str | None = _short_label(kwargs.get("actor_label"))
        cat_lower = category.lower()

        # Map event types to icons and Spanish labels
        event_config = {
            "birth": ("🐣", "Nacimiento"),
            "calving": ("🐄", "Parto"),
            "service": ("❤️", "Servicio"),
            "embryo_transfer": ("🧬", "Transferencia de embrión"),
            "dry_off": ("🥛", "Secado"),
            "sale": ("💰", "Venta"),
            "death": ("⚫", "Muerte"),
            "cull": ("📤", "Descarte"),
            "abortion": ("⚠️", "Aborto"),
            "transfer": ("🔄", "Traslado"),
        }

        icon, label = event_config.get(cat_lower, (None, None))
        if not icon:
            # Fallback for legacy/custom types
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
        if not label:
            label = category

        # Format date nicely
        date_str = format_day_date(d, include_time=True) if d else None

        # Build animal description for title (shorter) and message
        animal_short = f"{tag}" + (f" {name}" if name else "")

        if cat_lower == "service":
            # Service: "❤️ Servicio a 010 Vaca Nombre"
            title = f"{icon} {label} a {animal_short}"
            method = event_data.get("method")
            technician = event_data.get("technician")
            external_sire_code = event_data.get("external_sire_code")
            sire_name = event_data.get("sire_name")

            method_labels = {"AI": "IA", "NATURAL": "Monta natural", "ET": "TE"}
            method_label = method_labels.get(method, method) if method else None

            parts = []
            if method_label:
                parts.append(f"Método: {method_label}")
            if sire_name:
                parts.append(f"Toro: {sire_name}")
            elif external_sire_code:
                parts.append(f"Toro: {external_sire_code}")
            if technician:
                parts.append(f"Técnico: {technician}")
            if date_str:
                parts.append(date_str)
            if actor:
                parts.append(f"por {actor}")
            message = " • ".join(parts) if parts else f"{date_str or ''}"
        elif cat_lower == "calving":
            # Calving: "🐄 Parto de 010 Vaca Nombre"
            title = f"{icon} {label} de {animal_short}"
            parts = []
            if date_str:
                parts.append(date_str)
            if actor:
                parts.append(f"por {actor}")
            message = " • ".join(parts) if parts else "Parto registrado"
        elif cat_lower == "birth":
            # Birth: "🐣 Nacimiento: cría 011 de 010 Vaca"
            calf_tag = event_data.get("calf_tag")
            calf_sex = event_data.get("calf_sex")
            calf_name = event_data.get("calf_name")
            sex_label = {"MALE": "macho", "FEMALE": "hembra"}.get(calf_sex, "")
            calf_desc = calf_tag or "nueva cría"
            if calf_name:
                calf_desc += f" {calf_name}"
            title = f"{icon} {label}: {calf_desc} de {animal_short}"
            parts = []
            if sex_label:
                parts.append(sex_label.capitalize())
            if date_str:
                parts.append(date_str)
            if actor:
                parts.append(f"por {actor}")
            message = " • ".join(parts) if parts else "Nacimiento registrado"
        elif cat_lower == "dry_off":
            # Dry off: "🥛 Secado de 010 Vaca Nombre"
            title = f"{icon} {label} de {animal_short}"
            parts = []
            if date_str:
                parts.append(date_str)
            if actor:
                parts.append(f"por {actor}")
            message = " • ".join(parts) if parts else "Secado registrado"
        elif cat_lower == "sale":
            # Sale: "💰 Venta de 010 Vaca Nombre"
            title = f"{icon} {label} de {animal_short}"
            reason = event_data.get("reason")
            buyer = event_data.get("buyer")
            price = event_data.get("price")
            parts = []
            if buyer:
                parts.append(f"Comprador: {buyer}")
            if price:
                parts.append(f"Precio: {price}")
            if reason:
                parts.append(reason)
            if date_str:
                parts.append(date_str)
            if actor:
                parts.append(f"por {actor}")
            message = " • ".join(parts) if parts else "Venta registrada"
        elif cat_lower == "death":
            # Death: "⚫ Muerte de 010 Vaca Nombre"
            title = f"{icon} {label} de {animal_short}"
            cause = event_data.get("cause")
            parts = []
            if cause:
                parts.append(f"Causa: {cause}")
            if date_str:
                parts.append(date_str)
            if actor:
                parts.append(f"por {actor}")
            message = " • ".join(parts) if parts else "Muerte registrada"
        elif cat_lower == "cull":
            # Cull: "📤 Descarte de 010 Vaca Nombre"
            title = f"{icon} {label} de {animal_short}"
            reason = event_data.get("reason")
            parts = []
            if reason:
                parts.append(f"Razón: {reason}")
            if date_str:
                parts.append(date_str)
            if actor:
                parts.append(f"por {actor}")
            message = " • ".join(parts) if parts else "Descarte registrado"
        elif cat_lower == "abortion":
            # Abortion: "⚠️ Aborto de 010 Vaca Nombre"
            title = f"{icon} {label} de {animal_short}"
            cause = event_data.get("cause")
            gestation_days = event_data.get("gestation_days")
            parts = []
            if gestation_days:
                parts.append(f"{gestation_days} días de gestación")
            if cause:
                parts.append(f"Causa: {cause}")
            if date_str:
                parts.append(date_str)
            if actor:
                parts.append(f"por {actor}")
            message = " • ".join(parts) if parts else "Aborto registrado"
        elif cat_lower == "transfer":
            # Transfer: "🔄 Traslado de 010 Vaca Nombre"
            title = f"{icon} {label} de {animal_short}"
            from_lot = event_data.get("from_lot")
            to_lot = event_data.get("to_lot")
            parts = []
            if from_lot and to_lot:
                parts.append(f"De {from_lot} a {to_lot}")
            elif to_lot:
                parts.append(f"A {to_lot}")
            if date_str:
                parts.append(date_str)
            if actor:
                parts.append(f"por {actor}")
            message = " • ".join(parts) if parts else "Traslado registrado"
        elif cat_lower == "embryo_transfer":
            # Embryo transfer: "🧬 Transferencia de embrión a 010 Vaca"
            title = f"{icon} {label} a {animal_short}"
            embryo_code = event_data.get("embryo_code")
            parts = []
            if embryo_code:
                parts.append(f"Embrión: {embryo_code}")
            if date_str:
                parts.append(date_str)
            if actor:
                parts.append(f"por {actor}")
            message = " • ".join(parts) if parts else "Transferencia registrada"
        else:
            # Generic event: "🐾 Evento para 010 Vaca Nombre"
            title = f"{icon} {label} para {animal_short}"
            parts = []
            if date_str:
                parts.append(date_str)
            if actor:
                parts.append(f"por {actor}")
            message = " • ".join(parts) if parts else f"{label} registrado"

        data = {
            "animal_id": str(kwargs.get("animal_id")) if kwargs.get("animal_id") else None,
            "event_id": str(kwargs.get("event_id")) if kwargs.get("event_id") else None,
            "category": category,
            "event_name": event_name,
            "date": str(d) if d else None,
            "tag": tag,
            "name": name,
            "actor": actor,
            "event_data": event_data,
        }
        return BuiltNotification(ntype, title, message, data)

    if ntype == NotificationType.PREGNANCY_CHECK_RECORDED:
        result: str = kwargs.get("result", "CONFIRMED")
        tag: str = kwargs.get("tag", "Animal")
        name: str | None = kwargs.get("name")
        checked_by: str | None = kwargs.get("checked_by")
        expected_calving_date = kwargs.get("expected_calving_date")
        actor: str | None = _short_label(kwargs.get("actor_label"))
        animal_short = f"{tag}" + (f" {name}" if name else "")

        if result == "CONFIRMED":
            title = f"\U0001f930 Preñez confirmada: {animal_short}"
            parts = []
            if expected_calving_date:
                parts.append(f"Parto esperado: {expected_calving_date}")
            if checked_by:
                parts.append(f"Verificado por: {checked_by}")
            if actor:
                parts.append(f"por {actor}")
            message = " • ".join(parts) if parts else "Preñez confirmada"
        elif result == "OPEN":
            title = f"\U0001f534 Vacía: {animal_short}"
            parts = ["Requiere re-servicio"]
            if checked_by:
                parts.append(f"Verificado por: {checked_by}")
            if actor:
                parts.append(f"por {actor}")
            message = " • ".join(parts)
        else:  # LOST
            title = f"\u26a0\ufe0f Pérdida gestacional: {animal_short}"
            parts = []
            if checked_by:
                parts.append(f"Verificado por: {checked_by}")
            if actor:
                parts.append(f"por {actor}")
            message = " • ".join(parts) if parts else "Pérdida gestacional registrada"

        data = {
            "insemination_id": str(kwargs.get("insemination_id"))
            if kwargs.get("insemination_id")
            else None,
            "animal_id": str(kwargs.get("animal_id")) if kwargs.get("animal_id") else None,
            "result": result,
            "tag": tag,
            "name": name,
            "checked_by": checked_by,
            "expected_calving_date": str(expected_calving_date) if expected_calving_date else None,
            "actor": actor,
        }
        return BuiltNotification(ntype, title, message, data)

    if ntype == NotificationType.SEMEN_STOCK_LOW:
        sire_name: str = kwargs.get("sire_name", "Toro")
        quantity: int = int(kwargs.get("current_quantity", 0) or 0)
        batch_code: str | None = kwargs.get("batch_code")
        title = "\U0001f9ca Stock de semen bajo"
        message = f"Toro: {sire_name} — quedan {quantity} pajillas"
        if batch_code:
            message += f" (lote {batch_code})"
        data = {
            "sire_catalog_id": str(kwargs.get("sire_catalog_id"))
            if kwargs.get("sire_catalog_id")
            else None,
            "sire_name": sire_name,
            "current_quantity": quantity,
            "batch_code": batch_code,
        }
        return BuiltNotification(ntype, title, message, data)

    if ntype == NotificationType.PREGNANCY_CHECK_DUE:
        count: int = int(kwargs.get("count", 0) or 0)
        title = "\U0001f4cb Chequeos de preñez pendientes"
        message = f"{count} animales entre 35-50 días post-servicio"
        data = {"count": count}
        return BuiltNotification(ntype, title, message, data)

    if ntype == NotificationType.CALVING_EXPECTED_SOON:
        count: int = int(kwargs.get("count", 0) or 0)
        days: int = int(kwargs.get("days", 7) or 7)
        title = "\U0001f404 Partos próximos"
        message = f"{count} animales con parto esperado en los próximos {days} días"
        data = {"count": count, "days": days}
        return BuiltNotification(ntype, title, message, data)

    # Fallback to pass-through
    return BuiltNotification(
        ntype,
        title=str(kwargs.get("title", "Notificación")),
        message=str(kwargs.get("message", "")),
        data=dict(kwargs.get("data", {})),
    )
