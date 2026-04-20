"""
Reads, writes, and auto-generates routine and baby card JSON files.

Routine cards live at  data/routine-cards/<week_key>/<area_key>.json
Baby cards live at     data/baby-cards/<YYYY-MM-DD>.json

On first access for a given week/date the card is auto-generated from
the config files (routines.yaml / baby_config.yaml).
"""

import json
import os
import threading
from datetime import date, timedelta

import yaml

_file_locks: dict[str, threading.Lock] = {}
_locks_lock = threading.Lock()


def _get_lock(path: str) -> threading.Lock:
    with _locks_lock:
        if path not in _file_locks:
            _file_locks[path] = threading.Lock()
        return _file_locks[path]


# Cache for `_collect_last_completed_before_week`. Recomputing this scans
# every prior week's JSON, and on a dashboard render with N areas it was
# previously called N+1 times. The cache is keyed by `before_week_key` and
# the directory mtime so it auto-invalidates when any week file changes.
_last_completed_cache_lock = threading.Lock()
_last_completed_cache: dict[str, tuple[float | None, dict]] = {}


import config
from services.local_time import local_today
from services.routine_manager import load_routines
from services.week_planner import (
    plan_week,
    iso_week_key,
    week_start_date,
    LastCompletedMap,
)


def _monday_from_week_key(week_key: str) -> date | None:
    parts = week_key.split("-W")
    if len(parts) != 2:
        return None
    try:
        y, wn = int(parts[0]), int(parts[1])
        return date.fromisocalendar(y, wn, 1)
    except ValueError:
        return None


def _merge_last_completed_from_this_card(
    card: dict,
    week_key: str,
    acc: LastCompletedMap,
    as_of: date,
) -> None:
    """Update acc with latest completion date per task from this card up to as_of."""
    monday = _monday_from_week_key(week_key)
    if monday is None:
        return
    area_key = card.get("area_key")
    if not area_key:
        return
    for task in card.get("tasks", []):
        tname = task.get("name")
        if not tname:
            continue
        sched = _sched_seven(task.get("scheduled"))
        days = task.get("days") or []
        for di in range(min(7, len(days))):
            day_date = monday + timedelta(days=di)
            if day_date > as_of:
                continue
            nsched = sched[di] if di < len(sched) else 0
            row = days[di] if di < len(days) else []
            for doi in range(min(nsched, len(row))):
                if row[doi]:
                    key = (area_key, tname)
                    prev = acc.get(key)
                    acc[key] = day_date if prev is None else max(prev, day_date)


def _collect_last_completed_before_week(
    before_week_key: str,
) -> LastCompletedMap:
    """
    For each (area_key, task_name), the latest calendar date on which any
    scheduled routine dot was completed in a week strictly before before_week_key.
    """
    cutoff = _monday_from_week_key(before_week_key)
    if cutoff is None:
        return {}
    base = config.ROUTINE_CARDS_DIR
    if not os.path.isdir(base):
        return {}

    try:
        dir_mtime = os.path.getmtime(base)
    except OSError:
        dir_mtime = None
    cache_key = before_week_key
    with _last_completed_cache_lock:
        cached = _last_completed_cache.get(cache_key)
        if cached is not None and cached[0] == dir_mtime:
            return cached[1]

    acc: LastCompletedMap = {}
    for wk_name in os.listdir(base):
        if wk_name.count("-W") != 1:
            continue
        wk_mon = _monday_from_week_key(wk_name)
        if wk_mon is None or wk_mon >= cutoff:
            continue
        wk_dir = os.path.join(base, wk_name)
        if not os.path.isdir(wk_dir):
            continue
        for fname in os.listdir(wk_dir):
            if not fname.endswith(".json"):
                continue
            area_key = fname[:-5]
            card = _load_json(os.path.join(wk_dir, fname))
            if not card:
                continue
            for task in card.get("tasks", []):
                tname = task.get("name")
                if not tname:
                    continue
                sched = _sched_seven(task.get("scheduled"))
                days = task.get("days") or []
                for di in range(min(7, len(days))):
                    nsched = sched[di] if di < len(sched) else 0
                    row = days[di] if di < len(days) else []
                    for doi in range(min(nsched, len(row))):
                        if row[doi]:
                            d = wk_mon + timedelta(days=di)
                            key = (area_key, tname)
                            prev = acc.get(key)
                            if prev is None or d > prev:
                                acc[key] = d

    with _last_completed_cache_lock:
        _last_completed_cache[cache_key] = (dir_mtime, acc)
    return acc


