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
    d = today or date.today()
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
    """Clear push cooldown when this task has no incomplete scheduled dots left today."""
    card = get_routine_card(week_key, area_key)
    if not card:
        return
    tasks = card.get(list_key, [])
    if task_idx >= len(tasks):
        return
    if _first_incomplete_scheduled_dot(tasks[task_idx], day_idx) is None:
        clear_reminder_cooldown(reminder_tag(week_key, area_key, list_key, task_idx))


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
    return datetime.now().time() >= target


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


def run_reminder_scan() -> None:
    if webpush is None:
        return
    subs = push_subscriptions.list_subscriptions()
    if not subs:
        return
    vapid_keys.ensure_vapid_keys()

    week_key = _week_key_containing_today()
    cards = get_routine_cards(week_key)
    week_start = next((c.get("week_start") for c in cards.values()), None)
    if not week_start:
        return
    day_idx = today_weekday_index(week_start)
    if day_idx is None:
        return

    nags = collect_today_nags(week_key, day_idx)
    if not nags:
        return

    state = _load_state()
    last_sent = state.setdefault("last_sent", {})
    daily_scheduled = state.setdefault("daily_scheduled", {})
    now = time.time()
    cool = _cooldown_seconds()
    today_iso = date.today().isoformat()
    nt_map = notify_time_lookup()

    for item in nags:
        tag = item["tag"]
        list_key = item["list_key"]
        if list_key != "tasks":
            nt = None
        else:
            nt = nt_map.get((item["area_key"], item["task_name"]))

        if nt:
            if not _notify_time_reached(nt):
                continue
            if daily_scheduled.get(tag) == today_iso:
                continue
        else:
            prev = last_sent.get(tag)
            if prev is not None and (now - prev) < cool:
                continue

        payload = {
            "title": item["title"],
            "body": item["body"],
            "tag": item["tag"],
            "week_key": item["week_key"],
            "area_key": item["area_key"],
            "task": item["task_idx"],
            "day": item["day"],
            "dot": item["dot"],
            "list": item["list_key"],
            "url": f"/cards?week={item['week_key']}",
        }
        any_ok = False
        for sub in subs:
            if send_push_to_subscription(sub, payload):
                any_ok = True
        if any_ok:
            if nt:
                daily_scheduled[tag] = today_iso
            else:
                last_sent[tag] = now
            _save_state(state)
