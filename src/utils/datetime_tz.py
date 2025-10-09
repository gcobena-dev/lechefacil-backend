from __future__ import annotations

from datetime import date, datetime, time, timezone

from zoneinfo import ZoneInfo

# Default application timezone aligned with frontend
DEFAULT_TIMEZONE_NAME = "America/Guayaquil"
DEFAULT_TZ = ZoneInfo(DEFAULT_TIMEZONE_NAME)


def assume_local_tz(dt: datetime) -> datetime:
    """Assume the given naive datetime is in DEFAULT_TZ.

    If `dt` is naive, attach DEFAULT_TZ without shifting time.
    If `dt` is aware, return as-is.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=DEFAULT_TZ)
    return dt


def to_utc(dt: datetime) -> datetime:
    """Convert a datetime to UTC, assuming DEFAULT_TZ for naive values."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=DEFAULT_TZ)
    return dt.astimezone(timezone.utc)


_DOW_ES = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
_MON_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def format_day_date(
    d: date | datetime | str | None,
    *,
    include_time: bool = False,
    t: time | None = None,
    tz: ZoneInfo | None = DEFAULT_TZ,
) -> str:
    """Return 'vie 05/oct' or with time 'vie 05/oct hh:mm' (es-ES style).

    Accepts ISO date/datetime strings (with optional trailing 'Z').
    Normalizes to `tz` (assumes UTC if aware missing).
    """
    if d is None:
        return ""
    if isinstance(d, str):
        s = d.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except Exception:
            try:
                only_date = date.fromisoformat(s)
                dt = datetime.combine(only_date, time(0, 0))
            except Exception:
                return str(d)
    elif isinstance(d, datetime):
        dt = d
    else:
        dt = datetime.combine(d, time(0, 0))

    if tz is not None:
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(tz)

    dow = _DOW_ES[dt.weekday()]
    mon = _MON_ES[dt.month - 1]
    day_str = f"{dt.day:02d}/{mon}"
    if include_time:
        hhmm = t.strftime("%H:%M") if t else dt.strftime("%H:%M")
        return f"{dow} {day_str} {hhmm}"
    return f"{dow} {day_str}"