def _task_has_fixed_weekdays(area_key: str, task_name: str) -> bool:
    routines = load_routines()
    area = routines.get("areas", {}).get(area_key) or {}
    for t in area.get("tasks", []):
        if t.get("name") != task_name:
            continue
        od = t.get("on_days")
        if od is None:
            return False
        if isinstance(od, (list, tuple)) and len(od) == 0:
            return False
        return True
    return False


def _reconcile_sub_weekly_tasks_with_last_completion(
    card: dict, week_key: str
) -> bool:
    """For freq < 1 tasks, re-evaluate whether this week is still "due".

    Pre-generated weeks can hold a dot that was scheduled before the user
    completed the task in an earlier week. Example: Knife Sharpening
    (``freq_per_year: 4`` ≈ every 13 weeks) got dotted this week when it was
    last done a year ago, but the user just sharpened 2 weeks ago — the dot
    should disappear. Conversely, a previously not-due week should light up
    if the task's gap has elapsed. No fills are ever discarded: if the row
    has any ``True`` the current schedule is left alone.
    """
    area_key = card.get("area_key")
    if not area_key:
        return False
    parts = week_key.split("-W")
    if len(parts) != 2:
        return False
    y, wn = int(parts[0]), int(parts[1])
    target = date.fromisocalendar(y, wn, 1)

    last_map = dict(_collect_last_completed_before_week(week_key))
    _merge_last_completed_from_this_card(card, week_key, last_map, local_today())
    routines = load_routines()
    plans = plan_week(
        routines.get("areas", {}),
        target,
        last_completed=last_map or None,
        as_of_date=local_today(),
    )
    plan = next((p for p in plans if p["key"] == area_key), None)
    if not plan:
        return False
    canon = {t["name"]: t["dots"] for t in plan["tasks"]}

    changed = False
    for task in card.get("tasks", []):
        name = task.get("name")
        if name is None or name not in canon:
            continue
        f = float(task.get("freq") or 0)
        if f >= 1:
            continue
        existing_days = task.get("days") or []
        has_any_fill = any(
            any(bool(v) for v in (row or [])) for row in existing_days
        )
        if has_any_fill:
            continue
        target_sched = _sched_seven(canon[name])
        old_sched = _sched_seven(task.get("scheduled"))
        grid_ok = _days_grid_matches_sched(task, target_sched)
        if old_sched == target_sched and grid_ok:
            continue
        new_days = []
        for d in range(7):
            ns = target_sched[d]
            nlen = max(ns, 1)
            new_days.append([False] * nlen)
        task["scheduled"] = target_sched
        task["days"] = new_days
        changed = True
    return changed


def _reconcile_mid_frequency_tasks_with_last_completion(
    card: dict, week_key: str
) -> bool:
    """
    For 1 <= freq < 7 tasks without fixed on_days, re-sync scheduled[] to the
    planner when the global pattern should shift based on the last completion.
    """
    parts = week_key.split("-W")
    if len(parts) != 2:
        return False
    y, wn = int(parts[0]), int(parts[1])
    target = date.fromisocalendar(y, wn, 1)
    area_key = card.get("area_key")
    if not area_key:
        return False

    last_map = dict(_collect_last_completed_before_week(week_key))
    _merge_last_completed_from_this_card(card, week_key, last_map, local_today())
    routines = load_routines()
    plans = plan_week(
        routines.get("areas", {}),
        target,
        last_completed=last_map or None,
        as_of_date=local_today(),
    )
    plan = next((p for p in plans if p["key"] == area_key), None)
    if not plan:
        return False
    canon = {t["name"]: t["dots"] for t in plan["tasks"]}
    changed = False
    for task in card.get("tasks", []):
        name = task["name"]
        if name not in canon:
            continue
        f = float(task.get("freq") or 0)
        if not (1 <= f < 7):
            continue
        if _task_has_fixed_weekdays(area_key, name):
            continue
        if task.get("carryover") or task.get("carryover_week_key"):
            continue
        target_sched = _sched_seven(canon[name])
        old_sched = _sched_seven(task.get("scheduled"))
        grid_ok = _days_grid_matches_sched(task, target_sched)
        if old_sched == target_sched and grid_ok:
            continue
        task["scheduled"] = target_sched
        task["days"] = _rebuild_days_preserving_fills(
            task.get("days") or [], target_sched
        )
        changed = True
    return changed


def _prev_week_key(week_key: str) -> str:
    parts = week_key.split("-W")
    if len(parts) != 2:
        return ""
    y, wn = int(parts[0]), int(parts[1])
    monday = date.fromisocalendar(y, wn, 1)
    return iso_week_key(monday - timedelta(days=7))


