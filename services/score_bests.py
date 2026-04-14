"""
Persistent all-time bests for blended routine scores.

best_completed_week: only updated for ISO weeks that have fully ended (Mon–Sun in the past),
  so mid-week snapshots do not steal the record on thin evidence.

best_day: best calendar-day blended % seen so far (today or any past day in a loaded week).
"""

from __future__ import annotations

import json
import os
import threading
from datetime import date, timedelta

import config
from services.score_helpers import (
    daily_breakdown_weighted,
    weighted_week_score,
    week_scheduled_weight_total,
)

_lock = threading.Lock()

DEFAULT_STATE: dict = {
    "version": 1,
    "best_completed_week": None,
    "best_day": None,
}


def _load() -> dict:
    path = config.SCORE_BESTS_FILE
    if not os.path.isfile(path):
        return dict(DEFAULT_STATE)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return dict(DEFAULT_STATE)
        out = dict(DEFAULT_STATE)
        out.update(data)
        return out
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_STATE)


def _save(data: dict) -> None:
    path = config.SCORE_BESTS_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _week_sunday(week_start_iso: str) -> date:
    mon = date.fromisoformat(week_start_iso[:10])
    return mon + timedelta(days=6)


def _week_fully_in_past(week_start_iso: str, today: date) -> bool:
    return today > _week_sunday(week_start_iso)


def update_and_return_bests(week_key: str, cards: dict) -> dict:
    """
    Merge scores from this week into bests; return merged dict for templates.
    Thread-safe; cheap when cards empty.
    """
    if not cards:
        return _load()

    week_start = next((c.get("week_start") for c in cards.values() if c.get("week_start")), None)
    if not week_start:
        return _load()

    _, _, week_pct = weighted_week_score(cards)
    daily_row = daily_breakdown_weighted(cards)
    sched_w = week_scheduled_weight_total(cards)
    today = date.today()

    with _lock:
        data = _load()

        if (
            week_pct is not None
            and sched_w >= 12.0
            and _week_fully_in_past(week_start, today)
        ):
            cur = data.get("best_completed_week")
            if cur is None or week_pct > int(cur.get("pct", -1)):
                data["best_completed_week"] = {
                    "pct": week_pct,
                    "week_key": week_key,
                    "week_start": week_start[:10],
                }

        mon = date.fromisoformat(week_start[:10])
        best_day = data.get("best_day")
        best_pct = int(best_day["pct"]) if best_day else -1

        for i in range(7):
            d = mon + timedelta(days=i)
            if d > today:
                continue
            pct = daily_row[i]
            if pct is None:
                continue
            if pct > best_pct:
                best_pct = pct
                data["best_day"] = {
                    "pct": pct,
                    "date": d.isoformat(),
                    "week_key": week_key,
                }

        _save(data)
        return data


def load_bests_for_template() -> dict:
    """Read-only (no merge), for pages that do not have cards in memory."""
    return _load()
