"""
Web Push routine reminders.

Driven by ``run_reminder_scan``:

- **Waterfall timers** (default): the current day-plan task pings when its
  cascaded timer starts, when the timer ends, and every 10 minutes while
  still open. Completing or skipping advances the cascade.
- **Legacy wall-clock reminders**: each task's ``time`` / ``notify_time``
  once per day. Re-enable with ``LM_REMINDER_WALL_CLOCK=1``.
- **Periodic nudge** (off by default): legacy every-few-hours check-in.
  Re-enable with ``LM_REMINDER_PERIODIC_NUDGE=1`` if you want it back.

Stable notification tags let Android replace duplicate nags instead of
stacking them.
"""

from __future__ import annotations

import json
import os
import traceback
from datetime import date, time as time_cls

import config
from services.card_store import get_routine_cards
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
        return {"last_sent": {}, "waterfall_sent": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data.get("last_sent"), dict):
            data["last_sent"] = {}
        if not isinstance(data.get("waterfall_sent"), dict):
            data["waterfall_sent"] = {}
        data.pop("daily_scheduled", None)  # legacy per-dot cooldown state
        return data
    except (json.JSONDecodeError, OSError):
        return {"last_sent": {}, "waterfall_sent": {}}


def _save_state(state: dict) -> None:
    path = config.PUSH_REMINDER_STATE_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, path)


def reminder_tag(week_key: str, area_key: str, list_key: str, task_idx: int, day_idx: int) -> str:
    """Stable within a day (same-day re-sends replace instead of stacking) but
    fresh across days — browsers can silently suppress a tag that has been
    re-shown too many times, which would eat future reminders."""
    return f"lm-{week_key}-{area_key}-{list_key}-{task_idx}-d{day_idx}"


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
                tag = reminder_tag(week_key, area_key, list_key, task_idx, day_idx)
                tname = task.get("name", "Task")
                body = f"{area_name}: {tname} — scheduled today"
                try:
                    freq = float(task.get("freq") or 0)
                except (TypeError, ValueError):
                    freq = 0.0
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
                    "freq": freq,
                })
    return out


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


def notify_time_lookup() -> dict[tuple[str, str], str]:
    """(area_key, task_name) -> 'HH:MM' for push reminders.

    Uses the day-plan ``time`` by default so reminders match Today's schedule.
    An explicit ``notify_time`` (or legacy ``notify_at``) overrides when set.
    """
    data = load_routines()
    out: dict[tuple[str, str], str] = {}
    for ak, area in data.get("areas", {}).items():
        for t in area.get("tasks", []):
            name = (t.get("name") or "").strip()
            if not name:
                continue
            override = None
            if "notify_time" in t:
                override = _normalize_hhmm(t.get("notify_time"))
            elif "notify_at" in t:
                override = _normalize_hhmm(t.get("notify_at"))
            sched = _normalize_hhmm(t.get("time"))
            hhmm = override or sched
            if hhmm:
                out[(ak, name)] = hhmm
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


def _send_to_all(subs: list[dict], payload: dict) -> int:
    """Send one payload to every subscription; returns delivery count."""
    n = 0
    for sub in subs:
        if send_push_to_subscription(sub, payload):
            n += 1
    return n


def _collect_nags_for_today() -> list[dict]:
    try:
        week_key = _week_key_containing_today()
        cards = get_routine_cards(week_key)
        week_start = next((c.get("week_start") for c in cards.values()), None)
        if not week_start:
            return []
        day_idx = today_weekday_index(week_start)
        if day_idx is None:
            return []
        return collect_today_nags(week_key, day_idx)
    except Exception:
        traceback.print_exc()
        return []


def _pick_featured_nag(nags: list[dict]) -> dict:
    """The task to spotlight in the periodic nudge. Non-daily tasks first —
    those are the ones that slip — matching the Today page's Up Next order."""
    return sorted(nags, key=lambda n: (n.get("freq", 0) >= 7,))[0]