def _load_card_file(week_key: str, area_key: str) -> dict | None:
    path = _routine_path(week_key, area_key)
    if not os.path.isfile(path):
        return None
    return _load_json(path)


def _prev_week_unmet_scheduled_count(prev_card: dict, task_name: str) -> int:
    """How many scheduled dots from last week were left unchecked for this task."""
    for t in prev_card.get("tasks", []):
        if t.get("name") != task_name:
            continue
        sched = t.get("scheduled") or [0] * 7
        days = t.get("days") or []
        unmet = 0
        n_sched = 0
        n_fill = 0
        for di in range(min(7, len(sched))):
            try:
                n_sched += max(0, int(sched[di]))
            except (TypeError, ValueError):
                pass
        for di in range(min(7, len(days))):
            row = days[di] or []
            for cell in row:
                if cell:
                    n_fill += 1
        pool = min(n_sched, n_fill)
        if pool >= n_sched:
            return 0
        return n_sched - pool
    return 0


def _prev_week_last_unmet_day_streak(prev_card: dict, task_name: str) -> int:
    """How many trailing days of last week ended with an unmet scheduled dot.

    Walks Sunday → back through Monday counting consecutive days that had at
    least one unmet scheduled slot; used to seed the overdue streak into the
    new week so Monday inherits the color instead of resetting to plain.
    """
    for t in prev_card.get("tasks", []):
        if t.get("name") != task_name:
            continue
        sched = list(t.get("scheduled") or [0] * 7)
        days = t.get("days") or []
        n_sched = 0
        n_fill = 0
        for di in range(min(7, len(sched))):
            try:
                n_sched += max(0, int(sched[di]))
            except (TypeError, ValueError):
                pass
        for di in range(min(7, len(days))):
            row = days[di] or []
            for cell in row:
                if cell:
                    n_fill += 1
        pool = min(n_sched, n_fill)
        k = 0
        streak = 0
        fills_left = pool
        unmet_from_end: list[bool] = []
        for di in range(min(7, len(sched))):
            try:
                sc = max(0, int(sched[di]))
            except (TypeError, ValueError):
                sc = 0
            row = days[di] if di < len(days) else []
            for doi in range(sc):
                slot_k = k
                k += 1
                if slot_k < pool:
                    unmet_from_end.append(False)
                else:
                    unmet_from_end.append(not (doi < len(row) and row[doi]))
        if not unmet_from_end:
            return 0
        day_sched_counts: list[int] = []
        for di in range(min(7, len(sched))):
            try:
                day_sched_counts.append(max(0, int(sched[di])))
            except (TypeError, ValueError):
                day_sched_counts.append(0)
        while len(day_sched_counts) < 7:
            day_sched_counts.append(0)
        per_day_unmet: list[bool] = [False] * 7
        idx = 0
        for di in range(7):
            sc = day_sched_counts[di]
            any_unmet = False
            for _ in range(sc):
                if idx < len(unmet_from_end) and unmet_from_end[idx]:
                    any_unmet = True
                idx += 1
            per_day_unmet[di] = any_unmet
        streak = 0
        for di in range(6, -1, -1):
            if day_sched_counts[di] == 0:
                continue
            if per_day_unmet[di]:
                streak += 1
                continue
            break
        return streak
    return 0


def _attach_prev_week_carry_state(card: dict, prev_card: dict | None) -> None:
    """Annotate tasks with how much overdue streak they inherit from last week.

    The UI (``dotClass``) uses this to keep the Sunday-was-orange color
    visible on Monday's first scheduled dot instead of treating the new week
    like a fresh start. No extra scheduled Monday dot is added.
    """
    if not prev_card:
        return
    for task in card.get("tasks", []):
        name = task.get("name")
        streak = _prev_week_last_unmet_day_streak(prev_card, name)
        unmet = _prev_week_unmet_scheduled_count(prev_card, name)
        task["prev_week_overdue_streak"] = streak
        task["prev_week_unmet_scheduled"] = unmet


def _strip_legacy_carryover(card: dict) -> bool:
    """Remove the old ad-hoc Monday carryover dot + metadata.

    We no longer add an extra Monday scheduled slot when last week had
    unfinished work; the overdue-streak carryover handles cohesion visually.
    Existing cards that still carry ``carryover`` / ``carryover_week_key``
    get cleaned up on load.
    """
    changed = False
    for task in card.get("tasks", []):
        if task.get("carryover"):
            task.pop("carryover", None)
            changed = True
        if task.get("carryover_week_key"):
            task.pop("carryover_week_key", None)
            changed = True
    return changed


