from __future__ import annotations

from datetime import datetime, timezone
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

