"""One-time repair for daily routine definitions and generated cards.

Production keeps the editable routines.yaml and generated routine cards on a
persistent volume. If the inline routine editor or a bad deploy scrambled daily
habit names/order, updating the bundled repo YAML is not enough. This repair
restores daily tasks from the bundled baseline and rewrites generated cards from
May 11, 2026 forward while preserving checked dots where possible.
"""

from __future__ import annotations

import copy
import json
import os
from datetime import date

import yaml

import config

MIGRATION = "restore_daily_tasks_from_bundled_2026_05_10_v2"
CUTOFF = date(2026, 5, 11)


def _weekly_freq(task: dict) -> float:
    try:
        if "freq" in task:
            return float(task.get("freq") or 0)
        if "freq_per_year" in task:
            return float(task.get("freq_per_year") or 0) / 52.0
    except (TypeError, ValueError):
        return 0.0
    return 0.0


def _is_daily(task: dict) -> bool:
    return _weekly_freq(task) >= 7.0


def _load_bundled() -> dict:
    if not os.path.exists(config.ROUTINES_BUNDLED_FILE):
        return {"areas": {}}
    with open(config.ROUTINES_BUNDLED_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"areas": {}}


def _daily_schedule(freq: float) -> list[int]:
    base = int(freq // 7)
    extra = round(freq - base * 7)
    dots = [base] * 7
    if extra > 0:
        step = 7 / extra
        for i in range(extra):
            idx = int(round(i * step)) % 7
            dots[idx] += 1
    return dots


def _rebuild_days(old_days, schedule: list[int]) -> list[list[bool]]:
    old_days = old_days or []
    out: list[list[bool]] = []
    for d in range(7):
        old_row = old_days[d] if d < len(old_days) and isinstance(old_days[d], list) else []
        fills = [bool(v) for v in old_row if v]
        n = max(int(schedule[d] if d < len(schedule) else 0), 1, len(fills))
        row = [False] * n
        for i in range(min(len(fills), n)):
            row[i] = True
        out.append(row)
    return out


def _restore_config_daily_tasks(data: dict, bundled: dict) -> bool:
    changed = False
    areas = data.setdefault("areas", {})
    for area_key, bundled_area in (bundled.get("areas") or {}).items():
        canonical_tasks = [t for t in bundled_area.get("tasks", []) if isinstance(t, dict)]
        canonical_daily = [t for t in canonical_tasks if _is_daily(t)]
        if not canonical_daily:
            continue

        area = areas.setdefault(area_key, {"name": bundled_area.get("name", area_key), "tasks": []})
        area.setdefault("name", bundled_area.get("name", area_key))
        current = [t for t in area.get("tasks", []) if isinstance(t, dict)]
        current_non_daily = {
            str(t.get("name", "")).strip().lower(): t
            for t in current
            if not _is_daily(t)
        }
        used: set[str] = set()
        rebuilt: list[dict] = []

        for base_task in canonical_tasks:
            name_key = str(base_task.get("name", "")).strip().lower()
            if _is_daily(base_task):
                rebuilt.append(copy.deepcopy(base_task))
                continue
            live_task = current_non_daily.get(name_key)
            if live_task is not None:
                rebuilt.append(live_task)
                used.add(name_key)

        for task in current:
            name_key = str(task.get("name", "")).strip().lower()
            if _is_daily(task) or name_key in used:
                continue
            rebuilt.append(task)

        if rebuilt != current:
            area["tasks"] = rebuilt
            changed = True
    return changed


def _canonical_daily_by_area(bundled: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for area_key, area in (bundled.get("areas") or {}).items():
        daily = [copy.deepcopy(t) for t in area.get("tasks", []) if isinstance(t, dict) and _is_daily(t)]
        if daily:
            out[area_key] = daily
    return out


def _week_monday(week_name: str) -> date | None:
    if week_name.count("-W") != 1:
        return None
    try:
        year, week = week_name.split("-W")
        return date.fromisocalendar(int(year), int(week), 1)
    except (TypeError, ValueError):
        return None


def _repair_generated_cards(bundled: dict) -> bool:
    base = config.ROUTINE_CARDS_DIR
    if not os.path.isdir(base):
        return False
    canonical = _canonical_daily_by_area(bundled)
    changed_any = False

    for week_name in os.listdir(base):
        monday = _week_monday(week_name)
        if monday is None or monday < CUTOFF:
            continue
        week_dir = os.path.join(base, week_name)
        if not os.path.isdir(week_dir):
            continue

        for area_key, daily_tasks in canonical.items():
            path = os.path.join(week_dir, f"{area_key}.json")
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    card = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue

            tasks = [t for t in card.get("tasks", []) if isinstance(t, dict)]
            old_daily = [t for t in tasks if _is_daily(t)]
            old_daily_by_name = {str(t.get("name", "")).strip().lower(): t for t in old_daily}
            non_daily = [t for t in tasks if not _is_daily(t)]
            rebuilt_daily: list[dict] = []

            for idx, base_task in enumerate(daily_tasks):
                key = str(base_task.get("name", "")).strip().lower()
                source = old_daily_by_name.get(key)
                if source is None and idx < len(old_daily):
                    source = old_daily[idx]
                freq = _weekly_freq(base_task)
                scheduled = _daily_schedule(freq)
                rebuilt = {
                    "name": base_task.get("name"),
                    "freq": freq,
                    "weight": base_task.get("weight", 1.0),
                    "scheduled": scheduled,
                    "days": _rebuild_days((source or {}).get("days"), scheduled),
                }
                for meta_key in ("prev_week_overdue_streak", "prev_week_unmet_scheduled"):
                    if source and meta_key in source:
                        rebuilt[meta_key] = source[meta_key]
                rebuilt_daily.append(rebuilt)

            new_tasks = rebuilt_daily + non_daily
            if new_tasks == tasks:
                continue
            card["tasks"] = new_tasks
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(card, f, indent=2)
                changed_any = True
            except OSError:
                continue

    return changed_any


def restore_may10_daily_routines(data: dict) -> bool:
    migrations = data.setdefault("_migrations", [])
    if MIGRATION in migrations:
        return False

    bundled = _load_bundled()
    changed = False
    if _restore_config_daily_tasks(data, bundled):
        changed = True
    if _repair_generated_cards(bundled):
        changed = True

    migrations.append(MIGRATION)
    return True or changed