def _task_is_high_frequency(freq: float) -> bool:
    """Daily / multi-day habits: never keep ad-hoc carryover bumps in saved JSON."""
    return freq >= 7 or freq > 2


def _sched_seven(sched) -> list[int]:
    s = list(sched or [])
    while len(s) < 7:
        s.append(0)
    return s[:7]


def _days_grid_matches_sched(task: dict, target_sched: list[int]) -> bool:
    """True only if each day row length is max(scheduled[d], 1)."""
    days = task.get("days") or []
    for d in range(7):
        nlen = max(target_sched[d], 1)
        row = days[d] if d < len(days) else None
        if row is None or len(row) != nlen:
            return False
    return True


def _rebuild_days_preserving_fills(
    old_days: list,
    target_sched: list[int],
) -> list:
    """Rebuild the ``days`` grid around ``target_sched`` without losing fills.

    The previous rebuild code dropped ``True`` cells that used to sit in the
    bonus tail (``days[d]`` longer than ``scheduled[d]``). That cost users
    real completions whenever the planner shifted a task to a different day.
    This helper keeps every ``True`` cell: scheduled-slot fills are aligned
    Mon→Sun, then any remaining fills are appended as bonus slots per day.
    """
    old_days = old_days or []
    filled_per_day: list[int] = []
    for d in range(7):
        row = old_days[d] if d < len(old_days) else []
        filled_per_day.append(sum(1 for v in (row or []) if v))

    new_days: list[list[bool]] = []
    for d in range(7):
        ns = target_sched[d] if d < len(target_sched) else 0
        base = max(ns, 1)
        f = filled_per_day[d]
        total = max(base, f)
        row = [False] * total
        for i in range(min(ns, f)):
            row[i] = True
        for i in range(max(0, f - ns)):
            row[ns + i] = True
        new_days.append(row)
    return new_days


def _reconcile_pinned_day_tasks_with_routines(card: dict, week_key: str) -> bool:
    """Sync pinned-day tasks (routines.yaml ``on_days``) to the canonical pattern.

    When the user edits ``on_days`` on a task (e.g. "trash only on Tuesdays")
    we need any previously-saved week cards to update to the new pinning; the
    high- and mid-frequency reconcilers both skip ``on_days`` tasks by design,
    which is why "Take out Trash" could keep a stale Mon+Fri pattern forever.

    Also handles the inverse — a task that used to have ``on_days`` but no
    longer does. That case falls through to the normal mid-frequency pass.
    """
    area_key = card.get("area_key")
    if not area_key:
        return False
    routines = load_routines()
    area = routines.get("areas", {}).get(area_key) or {}
    by_name: dict[str, dict] = {}
    for raw in area.get("tasks", []) or []:
        n = raw.get("name")
        if n:
            by_name[n] = raw

    changed = False
    for task in card.get("tasks", []):
        name = task.get("name")
        raw = by_name.get(name)
        if raw is None:
            continue
        from services.week_planner import (
            _normalize_on_days,
            _dots_from_fixed_days,
            effective_weekly_freq,
        )
        on_days = _normalize_on_days(raw.get("on_days"))
        if not on_days:
            continue
        freq = effective_weekly_freq(raw)
        n_dots = max(1, round(freq)) if freq >= 1 else 1
        target_sched = _sched_seven(_dots_from_fixed_days(n_dots, on_days))
        old_sched = _sched_seven(task.get("scheduled"))
        grid_ok = _days_grid_matches_sched(task, target_sched)
        if old_sched == target_sched and grid_ok:
            continue
        task["scheduled"] = target_sched
        task["days"] = _rebuild_days_preserving_fills(
            task.get("days") or [], target_sched
        )
        changed = True
    return changed


