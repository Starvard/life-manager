"""Cascading day-plan timers (waterfall schedule).

Each timed day-plan task gets a duration equal to the gap until the next
timeline anchor (next timed task or flex slot). The first open task starts
at its scheduled clock time; when it is completed or skipped, the next
task's timer starts from that moment (not the original wall clock).

Resolved state (done / skipped timestamps) lives in
``data/routine-day-state/<YYYY-MM-DD>.json`` so it survives card regenerations
and does not pollute completion history.

Flex picks use ``flex_skips`` keyed by flex slot: skipping Laundry from
Morning flex refills that slot from the pool, but Laundry can still appear
in a later flex the same day.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from typing import Any

import config
from services.card_store import get_daily_flex_slots, get_routine_cards
from services.local_time import local_now, local_today, local_tz
from services.score_helpers import today_weekday_index
from services.week_planner import iso_week_key, week_start_date

DEFAULT_LAST_DURATION_MIN = 10
OVERDUE_REPEAT_MIN = 10


def _state_path(day_iso: str) -> str:
    return os.path.join(config.DATA_DIR, "routine-day-state", f"{day_iso}.json")


def task_state_key(area_key: str, task_name: str, list_key: str = "tasks") -> str:
    return f"{area_key}::{list_key}::{task_name}"


def load_day_state(day_iso: str | None = None) -> dict:
    day_iso = day_iso or local_today().isoformat()
    path = _state_path(day_iso)
    empty = {"date": day_iso, "resolved": {}, "flex_skips": {}}
    if not os.path.isfile(path):
        return empty
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return empty
        if not isinstance(data.get("resolved"), dict):
            data["resolved"] = {}
        # flex_skips: { flex_key: { task_key: {at, area_key, task_name, list_key} } }
        # Skipping a task from one flex does not block later flexes the same day.
        if not isinstance(data.get("flex_skips"), dict):
            data["flex_skips"] = {}
        else:
            cleaned: dict = {}
            for fk, bucket in data["flex_skips"].items():
                if isinstance(bucket, dict):
                    cleaned[str(fk)] = bucket
            data["flex_skips"] = cleaned
        data["date"] = day_iso
        return data
    except (json.JSONDecodeError, OSError):
        return empty


def save_day_state(state: dict) -> None:
    day_iso = state.get("date") or local_today().isoformat()
    state = dict(state)
    state["date"] = day_iso
    path = _state_path(day_iso)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, path)


def _parse_iso_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    tz = local_tz()
    if dt.tzinfo is None:
        if tz is not None:
            return dt.replace(tzinfo=tz)
        return dt
    if tz is not None:
        return dt.astimezone(tz)
    return dt


def _fmt_iso_dt(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _normalize_hhmm(raw) -> str | None:
    if raw is None or raw == "":
        return None
    s = str(raw).strip()
    if not s:
        return None
    parts = s.replace(".", ":").split(":")
    if len(parts) < 2:
        return None
    try:
        h = max(0, min(23, int(parts[0])))
        m = max(0, min(59, int(parts[1])))
    except ValueError:
        return None
    return f"{h:02d}:{m:02d}"


def _hhmm_to_minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _minutes_to_hhmm(total: int) -> str:
    total = max(0, min(24 * 60 - 1, int(total)))
    return f"{total // 60:02d}:{total % 60:02d}"


def _combine_local(day: date, hhmm: str) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    tz = local_tz()
    dt = datetime(day.year, day.month, day.day, h, m, 0)
    if tz is not None:
        return dt.replace(tzinfo=tz)
    return dt


def _is_daily(freq) -> bool:
    try:
        return float(freq or 0) >= 7
    except (TypeError, ValueError):
        return False


def _scheduled_count(task: dict, day_idx: int) -> int:
    sched = list(task.get("scheduled") or [])
    while len(sched) < 7:
        sched.append(0)
    try:
        return max(0, int(sched[day_idx]))
    except (TypeError, ValueError):
        return 0


def _day_dots_complete(task: dict, day_idx: int) -> bool:
    n = _scheduled_count(task, day_idx)
    if n <= 0:
        # Untimed/unscheduled recurring pulled into flex: one logical check.
        days = task.get("days") or []
        if day_idx >= len(days):
            return False
        row = days[day_idx] or []
        return bool(row and any(row))
    days = task.get("days") or []
    if day_idx >= len(days):
        return False
    row = list(days[day_idx] or [])
    while len(row) < n:
        row.append(False)
    return all(row[i] for i in range(n))


def mark_task_resolved(
    day_iso: str,
    area_key: str,
    task_name: str,
    status: str,
    list_key: str = "tasks",
    at: datetime | None = None,
) -> dict:
    """Record done/skipped for a task on a calendar day."""
    if status not in ("done", "skipped"):
        raise ValueError("status must be done or skipped")
    state = load_day_state(day_iso)
    key = task_state_key(area_key, task_name, list_key)
    when = at or local_now()
    state.setdefault("resolved", {})[key] = {
        "status": status,
        "at": _fmt_iso_dt(when),
        "area_key": area_key,
        "task_name": task_name,
        "list_key": list_key,
    }
    save_day_state(state)
    return state


def clear_task_resolved(
    day_iso: str,
    area_key: str,
    task_name: str,
    list_key: str = "tasks",
) -> dict:
    state = load_day_state(day_iso)
    key = task_state_key(area_key, task_name, list_key)
    if key in state.get("resolved", {}):
        del state["resolved"][key]
        save_day_state(state)
    return state


def skip_task_for_day(
    day_iso: str,
    area_key: str,
    task_name: str,
    list_key: str = "tasks",
) -> dict:
    return mark_task_resolved(day_iso, area_key, task_name, "skipped", list_key)


def unskip_task_for_day(
    day_iso: str,
    area_key: str,
    task_name: str,
    list_key: str = "tasks",
) -> dict:
    state = load_day_state(day_iso)
    key = task_state_key(area_key, task_name, list_key)
    entry = (state.get("resolved") or {}).get(key)
    if entry and entry.get("status") == "skipped":
        del state["resolved"][key]
        save_day_state(state)
    return state


def skip_flex_slot_task(
    day_iso: str,
    flex_key: str,
    area_key: str,
    task_name: str,
    list_key: str = "tasks",
    at: datetime | None = None,
) -> dict:
    """Skip a task from one flex slot only — later flexes may still pick it."""
    flex_key = (flex_key or "").strip()
    if not flex_key:
        raise ValueError("flex_key required")
    state = load_day_state(day_iso)
    key = task_state_key(area_key, task_name, list_key)
    when = at or local_now()
    bucket = state.setdefault("flex_skips", {}).setdefault(flex_key, {})
    bucket[key] = {
        "at": _fmt_iso_dt(when),
        "area_key": area_key,
        "task_name": task_name,
        "list_key": list_key,
    }
    save_day_state(state)
    return state


def unskip_flex_slot_task(
    day_iso: str,
    flex_key: str,
    area_key: str,
    task_name: str,
    list_key: str = "tasks",
) -> dict:
    flex_key = (flex_key or "").strip()
    state = load_day_state(day_iso)
    key = task_state_key(area_key, task_name, list_key)
    bucket = (state.get("flex_skips") or {}).get(flex_key) or {}
    if key in bucket:
        del bucket[key]
        if not bucket and flex_key in (state.get("flex_skips") or {}):
            del state["flex_skips"][flex_key]
        save_day_state(state)
    return state


def _flex_skip_keys(state: dict, flex_key: str | None) -> set[str]:
    if not flex_key:
        return set()
    bucket = (state.get("flex_skips") or {}).get(flex_key) or {}
    return set(bucket.keys()) if isinstance(bucket, dict) else set()


def _latest_flex_skip_at(state: dict, flex_key: str | None) -> datetime | None:
    if not flex_key:
        return None
    bucket = (state.get("flex_skips") or {}).get(flex_key) or {}
    latest: datetime | None = None
    for entry in bucket.values():
        if not isinstance(entry, dict):
            continue
        dt = _parse_iso_dt(entry.get("at"))
        if dt and (latest is None or dt > latest):
            latest = dt
    return latest


def sync_completion_stamp(
    week_key: str,
    area_key: str,
    task_idx: int,
    day_idx: int,
    list_key: str = "tasks",
) -> None:
    """After a dot change: stamp done when today's scheduled dots are full,
    clear a done stamp when they are not. Leaves explicit skips alone."""
    cards = get_routine_cards(week_key)
    card = cards.get(area_key)
    if not card:
        return
    tasks = card.get(list_key) or []
    if task_idx < 0 or task_idx >= len(tasks):
        return
    task = tasks[task_idx]
    name = (task.get("name") or "").strip()
    if not name:
        return
    week_start = card.get("week_start")
    if not week_start:
        return
    try:
        monday = date.fromisoformat(str(week_start)[:10])
    except ValueError:
        return
    day_iso = (monday + timedelta(days=day_idx)).isoformat()
    key = task_state_key(area_key, name, list_key)
    state = load_day_state(day_iso)
    existing = (state.get("resolved") or {}).get(key)

    if _day_dots_complete(task, day_idx):
        if existing and existing.get("status") == "skipped":
            # Completing after a skip upgrades to done at now.
            pass
        if not existing or existing.get("status") != "done":
            mark_task_resolved(day_iso, area_key, name, "done", list_key)
        return

    # Incomplete dots: drop a prior done stamp so the waterfall reopens.
    if existing and existing.get("status") == "done":
        clear_task_resolved(day_iso, area_key, name, list_key)


def _flex_priority(status: str) -> int:
    if status == "overdue":
        return 0
    if status == "due":
        return 1
    if status == "upcoming":
        return 2
    return 3


def _recurring_due_status(task: dict, day_iso: str) -> str:
    """Lightweight due/overdue for flex picks (scheduled-week heuristic)."""
    sched = task.get("scheduled") or []
    # If scheduled today → due; if any earlier weekday scheduled and not done → overdue-ish.
    # Callers already filter incomplete tasks.
    return "due"


def _pick_flex(
    candidates: list[dict],
    pool: str,
    used_keys: set[str],
    day_idx: int,
    slot_skip_keys: set[str] | None = None,
) -> dict | None:
    pool = (pool or "home").lower()
    skip_keys = slot_skip_keys or set()
    cand = []
    for c in candidates:
        if c["key"] in used_keys or c["key"] in skip_keys:
            continue
        if c.get("time"):
            continue  # timed stay on clock timeline
        if c.get("complete") or c.get("skipped"):
            continue
        # Pinned to other weekday (has schedule elsewhere, not today)
        sched = c["task"].get("scheduled") or []
        today_n = _scheduled_count(c["task"], day_idx)
        if today_n <= 0 and any(int(x or 0) > 0 for x in sched):
            continue
        at_work = bool(c["task"].get("at_work"))
        if pool == "at_work" and not at_work:
            continue
        if pool != "at_work" and at_work:
            continue
        cand.append(c)
    cand.sort(key=lambda c: (_flex_priority(c.get("due_status") or "due"), c["name"]))
    return cand[0] if cand else None


def _collect_task_candidates(cards: dict[str, dict], day_idx: int, state: dict) -> list[dict]:
    resolved = state.get("resolved") or {}
    out: list[dict] = []
    for area_key, card in cards.items():
        area_name = card.get("area_name", area_key)
        for list_key in ("tasks", "extra_tasks"):
            for task_idx, task in enumerate(card.get(list_key) or []):
                name = (task.get("name") or "").strip()
                if not name:
                    continue
                time_hhmm = _normalize_hhmm(task.get("time"))
                sched_n = _scheduled_count(task, day_idx)
                complete = _day_dots_complete(task, day_idx)
                key = task_state_key(area_key, name, list_key)
                entry = resolved.get(key)
                skipped = bool(entry and entry.get("status") == "skipped")
                if entry and entry.get("status") == "done":
                    complete = True
                try:
                    freq = float(task.get("freq") or 0)
                except (TypeError, ValueError):
                    freq = 0.0
                daily = _is_daily(freq)
                on_plan = bool(time_hhmm and (daily or sched_n > 0))
                out.append({
                    "key": key,
                    "area_key": area_key,
                    "area_name": area_name,
                    "list_key": list_key,
                    "task_idx": task_idx,
                    "task": task,
                    "name": name,
                    "time": time_hhmm,
                    "freq": freq,
                    "daily": daily,
                    "sched_n": sched_n,
                    "complete": complete,
                    "skipped": skipped,
                    "resolved_entry": entry,
                    "on_plan": on_plan,
                    "due_status": _recurring_due_status(task, ""),
                })
    return out


def build_day_plan_items(
    week_key: str | None = None,
    day_iso: str | None = None,
) -> list[dict]:
    """Ordered day-plan rows (tasks + empty flex anchors) with waterfall fields."""
    day = date.fromisoformat((day_iso or local_today().isoformat())[:10])
    day_iso = day.isoformat()
    monday = week_start_date(day)
    week_key = week_key or iso_week_key(monday)
    day_idx = (day - monday).days
    cards = get_routine_cards(week_key)
    state = load_day_state(day_iso)
    candidates = _collect_task_candidates(cards, day_idx, state)
    used: set[str] = set()
    raw_items: list[dict] = []

    for c in candidates:
        if not c["on_plan"] or not c["time"]:
            continue
        used.add(c["key"])
        raw_items.append({
            "sort_time": c["time"],
            "kind": "task",
            "flex": None,
            "candidate": c,
        })

    for slot in get_daily_flex_slots():
        t = _normalize_hhmm(slot.get("time"))
        if not t:
            continue
        on_days = slot.get("on_days")
        if isinstance(on_days, list) and on_days and day_idx not in {int(d) for d in on_days}:
            continue
        flex_key = str(slot.get("key") or "").strip()
        slot_skips = _flex_skip_keys(state, flex_key)
        pick = _pick_flex(
            candidates, slot.get("pool") or "home", used, day_idx, slot_skips
        )
        if not pick:
            raw_items.append({
                "sort_time": t,
                "kind": "flex_empty",
                "flex": {
                    "key": flex_key or slot.get("key"),
                    "label": slot.get("label") or "Flex",
                    "pool": slot.get("pool") or "home",
                    "empty": True,
                },
                "candidate": None,
            })
            continue
        used.add(pick["key"])
        raw_items.append({
            "sort_time": t,
            "kind": "task",
            "flex": {
                "key": flex_key or slot.get("key"),
                "label": slot.get("label") or "Flex",
                "pool": slot.get("pool") or "home",
                "empty": False,
            },
            "candidate": pick,
        })

    raw_items.sort(key=lambda it: it["sort_time"])

    # Duration from gap to next timeline anchor (task or empty flex).
    for i, it in enumerate(raw_items):
        start_m = _hhmm_to_minutes(it["sort_time"])
        if i + 1 < len(raw_items):
            dur = max(1, _hhmm_to_minutes(raw_items[i + 1]["sort_time"]) - start_m)
        else:
            dur = DEFAULT_LAST_DURATION_MIN
        it["duration_min"] = dur

    # Waterfall effective start/due for real tasks only.
    prev_finish: datetime | None = None
    locked = False
    now = local_now()
    out: list[dict] = []

    for it in raw_items:
        flex_meta = it.get("flex") or {}
        flex_key = flex_meta.get("key")
        latest_flex_skip = _latest_flex_skip_at(state, flex_key)

        if it["kind"] == "flex_empty":
            # Skipped-through empty flex still hands the cascade forward.
            if not locked and latest_flex_skip is not None:
                if prev_finish is None or latest_flex_skip > prev_finish:
                    prev_finish = latest_flex_skip
            out.append({
                "sort_time": it["sort_time"],
                "scheduled_time": it["sort_time"],
                "duration_min": it["duration_min"],
                "kind": "flex_empty",
                "flex": it["flex"],
                "flex_key": flex_key,
                "resolved": False,
                "complete": False,
                "skipped": False,
                "current": False,
                "locked": locked,
            })
            continue

        c = it["candidate"]
        dur = it["duration_min"]
        scheduled = it["sort_time"]
        entry = c.get("resolved_entry")
        complete = bool(c["complete"])
        skipped = bool(c["skipped"])
        resolved = complete or skipped

        if locked:
            effective_start = None
            effective_due = None
            current = False
        else:
            if prev_finish is None:
                effective_start = _combine_local(day, scheduled)
            else:
                effective_start = prev_finish
            # A prior skip inside this flex slot starts the replacement pick now.
            if latest_flex_skip is not None and latest_flex_skip > effective_start:
                effective_start = latest_flex_skip
            effective_due = effective_start + timedelta(minutes=dur)
            current = not resolved

        finish_at: datetime | None = None
        status = None
        if skipped and entry:
            status = "skipped"
            finish_at = _parse_iso_dt(entry.get("at")) or effective_start or _combine_local(day, scheduled)
        elif complete:
            status = "done"
            if entry and entry.get("status") == "done":
                finish_at = _parse_iso_dt(entry.get("at"))
            if finish_at is None:
                # Synthetic: treat as finished when the timer would have ended
                # (or now if still inside the window) so the chain keeps moving.
                base = effective_start or _combine_local(day, scheduled)
                synth_due = base + timedelta(minutes=dur)
                finish_at = min(now, synth_due) if now < synth_due else synth_due

        if resolved:
            prev_finish = finish_at or prev_finish or _combine_local(day, scheduled)
        else:
            # First open task becomes current; everything after is locked.
            locked = True

        # First incomplete scheduled dot for push Done ✓
        dot = 0
        if c["sched_n"] > 0:
            row = list((c["task"].get("days") or [None] * 7)[day_idx] or [])
            while len(row) < c["sched_n"]:
                row.append(False)
            for doi in range(c["sched_n"]):
                if not row[doi]:
                    dot = doi
                    break

        out.append({
            "sort_time": scheduled,
            "scheduled_time": scheduled,
            "effective_start": _fmt_iso_dt(effective_start) if effective_start else None,
            "effective_due": _fmt_iso_dt(effective_due) if effective_due else None,
            "duration_min": dur,
            "kind": "task",
            "flex": it["flex"],
            "flex_key": flex_key,
            "area_key": c["area_key"],
            "area_name": c["area_name"],
            "list_key": c["list_key"],
            "task_idx": c["task_idx"],
            "task_name": c["name"],
            "key": c["key"],
            "freq": c["freq"],
            "daily": c["daily"],
            "complete": complete,
            "skipped": skipped,
            "resolved": resolved,
            "status": status,
            "finished_at": _fmt_iso_dt(finish_at) if finish_at else None,
            "current": current,
            "locked": bool(effective_start is None and not resolved),
            "day_index": day_idx,
            "dot": dot,
            "week_key": week_key,
        })

    return out


def current_timeline_task(items: list[dict] | None = None, **kwargs) -> dict | None:
    items = items if items is not None else build_day_plan_items(**kwargs)
    for it in items:
        if it.get("kind") == "task" and it.get("current"):
            return it
    return None


def timeline_bootstrap(day_iso: str | None = None) -> dict[str, Any]:
    """Payload embedded in /today for client timers + skip UI."""
    day_iso = day_iso or local_today().isoformat()
    items = build_day_plan_items(day_iso=day_iso)
    state = load_day_state(day_iso)
    return {
        "date": day_iso,
        "now": _fmt_iso_dt(local_now()),
        "overdue_repeat_min": OVERDUE_REPEAT_MIN,
        "items": items,
        "resolved": state.get("resolved") or {},
        "flex_skips": state.get("flex_skips") or {},
        "current_key": (current_timeline_task(items) or {}).get("key"),
    }


def due_reminder_actions(items: list[dict] | None = None, now: datetime | None = None) -> list[dict]:
    """Reminder phases for the single current waterfall task.

    Returns zero or one action dict with keys:
    phase ('start'|'due'|'overdue'), item, slot_key (for idempotency).
    """
    now = now or local_now()
    items = items if items is not None else build_day_plan_items()
    cur = current_timeline_task(items)
    if not cur:
        return []
    start = _parse_iso_dt(cur.get("effective_start"))
    due = _parse_iso_dt(cur.get("effective_due"))
    if not start or not due:
        return []
    if now < start:
        return []

    actions: list[dict] = []
    day_iso = local_today().isoformat()
    tag_base = (
        f"lm-wf-{day_iso}-{cur['area_key']}-{cur['list_key']}-"
        f"{cur['task_idx']}"
    )

    # Start ping once the timer has begun.
    actions.append({
        "phase": "start",
        "item": cur,
        "tag": f"{tag_base}-start",
        "slot_key": f"{tag_base}-start",
        "title": f"⏰ {cur['task_name']}",
        "body": (
            f"{cur['area_name']} · you've got {cur['duration_min']} min. "
            f"Hit Done ✓ when finished, or skip in Today."
        ),
    })

    if now >= due:
        actions.append({
            "phase": "due",
            "item": cur,
            "tag": f"{tag_base}-due",
            "slot_key": f"{tag_base}-due",
            "title": f"⏱️ Should be done: {cur['task_name']}",
            "body": (
                f"{cur['area_name']} · timer's up ({cur['duration_min']} min). "
                f"Finish or skip so the day can keep moving."
            ),
        })
        overdue_for = int((now - due).total_seconds() // 60)
        # Every OVERDUE_REPEAT_MIN after due: 10, 20, 30, ...
        if overdue_for >= OVERDUE_REPEAT_MIN:
            n = overdue_for // OVERDUE_REPEAT_MIN
            slot = n * OVERDUE_REPEAT_MIN
            actions.append({
                "phase": "overdue",
                "item": cur,
                "tag": f"{tag_base}-overdue",
                "slot_key": f"{tag_base}-overdue-{slot}",
                "title": f"🔔 Still open: {cur['task_name']}",
                "body": (
                    f"{cur['area_name']} · {slot} min past the timer. "
                    f"Done ✓ or skip to unlock the next step."
                ),
            })
    return actions
