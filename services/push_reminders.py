"""
Scan today's incomplete scheduled routine dots and send Web Push reminders.

Uses stable notification tags (one per task row + list) so Android replaces
duplicate nags. Cooldown avoids buzzing the same task too often while still
uncompleted.
"""

from __future__ import annotations

import json
import os
import time
import traceback
from datetime import date, datetime, time as time_cls

import config
from services.card_store import get_routine_card, get_routine_cards
from services.local_time import local_now, local_today
from services.routine_manager import load_routines
from services.score_helpers import today_weekday_index
from services.week_planner import iso_week_key, week_start_date
from services import push_subscriptions
from services import vapid_keys

try:
    from pywebpush import WebPushException, webpush
except ImportError:
    webpush = None  # type: ignore
    WebPushException = Exception  # type: ignore


def _week_key_containing_today(today: date | None = None) -> str:
    d = today or local_today()
    monday = week_start_date(d)
    return iso_week_key(monday)


def _load_state() -> dict:
    path = config.PUSH_REMINDER_STATE_FILE
    if not os.path.isfile(path):
        return {"last_sent": {}, "daily_scheduled": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data.get("last_sent"), dict):
            data["last_sent"] = {}
        if not isinstance(data.get("daily_scheduled"), dict):
            data["daily_scheduled"] = {}
        return data
    except (json.JSONDecodeError, OSError):
        return {"last_sent": {}, "daily_scheduled": {}}


def _save_state(state: dict) -> None:
    path = config.PUSH_REMINDER_STATE_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, path)


def reminder_tag(week_key: str, area_key: str, list_key: str, task_idx: int) -> str:
    return f"lm-{week_key}-{area_key}-{list_key}-{task_idx}"


def refresh_reminder_state_after_dot_change(
    week_key: str,
    area_key: str,
    list_key: str,
    task_idx: int,
    day_idx: int,
) -> None:
    """No-op since reminders moved to a simple periodic nudge (no per-task
    cooldowns). Kept for API compatibility with app.py; returning early also
    avoids an extra card file read on every dot toggle."""
    return


def clear_reminder_cooldown(tag: str) -> None:
    """Call when a task is completed so the next due window can notify again."""
    state = _load_state()
    ls = state.get("last_sent", {})
    if tag in ls:
        del ls[tag]
        state["last_sent"] = ls
    ds = state.get("daily_scheduled", {})
    if tag in ds:
        del ds[tag]
        state["daily_scheduled"] = ds
    _save_state(state)


def _first_incomplete_scheduled_dot(task: dict, day_idx: int) -> int | None:
    sched = list(task.get("scheduled") or [])
    while len(sched) < 7:
        sched.append(0)
    try:
        n = max(0, int(sched[day_idx]))
    except (TypeError, ValueError):
        n = 0
    if n <= 0:
        return None
    days = task.get("days") or []
    if day_idx >= len(days):
        return None
    row = days[day_idx]
    for doi in range(min(n, len(row))):
        if not row[doi]:
            return doi
    return None


def collect_today_nags(week_key: str, day_idx: int) -> list[dict]:
    """
    Build reminder payloads for incomplete scheduled dots today.
    Each item: tag, title, body, week_key, area_key, area_name, task_name,
    task_idx, day, dot, list_key
    """
    cards = get_routine_cards(week_key)
    out: list[dict] = []
    for area_key, card in cards.items():
        area_name = card.get("area_name", area_key)
        for list_key in ("tasks", "extra_tasks"):
            tasks = card.get(list_key, [])
            for task_idx, task in enumerate(tasks):
                doi = _first_incomplete_scheduled_dot(task, day_idx)
                if doi is None:
                    continue
                tag = reminder_tag(week_key, area_key, list_key, task_idx)
                tname = task.get("name", "Task")
                body = f"{area_name}: {tname} — scheduled today"
                out.append({
                    "tag": tag,
                    "title": "Life Manager",
                    "body": body,
                    "week_key": week_key,
                    "area_key": area_key,
                    "area_name": area_name,
                    "task_name": tname,
                    "task_idx": task_idx,
                    "day": day_idx,
                    "dot": doi,
                    "list_key": list_key,
                })
    return out


def notify_time_lookup() -> dict[tuple[str, str], str]:
    """(area_key, task_name) -> 'HH:MM' from routines.yaml (local server time)."""
    data = load_routines()
    out: dict[tuple[str, str], str] = {}
    for ak, area in data.get("areas", {}).items():
        for t in area.get("tasks", []):
            name = (t.get("name") or "").strip()
            raw = t.get("notify_time") if "notify_time" in t else t.get("notify_at")
            if not name:
                continue
            if raw is None or raw == "":
                continue
            s = str(raw).strip()
            if not s:
                continue
            parts = s.replace(".", ":").split(":")
            if len(parts) < 2:
                continue
            try:
                h = max(0, min(23, int(parts[0])))
                m = max(0, min(59, int(parts[1])))
            except ValueError:
                continue
            out[(ak, name)] = f"{h:02d}:{m:02d}"
    return out