def _reconcile_high_frequency_tasks_with_planner(card: dict, week_key: str) -> bool:
    """
    For tasks scheduled 3+ times/week or daily, force scheduled[] + days[] to match
    the current planner output and drop carryover metadata.

    Fixes stale JSON where carryover incorrectly added extra Monday (or other) dots
    before eligibility rules existed.
    """
    parts = week_key.split("-W")
    if len(parts) != 2:
        return False
    y, wn = int(parts[0]), int(parts[1])
    target = date.fromisocalendar(y, wn, 1)
    routines = load_routines()
    plans = plan_week(routines.get("areas", {}), target)
    area_key = card.get("area_key")
    plan = next((p for p in plans if p["key"] == area_key), None)
    if not plan:
        return False
    canon = {t["name"]: t["dots"] for t in plan["tasks"]}
    changed = False
    for task in card.get("tasks", []):
        name = task["name"]
        if name not in canon:
            continue
        f = float(task.get("freq") or 0)
        if not _task_is_high_frequency(f):
            continue
        target_sched = _sched_seven(canon[name])
        old_sched = _sched_seven(task.get("scheduled"))
        has_carry_meta = bool(task.get("carryover") or task.get("carryover_week_key"))
        grid_ok = _days_grid_matches_sched(task, target_sched)
        if old_sched == target_sched and not has_carry_meta and grid_ok:
            continue
        task["scheduled"] = target_sched
        task["days"] = _rebuild_days_preserving_fills(
            task.get("days") or [], target_sched
        )
        task.pop("carryover", None)
        task.pop("carryover_week_key", None)
        changed = True
    return changed


def _ensure_prev_week_overdue_streak(card: dict, week_key: str, area_key: str) -> bool:
    """Cache how many trailing days of last week ended unmet, per task.

    Also strips any legacy ``carryover`` / ``carryover_week_key`` fields and
    trims the old Monday bump out of ``scheduled`` so new-week JSON is clean.
    """
    prev_wk = _prev_week_key(week_key)
    prev_card = _load_card_file(prev_wk, area_key) if prev_wk else None
    changed = _strip_legacy_carryover(card)
    if prev_card:
        for task in card.get("tasks", []):
            name = task.get("name")
            new_streak = _prev_week_last_unmet_day_streak(prev_card, name)
            new_unmet = _prev_week_unmet_scheduled_count(prev_card, name)
            if task.get("prev_week_overdue_streak") != new_streak:
                task["prev_week_overdue_streak"] = new_streak
                changed = True
            if task.get("prev_week_unmet_scheduled") != new_unmet:
                task["prev_week_unmet_scheduled"] = new_unmet
                changed = True
    else:
        for task in card.get("tasks", []):
            if task.pop("prev_week_overdue_streak", None) is not None:
                changed = True
            if task.pop("prev_week_unmet_scheduled", None) is not None:
                changed = True
    return changed


def _blank_extra_task(name: str) -> dict:
    """One-off row: one optional dot per day (all unscheduled / manual)."""
    scheduled = [0] * 7
    days = [[False] for _ in range(7)]
    return {
        "name": name.strip(),
        "freq": 1,
        "weight": 1.0,
        "days": days,
        "scheduled": scheduled,
        "temporary": True,
    }


# ── Routine Cards ─────────────────────────────────────────────────

def _routine_dir(week_key: str) -> str:
    return os.path.join(config.ROUTINE_CARDS_DIR, week_key)


def _routine_path(week_key: str, area_key: str) -> str:
    return os.path.join(_routine_dir(week_key), f"{area_key}.json")


def _generate_routine_cards(week_key: str, target_date: date) -> dict[str, dict]:
    """Generate all area cards for a week from routines.yaml + planner."""
    routines = load_routines()
    last_map = _collect_last_completed_before_week(week_key)
    plans = plan_week(
        routines.get("areas", {}),
        target_date,
        last_completed=last_map or None,
        as_of_date=local_today(),
    )

    week_dir = _routine_dir(week_key)
    os.makedirs(week_dir, exist_ok=True)

    cards = {}
    for plan in plans:
        if not plan["tasks"]:
            continue
        card = {
            "week_key": plan["week_key"],
            "area_key": plan["key"],
            "area_name": plan["name"],
            "week_start": plan["week_start"],
            "tasks": [],
            "extra_tasks": [],
            "notes": "",
        }
        for task in plan["tasks"]:
            scheduled = task["dots"]
            days = []
            for d in range(7):
                dot_count = max(scheduled[d], 1)
                days.append([False] * dot_count)
            w = task.get("weight", 1.0)
            try:
                w = float(w)
                if w <= 0:
                    w = 1.0
            except (TypeError, ValueError):
                w = 1.0
            card["tasks"].append({
                "name": task["name"],
                "freq": task["freq"],
                "weight": w,
                "days": days,
                "scheduled": scheduled,
            })
        prev_wk = _prev_week_key(week_key)
        prev = _load_card_file(prev_wk, plan["key"]) if prev_wk else None
        _attach_prev_week_carry_state(card, prev)
        cards[plan["key"]] = card
        _save_json(_routine_path(week_key, plan["key"]), card)

    return cards


