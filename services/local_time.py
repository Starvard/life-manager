"""Local time helpers.

The app doesn't care about precise wall-clock timestamps; it does care about
what calendar day it is in the user's own timezone. On Fly.io the container
has no ``TZ`` set and falls back to UTC, which meant the app thought it was
Monday from 8 PM EST on Sunday onward — rolling the week over early, firing
reminders at the wrong local hour, and mis-coloring overdue dots.

This module centralizes "what day is it for the user?" so we can set a
single env var (``LM_TIMEZONE``) and fix all of those in one place.
"""

from __future__ import annotations

import os
from datetime import date, datetime, time as time_cls, timezone
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # type: ignore


_DEFAULT_TZ_NAME = "UTC"


def _tz_name() -> str:
    raw = (os.environ.get("LM_TIMEZONE") or os.environ.get("TZ") or "").strip()
    return raw or _DEFAULT_TZ_NAME


def local_tz():
    """Return the user's configured tz (zoneinfo) or None if unavailable."""
    if ZoneInfo is None:
        return None
    name = _tz_name()
    try:
        return ZoneInfo(name)
    except Exception:
        try:
            return ZoneInfo(_DEFAULT_TZ_NAME)
        except Exception:
            return None


def local_now() -> datetime:
    """A timezone-aware ``datetime`` in the user's local timezone."""
    tz = local_tz()
    if tz is None:
        return datetime.now(timezone.utc)
    return datetime.now(tz)


def local_today() -> date:
    """What calendar day it is for the user right now."""
    return local_now().date()


def local_time_of_day() -> time_cls:
    """Wall-clock time for the user right now (naive ``time`` for comparison)."""
    n = local_now()
    return time_cls(n.hour, n.minute, n.second, n.microsecond)


__all__ = [
    "local_now",
    "local_today",
    "local_time_of_day",
    "local_tz",
]
