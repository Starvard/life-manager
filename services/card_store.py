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

import config
from services.routine_manager import load_routines
from services.week_planner import (
    plan_week, iso_week_key, week_start_date, upcoming_week_monday,
)


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


def _should_roll_carryover(task: dict, prev_card: dict, task_name: str) -> bool:
    """
    Roll unfinished work into Monday only when it helps without piling on.

    Rules:
    - Previous week must have had at least one scheduled dot still unchecked.
    - This week's plan must NOT already schedule Monday (no duplicate nag).
    - Target frequency at most ~2x/week (and not daily): weekly, bi-weekly, monthly,
      etc. Skip 3+ times/week (e.g. shower x4) — those rhythms already give many
      chances; overdue coloring on each scheduled dot handles misses.
    """
    if not _prev_week_has_unfilled_scheduled(prev_card, task_name):
        return False
    f = float(task.get("freq") or 0)
    if f >= 7:
        return False
    if f > 2:
        return False
    sched = list(task.get("scheduled") or [0] * 7)
    while len(sched) < 7:
        sched.append(0)
    if sched[0] >= 1:
        return False
    return True


def _prev_week_has_unfilled_scheduled(prev_card: dict, task_name: str) -> bool:
    """True if that task had at least one scheduled dot left unfilled last week."""
    for t in prev_card.get("tasks", []):
        if t.get("name") != task_name:
            continue
        sched = t.get("scheduled") or [0] * 7
        days = t.get("days") or []
        for di in range(min(7, len(days))):
            sc = sched[di] if di < len(sched) else 0
            row = days[di]
            for doi in range(min(sc, len(row))):
                if not row[doi]:
                    return True
        return False
    return False


def _apply_carryover_to_task(task: dict) -> None:
    """Add one scheduled Monday dot for this task (caller sets carryover_week_key)."""
    sched = list(task.get("scheduled") or [0] * 7)
    while len(sched) < 7:
        sched.append(0)
    if sched[0] == 0:
        sched[0] = 1
    else:
        sched[0] = sched[0] + 1
        task["days"][0].append(False)
    task["scheduled"] = sched
    task["carryover"] = True


def _apply_week_carryover(card: dict, prev_card: dict | None, prev_wk: str) -> None:
    """Add one scheduled Monday dot where _should_roll_carryover allows."""
    if not prev_card or not prev_wk:
        return
    for task in card.get("tasks", []):
        if not _should_roll_carryover(task, prev_card, task["name"]):
            continue
        _apply_carryover_to_task(task)
        task["carryover_week_key"] = prev_wk


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
        old_days = task.get("days") or [[False] for _ in range(7)]
        new_days = []
        for d in range(7):
            ns = target_sched[d]
            nlen = max(ns, 1)
            row = [False] * nlen
            old_row = old_days[d] if d < len(old_days) else []
            os_ = old_sched[d]
            for doi in range(min(ns, os_, len(old_row))):
                row[doi] = bool(old_row[doi])
            for doi in range(ns, nlen):
                if doi < len(old_row):
                    row[doi] = bool(old_row[doi])
            new_days.append(row)
        task["scheduled"] = target_sched
        task["days"] = new_days
        task.pop("carryover", None)
        task.pop("carryover_week_key", None)
        changed = True
    return changed


def _ensure_carryover_on_load(card: dict, week_key: str, area_key: str) -> bool:
    """
    If this week's JSON was created before carryover ran, apply it when the prior
    week's card exists and had unfilled scheduled work. Idempotent via carryover_week_key.
    """
    prev_wk = _prev_week_key(week_key)
    if not prev_wk:
        return False
    prev_card = _load_card_file(prev_wk, area_key)
    if not prev_card:
        return False
    changed = False
    for task in card.get("tasks", []):
        if task.get("carryover_week_key") == prev_wk:
            continue
        if task.get("carryover") and task.get("carryover_week_key") is None:
            task["carryover_week_key"] = prev_wk
            changed = True
            continue
        if not _should_roll_carryover(task, prev_card, task["name"]):
            continue
        _apply_carryover_to_task(task)
        task["carryover_week_key"] = prev_wk
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
    plans = plan_week(routines.get("areas", {}), target_date)

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
        prev = _load_card_file(prev_wk, plan["key"])
        _apply_week_carryover(card, prev, prev_wk)
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
            target = date.today()
        return _generate_routine_cards(week_key, target)

    cards = {}
    for fname in sorted(os.listdir(week_dir)):
        if fname.endswith(".json"):
            area_key = fname[:-5]
            path = os.path.join(week_dir, fname)
            data = _load_json(path)
            if data is not None:
                changed = _migrate_card(data)
                if _reconcile_high_frequency_tasks_with_planner(data, week_key):
                    changed = True
                if _ensure_carryover_on_load(data, week_key, area_key):
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