def get_routine_cards(week_key: str) -> dict[str, dict]:
    """Load all area cards for a week, auto-generating if needed."""
    week_dir = _routine_dir(week_key)
    if not os.path.isdir(week_dir):
        parts = week_key.split("-W")
        if len(parts) == 2:
            year = int(parts[0])
            week_num = int(parts[1])
            target = date.fromisocalendar(year, week_num, 1)
        else:
            target = local_today()
        return _generate_routine_cards(week_key, target)

    cards = {}
    for fname in sorted(os.listdir(week_dir)):
        if fname.endswith(".json"):
            area_key = fname[:-5]
            path = os.path.join(week_dir, fname)
            data = _load_json(path)
            if data is not None:
                changed = _migrate_card(data)
                # Strip legacy carryover metadata before reconcilers so the
                # mid/sub-weekly passes no longer treat these rows as pinned.
                if _ensure_prev_week_overdue_streak(data, week_key, area_key):
                    changed = True
                if _reconcile_pinned_day_tasks_with_routines(data, week_key):
                    changed = True
                if _reconcile_high_frequency_tasks_with_planner(data, week_key):
                    changed = True
                if _reconcile_mid_frequency_tasks_with_last_completion(data, week_key):
                    changed = True
                if _reconcile_sub_weekly_tasks_with_last_completion(data, week_key):
                    changed = True
                if changed:
                    _save_json(path, data)
                cards[area_key] = data
    if not cards:
        parts = week_key.split("-W")
        year, wn = int(parts[0]), int(parts[1])
        return _generate_routine_cards(week_key, date.fromisocalendar(year, wn, 1))
    if _sync_task_weights_from_routines(cards):
        for area_key, data in cards.items():
            _save_json(_routine_path(week_key, area_key), data)
    return cards


def regenerate_routine_cards(week_key: str) -> dict[str, dict]:
    """Rebuild cards from routines.yaml, preserving filled dots and notes."""
    week_dir = _routine_dir(week_key)

    old_fills = {}
    old_notes = {}
    old_extra = {}
    if os.path.isdir(week_dir):
        for fname in os.listdir(week_dir):
            if not fname.endswith(".json"):
                continue
            ak = fname[:-5]
            data = _load_json(os.path.join(week_dir, fname))
            if not data:
                continue
            old_notes[ak] = data.get("notes", "")
            old_fills[ak] = {t["name"]: t["days"] for t in data.get("tasks", [])}
            old_extra[ak] = data.get("extra_tasks", [])
            os.remove(os.path.join(week_dir, fname))

    parts = week_key.split("-W")
    year, wn = int(parts[0]), int(parts[1])
    new_cards = _generate_routine_cards(week_key, date.fromisocalendar(year, wn, 1))

    for ak, card in new_cards.items():
        area_fills = old_fills.get(ak, {})
        for task in card["tasks"]:
            old_days = area_fills.get(task["name"])
            if not old_days:
                continue
            for di in range(min(7, len(task["days"]), len(old_days))):
                for doi in range(min(len(task["days"][di]), len(old_days[di]))):
                    if old_days[di][doi]:
                        task["days"][di][doi] = True
        card["notes"] = old_notes.get(ak, "")
        card["extra_tasks"] = old_extra.get(ak, [])
        _save_json(_routine_path(week_key, ak), card)

    return new_cards


def get_routine_card(week_key: str, area_key: str) -> dict | None:
    cards = get_routine_cards(week_key)
    return cards.get(area_key)


def save_routine_card(week_key: str, area_key: str, card: dict):
    os.makedirs(_routine_dir(week_key), exist_ok=True)
    _save_json(_routine_path(week_key, area_key), card)


def toggle_routine_dot(week_key: str, area_key: str,
                       task_idx: int, day_idx: int, dot_idx: int,
                       list_key: str = "tasks") -> bool:
    """Toggle a single dot. list_key is 'tasks' or 'extra_tasks'."""
    card = get_routine_card(week_key, area_key)
    if card is None:
        return False
    tasks = card.get(list_key, [])
    if task_idx >= len(tasks):
        return False
    days = tasks[task_idx].get("days", [])
    if day_idx >= len(days):
        return False
    dots = days[day_idx]
    if dot_idx >= len(dots):
        return False
    dots[dot_idx] = not dots[dot_idx]
    save_routine_card(week_key, area_key, card)
    return dots[dot_idx]


