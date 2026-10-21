"""Pure validation rules for dining-context schedules and meal-window keys.

Conventions
-----------
- Local times are ``HH:MM`` on a 24-hour clock (00:00–23:59).
- ``active_days`` uses Python's ``date.weekday()`` numbering: 0=Mon … 6=Sun.
- A window must end strictly after it starts on the same local day.  Overnight
  windows (end <= start) are rejected; see DECISIONS.md D016.
- A meal-window key is ``YYYY-MM-DD#meal_type`` where the date is the local
  calendar date in the context's IANA time zone.

Every function raises ``ValueError`` with a human-readable message on failure
so it can be used from Pydantic validators and from application services.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import date
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MEAL_TYPES = ("lunch", "dinner", "brunch")

_HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_WINDOW_KEY = re.compile(r"^(\d{4}-\d{2}-\d{2})#([a-z]+)$")


def parse_local_time(value: str) -> int:
    """Return minutes after local midnight for a strict ``HH:MM`` value."""
    match = _HHMM.fullmatch(value)
    if match is None:
        raise ValueError(f"{value!r} is not a valid 24-hour HH:MM time")
    return int(match.group(1)) * 60 + int(match.group(2))


@lru_cache(maxsize=512)
def _load_zone(key: str) -> ZoneInfo:
    return ZoneInfo(key)


def validate_time_zone(value: str) -> str:
    """Return ``value`` if it names a loadable IANA time zone."""
    if not value or value != value.strip():
        raise ValueError(f"{value!r} is not a valid IANA time zone")
    try:
        _load_zone(value)
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        raise ValueError(f"{value!r} is not a valid IANA time zone") from exc
    return value


def validate_active_days(days: Sequence[int]) -> list[int]:
    """Require a non-empty list of unique weekday integers 0–6."""
    if not days:
        raise ValueError("active_days must contain at least one day")
    for day in days:
        # bool is an int subclass; reject it explicitly.
        if isinstance(day, bool) or not isinstance(day, int) or not 0 <= day <= 6:
            raise ValueError(f"active_days entries must be integers 0-6 (0=Mon), got {day!r}")
    if len(set(days)) != len(days):
        raise ValueError("active_days must not contain duplicates")
    return list(days)


def validate_window(start: str, end: str) -> None:
    """Require a same-day window whose end is strictly after its start."""
    start_min = parse_local_time(start)
    end_min = parse_local_time(end)
    if end_min <= start_min:
        raise ValueError(
            f"local_window_end {end!r} must be after local_window_start {start!r}; "
            "overnight windows are not supported"
        )


def parse_meal_window_key(key: str) -> tuple[date, str]:
    """Split ``YYYY-MM-DD#meal_type`` into a real calendar date and a meal type."""
    match = _WINDOW_KEY.fullmatch(key)
    if match is None:
        raise ValueError(f"{key!r} is not of the form YYYY-MM-DD#meal_type")
    try:
        local_date = date.fromisoformat(match.group(1))
    except ValueError as exc:
        raise ValueError(f"{match.group(1)!r} is not a real calendar date") from exc
    meal_type = match.group(2)
    if meal_type not in MEAL_TYPES:
        raise ValueError(f"{meal_type!r} is not a supported meal type")
    return local_date, meal_type


def check_meal_window_key(
    key: str,
    *,
    meal_type: str,
    active_days: Sequence[int],
    time_zone: str,
    local_window_start: str,
    local_window_end: str,
) -> None:
    """Verify that a meal-window key is consistent with a dining context.

    Checks that the key's date is real, its meal type matches the context,
    its weekday is one of the context's active days, and that the context's
    own schedule (time zone and local window) is valid.  The last two guard
    against rows written before strict validation existed.
    """
    local_date, key_meal = parse_meal_window_key(key)
    if key_meal != meal_type:
        raise ValueError(f"meal type {key_meal!r} does not match the context's {meal_type!r}")
    if local_date.weekday() not in active_days:
        raise ValueError(f"{local_date.isoformat()} is not one of the context's active days")
    validate_time_zone(time_zone)
    validate_window(local_window_start, local_window_end)