def _task_action_fields(nag: dict) -> dict:
    """Payload fields the service worker needs for the notification's
    Done ✓ action (completes the dot without opening the app)."""
    return {
        "week_key": nag["week_key"],
        "area_key": nag["area_key"],
        "task": nag["task_idx"],
        "day": nag["day"],
        "dot": nag["dot"],
        "list": nag["list_key"],
    }


def _send_notify_time_reminders(subs: list[dict], nags: list[dict], state: dict) -> int:
    """Legacy per-task wall-clock reminders (opt-in via LM_REMINDER_WALL_CLOCK)."""
    times = notify_time_lookup()
    if not times:
        return 0
    today_iso = local_today().isoformat()
    last_sent = state.get("last_sent") or {}
    sent = 0
    ordered = sorted(
        nags,
        key=lambda n: times.get((n["area_key"], n["task_name"])) or "99:99",
    )
    for nag in ordered:
        hhmm = times.get((nag["area_key"], nag["task_name"]))
        if not hhmm or not _notify_time_reached(hhmm):
            continue
        if last_sent.get(nag["tag"]) == today_iso:
            continue
        payload = {
            "title": f"⏰ {nag['task_name']}",
            "body": f"{nag['area_name']} · scheduled {hhmm}. Hit Done ✓ when it's finished.",
            "tag": nag["tag"],
            "url": "/today",
            "requireInteraction": True,
            **_task_action_fields(nag),
        }
        if _send_to_all(subs, payload) > 0:
            last_sent[nag["tag"]] = today_iso
            sent += 1
    state["last_sent"] = {k: v for k, v in last_sent.items() if v == today_iso}
    return sent