def set_routine_dot(
    week_key: str,
    area_key: str,
    task_idx: int,
    day_idx: int,
    dot_idx: int,
    value: bool,
    list_key: str = "tasks",
) -> bool:
    """Set a dot to a specific value (for push 'Done' without toggling)."""
    card = get_routine_card(week_key, area_key)
    if card is None:
        return False
    tasks = card.get(list_key, [])
    if task_idx >= len(tasks):
        return False
    days = tasks[task_idx].get("days", [])
    if day_idx >= len(days):
        return False
    dots = days[day_idx]
    if dot_idx >= len(dots):
        return False
    dots[dot_idx] = bool(value)
    save_routine_card(week_key, area_key, card)
    return dots[dot_idx]


def complete_routine_day_scheduled(
    week_key: str,
    area_key: str,
    task_idx: int,
    day_idx: int,
    list_key: str = "tasks",
) -> bool:
    """Mark all scheduled dots for this task on this day as done (push 'Done')."""
    card = get_routine_card(week_key, area_key)
    if card is None:
        return False
    tasks = card.get(list_key, [])
    if task_idx >= len(tasks):
        return False
    task = tasks[task_idx]
    days = task.get("days", [])
    if day_idx >= len(days):
        return False
    sched = list(task.get("scheduled") or [])
    while len(sched) < 7:
        sched.append(0)
    try:
        n = max(0, int(sched[day_idx]))
    except (TypeError, ValueError):
        n = 0
    if n <= 0:
        return False
    row = list(days[day_idx])
    while len(row) < n:
        row.append(False)
    for doi in range(min(n, len(row))):
        row[doi] = True
    days[day_idx] = row
    task["days"] = days
    save_routine_card(week_key, area_key, card)
    return True


def add_extra_task(week_key: str, area_key: str, name: str) -> dict | None:
    name = (name or "").strip()
    if not name:
        return None
    card = get_routine_card(week_key, area_key)
    if card is None:
        return None
    card.setdefault("extra_tasks", []).append(_blank_extra_task(name))
    save_routine_card(week_key, area_key, card)
    return card["extra_tasks"][-1]


def remove_extra_task(week_key: str, area_key: str, task_idx: int) -> bool:
    card = get_routine_card(week_key, area_key)
    if card is None:
        return False
    xs = card.get("extra_tasks", [])
    if 0 <= task_idx < len(xs):
        xs.pop(task_idx)
        save_routine_card(week_key, area_key, card)
        return True
    return False


def set_routine_notes(week_key: str, area_key: str, notes: str):
    card = get_routine_card(week_key, area_key)
    if card:
        card["notes"] = notes
        save_routine_card(week_key, area_key, card)


def list_routine_weeks() -> list[str]:
    d = config.ROUTINE_CARDS_DIR
    if not os.path.isdir(d):
        return []
    return sorted(
        f for f in os.listdir(d)
        if os.path.isdir(os.path.join(d, f)) and f.count("-W") == 1
    )


# ── Baby Cards ────────────────────────────────────────────────────

def _load_baby_config() -> dict:
    if not os.path.exists(config.BABY_CONFIG_FILE):
        return {"baby_name": "Baby", "tracks": []}
    with open(config.BABY_CONFIG_FILE, "r") as f:
        return yaml.safe_load(f) or {"baby_name": "Baby", "tracks": []}


def _baby_path(card_date: str) -> str:
    return os.path.join(config.BABY_CARDS_DIR, f"{card_date}.json")


def _generate_baby_card(card_date: str) -> dict:
    cfg = _load_baby_config()
    card = {
        "date": card_date,
        "baby_name": cfg.get("baby_name", "Baby"),
        "tracks": {},
    }
    for track in cfg.get("tracks", []):
        key = track["key"]
        t = track["type"]
        if t == "blocks":
            card["tracks"][key] = {
                "type": "blocks",
                "label": track.get("label", key),
                "hint": track.get("hint", ""),
                "squares": [False] * 48,
            }
        elif t == "tally":
            card["tracks"][key] = {
                "type": "tally",
                "label": track.get("label", key),
                "hint": track.get("hint", ""),
                "count": 0,
            }
        elif t == "notes":
            card["tracks"][key] = {
                "type": "notes",
                "label": track.get("label", key),
                "text": "",
            }

    os.makedirs(config.BABY_CARDS_DIR, exist_ok=True)
    _save_json(_baby_path(card_date), card)
    return card


def get_baby_card(card_date: str) -> dict:
    path = _baby_path(card_date)
    if os.path.exists(path):
        data = _load_json(path)
        if data is not None:
            return data
    return _generate_baby_card(card_date)


def save_baby_card(card_date: str, card: dict):
    os.makedirs(config.BABY_CARDS_DIR, exist_ok=True)
    _save_json(_baby_path(card_date), card)