def _notify_time_reached(hhmm: str) -> bool:
    try:
        h, m = hhmm.split(":")
        target = time_cls(int(h), int(m))
    except (ValueError, TypeError):
        return False
    return local_now().time() >= target


def send_test_push_to_all() -> tuple[int, int]:
    """Returns (success_count, subscription_count)."""
    if webpush is None:
        return 0, 0
    subs = push_subscriptions.list_subscriptions()
    if not subs:
        return 0, 0
    vapid_keys.ensure_vapid_keys()
    payload = {
        "title": "Life Manager",
        "body": "Test notification — push is working.",
        "tag": "lm-test",
        "week_key": "",
        "area_key": "",
        "task": 0,
        "day": 0,
        "dot": 0,
        "list": "tasks",
        "url": "/",
    }
    n = 0
    for sub in subs:
        if send_push_to_subscription(sub, payload):
            n += 1
    return n, len(subs)


def _cooldown_seconds() -> float:
    try:
        m = float(os.environ.get("LM_REMINDER_COOLDOWN_MINUTES", "120"))
    except ValueError:
        m = 120.0
    return max(60.0, m * 60.0)


def _vapid_contact() -> str:
    return os.environ.get("LM_VAPID_CONTACT", "mailto:life-manager@localhost")


def send_push_to_subscription(sub: dict, payload: dict) -> bool:
    if webpush is None:
        return False
    pem_path = vapid_keys.vapid_private_key_pem_path()
    sub_info = {
        "endpoint": sub["endpoint"],
        "keys": {
            "p256dh": sub.get("keys", {}).get("p256dh", ""),
            "auth": sub.get("keys", {}).get("auth", ""),
        },
    }
    try:
        webpush(
            subscription_info=sub_info,
            data=json.dumps(payload),
            vapid_private_key=pem_path,
            vapid_claims={"sub": _vapid_contact()},
            ttl=86400,
        )
        return True
    except WebPushException as e:
        resp = getattr(e, "response", None)
        if resp is not None and resp.status_code in (404, 410):
            push_subscriptions.remove_subscription(sub.get("endpoint", ""))
        else:
            traceback.print_exc()
        return False
    except Exception:
        traceback.print_exc()
        return False


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def reminder_window() -> tuple[int, int, int]:
    """(start_hour, end_hour, every_hours) for the periodic routine nudge.

    Defaults: ping every 3 hours from 7am to 10pm (local time). Override with
    LM_REMINDER_START_HOUR / LM_REMINDER_END_HOUR / LM_REMINDER_EVERY_HOURS.
    """
    start = max(0, min(23, _int_env("LM_REMINDER_START_HOUR", 7)))
    end = max(0, min(23, _int_env("LM_REMINDER_END_HOUR", 22)))
    every = max(1, min(12, _int_env("LM_REMINDER_EVERY_HOURS", 3)))
    if end < start:
        end = start
    return start, end, every


def _count_incomplete_today() -> int:
    """Best-effort count of routine dots scheduled today that aren't done yet."""
    try:
        week_key = _week_key_containing_today()
        cards = get_routine_cards(week_key)
        week_start = next((c.get("week_start") for c in cards.values()), None)
        if not week_start:
            return 0
        day_idx = today_weekday_index(week_start)
        if day_idx is None:
            return 0
        return len(collect_today_nags(week_key, day_idx))
    except Exception:
        return 0


def run_reminder_scan() -> None:
    """Simple recurring nudge: ping all subscribed devices every few hours during
    the day (default every 3h, 7am-10pm) so routines stay top of mind.

    The scheduler calls this every LM_REMINDER_INTERVAL_MINUTES (default 30), so
    we only actually send once per time slot — tracked by `last_routine_ping`."""
    if webpush is None:
        return
    subs = push_subscriptions.list_subscriptions()
    if not subs:
        return

    now = local_now()
    start, end, every = reminder_window()
    hour = now.hour
    if hour < start or hour > end:
        return

    slots = list(range(start, end + 1, every))  # e.g. [7, 10, 13, 16, 19, 22]
    due = [s for s in slots if hour >= s]
    if not due:
        return
    slot = max(due)
    today_iso = local_today().isoformat()
    slot_key = f"{today_iso}:{slot:02d}"

    state = _load_state()
    if state.get("last_routine_ping") == slot_key:
        return  # already pinged for this slot today

    vapid_keys.ensure_vapid_keys()
    count = _count_incomplete_today()
    if count > 0:
        body = f"{count} routine{'s' if count != 1 else ''} still open today — tap to knock one out."
    else:
        body = "Routine check-in 🌱 Tap to see what's coming up."
    payload = {
        "title": "Routine check-in",
        "body": body,
        "tag": "lm-routine-ping",
        "url": "/today",
        "list": "tasks",
    }

    any_ok = False
    for sub in subs:
        if send_push_to_subscription(sub, payload):
            any_ok = True
    if any_ok:
        state["last_routine_ping"] = slot_key
        _save_state(state)