def _waterfall_reminders_enabled() -> bool:
    """On by default; set LM_REMINDER_WATERFALL=0 to disable."""
    raw = os.environ.get("LM_REMINDER_WATERFALL", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _wall_clock_reminders_enabled() -> bool:
    """Off by default now that waterfall timers drive pushes."""
    return os.environ.get("LM_REMINDER_WALL_CLOCK", "").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _send_waterfall_reminders(subs: list[dict], state: dict) -> int:
    """Ping the current cascaded task: start, due, then every 10 min overdue."""
    from services.day_timeline import due_reminder_actions

    today_iso = local_today().isoformat()
    sent_map = state.get("waterfall_sent") or {}
    # Drop other days so the file stays small.
    sent_map = {k: v for k, v in sent_map.items() if str(v).startswith(today_iso) or v == today_iso}
    sent = 0
    try:
        actions = due_reminder_actions()
    except Exception:
        traceback.print_exc()
        actions = []

    # One notification per scan: prefer overdue > due > start so a late
    # catch-up doesn't spam every phase at once.
    phase_rank = {"overdue": 0, "due": 1, "start": 2}
    actions = sorted(actions, key=lambda a: phase_rank.get(a.get("phase"), 9))
    for action in actions:
        slot = action["slot_key"]
        if sent_map.get(slot) == today_iso:
            continue
        item = action["item"]
        payload = {
            "title": action["title"],
            "body": action["body"],
            "tag": action["tag"],
            "url": "/today",
            "requireInteraction": True,
            "week_key": item["week_key"],
            "area_key": item["area_key"],
            "task": item["task_idx"],
            "task_name": item["task_name"],
            "day": item["day_index"],
            "day_iso": today_iso,
            "dot": item.get("dot", 0),
            "list": item["list_key"],
        }
        if _send_to_all(subs, payload) > 0:
            sent_map[slot] = today_iso
            sent += 1
            # Mark milder phases for this task as handled so we don't
            # follow an overdue ping with a stale "time to start" ping.
            tag = action["tag"]
            tag_base = tag
            for suffix in ("-overdue", "-due", "-start"):
                if tag.endswith(suffix):
                    tag_base = tag[: -len(suffix)]
                    break
            sent_map[f"{tag_base}-start"] = today_iso
            sent_map[f"{tag_base}-due"] = today_iso
            break
    state["waterfall_sent"] = sent_map
    return sent


def _periodic_nudge_enabled() -> bool:
    """Legacy 3h check-in — off by default now that schedule times drive pushes."""
    return os.environ.get("LM_REMINDER_PERIODIC_NUDGE", "").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _send_periodic_nudge(subs: list[dict], nags: list[dict], state: dict) -> int:
    """Recurring check-in (default every 3h, 7am-10pm) spotlighting the next
    task. Skipped entirely when nothing is open, so every notification is
    actionable. The scheduler calls this every LM_REMINDER_INTERVAL_MINUTES
    (default 30); `last_routine_ping` ensures one send per time slot."""
    now = local_now()
    start, end, every = reminder_window()
    hour = now.hour
    if hour < start or hour > end:
        return 0

    slots = list(range(start, end + 1, every))  # e.g. [7, 10, 13, 16, 19, 22]
    due = [s for s in slots if hour >= s]
    if not due:
        return 0
    slot = max(due)
    today_iso = local_today().isoformat()
    slot_key = f"{today_iso}:{slot:02d}"

    if state.get("last_routine_ping") == slot_key:
        return 0  # already pinged for this slot today
    if not nags:
        # All clear — stay quiet instead of pinging "nothing to do". Mark the
        # slot handled so a task un-checked later doesn't trigger a late ping.
        state["last_routine_ping"] = slot_key
        return 0

    count = len(nags)
    featured = _pick_featured_nag(nags)
    others = count - 1
    name_bit = f"{featured['task_name']} · {featured['area_name']}"
    evening = slot >= max(slots[-2] if len(slots) > 1 else slots[-1], 18)
    if evening:
        title = "Evening check-in 🔥"
        body = (
            f"{count} routine{'s' if count != 1 else ''} left today. "
            f"Up next: {name_bit}. Hit Done ✓ to clear it."
        )
    else:
        title = "Routine check-in"
        if others > 0:
            body = f"Up next: {name_bit}. {others} more open today."
        else:
            body = f"Up next: {name_bit}. Last one today!"
    payload = {
        "title": title,
        "body": body,
        # Date-scoped: nudges within a day replace each other, but each day
        # starts with a fresh tag (repeated tags can get silently suppressed).
        "tag": f"lm-routine-ping-{today_iso}",
        "url": "/today",
        **_task_action_fields(featured),
    }

    delivered = _send_to_all(subs, payload)
    if delivered > 0:
        state["last_routine_ping"] = slot_key
    return delivered


def run_reminder_scan() -> dict:
    """Send any due routine reminders. Called by the in-process scheduler and
    by POST /api/push/run-reminders (external cron backstop for when the Fly
    machine was asleep). Safe to call repeatedly: waterfall phases and
    legacy wall-clock reminders are idempotent per slot.

    Returns a small summary dict for the HTTP endpoint / logs."""
    summary = {
        "subscriptions": 0,
        "waterfall_reminders_sent": 0,
        "task_reminders_sent": 0,
        "nudge_deliveries": 0,
    }
    if webpush is None:
        summary["skipped"] = "pywebpush not installed"
        return summary
    subs = push_subscriptions.list_subscriptions()
    summary["subscriptions"] = len(subs)
    if not subs:
        summary["skipped"] = "no subscribed devices"
        return summary

    vapid_keys.ensure_vapid_keys()
    nags = _collect_nags_for_today()
    summary["open_today"] = len(nags)

    state = _load_state()
    if _waterfall_reminders_enabled():
        summary["waterfall_reminders_sent"] = _send_waterfall_reminders(subs, state)
    else:
        summary["waterfall"] = "off"
    if _wall_clock_reminders_enabled():
        summary["task_reminders_sent"] = _send_notify_time_reminders(subs, nags, state)
    else:
        summary["wall_clock"] = "off"
    if _periodic_nudge_enabled():
        summary["nudge_deliveries"] = _send_periodic_nudge(subs, nags, state)
    else:
        summary["nudge_deliveries"] = 0
        summary["periodic_nudge"] = "off"
    _save_state(state)
    return summary