def update_baby_track(card_date: str, track_key: str, update: dict) -> dict:
    """
    Partial update for a single track.
    For tally:  {"count": N}
    For blocks:  {"square": idx, "value": bool}
    For notes:   {"text": str}
    Returns the updated track.
    """
    card = get_baby_card(card_date)
    track = card.get("tracks", {}).get(track_key)
    if track is None:
        return {}

    t = track["type"]
    if t == "tally" and "count" in update:
        track["count"] = max(0, int(update["count"]))
    elif t == "blocks" and "squares" in update:
        incoming = update["squares"]
        if isinstance(incoming, list) and len(incoming) == len(track["squares"]):
            track["squares"] = [bool(v) for v in incoming]
    elif t == "blocks" and "square" in update:
        idx = int(update["square"])
        if 0 <= idx < len(track["squares"]):
            track["squares"][idx] = bool(update.get("value", False))
    elif t == "notes" and "text" in update:
        track["text"] = str(update["text"])

    save_baby_card(card_date, card)
    return track


def list_baby_days() -> list[str]:
    d = config.BABY_CARDS_DIR
    if not os.path.isdir(d):
        return []
    return sorted(
        f[:-5] for f in os.listdir(d)
        if f.endswith(".json")
    )


def _name_to_weight_for_area(area_key: str) -> dict[str, float]:
    routines = load_routines()
    area = routines.get("areas", {}).get(area_key) or {}
    out: dict[str, float] = {}
    for t in area.get("tasks", []):
        name = t.get("name")
        if not name:
            continue
        try:
            w = float(t.get("weight", 1) or 1)
            out[name] = w if w > 0 else 1.0
        except (TypeError, ValueError):
            out[name] = 1.0
    return out


def _repair_task_grid_for_scheduled(task: dict) -> bool:
    """
    Ensure each day row has at least max(scheduled[d], 1) booleans so every
    scheduled dot (including carryover bumps) exists in JSON and can score.
    """
    changed = False
    sched = list(task.get("scheduled") or [])
    while len(sched) < 7:
        sched.append(0)
        changed = True
    days = list(task.get("days") or [])
    while len(days) < 7:
        days.append([False])
        changed = True
    if len(sched) > 7:
        sched = sched[:7]
        changed = True
    if len(days) > 7:
        days = days[:7]
        changed = True
    for di in range(7):
        try:
            sc = max(0, int(sched[di]))
        except (TypeError, ValueError):
            sc = 0
        nlen = max(sc, 1)
        row = list(days[di]) if di < len(days) else []
        while len(row) < nlen:
            row.append(False)
            changed = True
        days[di] = row
    task["scheduled"] = sched
    task["days"] = days
    return changed


def _sync_task_weights_from_routines(cards: dict[str, dict]) -> bool:
    """Align YAML weights onto card JSON (main tasks by name)."""
    changed = False
    for area_key, card in cards.items():
        weights = _name_to_weight_for_area(area_key)
        for task in card.get("tasks", []):
            name = task.get("name")
            nw = weights.get(name, task.get("weight", 1.0))
            try:
                nw = float(nw)
                if nw <= 0:
                    nw = 1.0
            except (TypeError, ValueError):
                nw = 1.0
            if task.get("weight") != nw:
                task["weight"] = nw
                changed = True
        for task in card.get("extra_tasks", []):
            task.setdefault("weight", 1.0)
    return changed


def _migrate_card(card: dict) -> bool:
    """Add scheduled[], weights, and align day row lengths to scheduled counts."""
    changed = False
    card.setdefault("extra_tasks", [])
    for task in card.get("tasks", []):
        if "scheduled" not in task:
            task["scheduled"] = [len(d) for d in task.get("days", [])]
            changed = True
        task.setdefault("weight", 1.0)
        if _repair_task_grid_for_scheduled(task):
            changed = True
    for task in card.get("extra_tasks", []):
        if "scheduled" not in task:
            task["scheduled"] = [len(d) for d in task.get("days", [])]
            changed = True
        task.setdefault("temporary", True)
        task.setdefault("freq", 1)
        task.setdefault("weight", 1.0)
        if _repair_task_grid_for_scheduled(task):
            changed = True
    return changed


# ── Helpers ───────────────────────────────────────────────────────

def _load_json(path: str) -> dict:
    lock = _get_lock(path)
    with lock:
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            os.remove(path)
            return None


def _save_json(path: str, data: dict):
    lock = _get_lock(path)
    with lock:
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
