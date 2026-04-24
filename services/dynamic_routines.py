from __future__ import annotations

import json
import os
from datetime import date, timedelta
from typing import Any

from flask import jsonify, redirect, render_template, request, url_for

import config
from services.local_time import local_today
from services.routine_manager import load_routines
from services.week_planner import effective_weekly_freq, iso_week_key, week_start_date
from services.card_store import get_routine_cards, get_routine_card, save_routine_card


def _week_monday(week_key: str) -> date | None:
    parts = week_key.split("-W")
    if len(parts) != 2:
        return None
    try:
        return date.fromisocalendar(int(parts[0]), int(parts[1]), 1)
    except ValueError:
        return None


def _task_key(area_key: str, task_name: str) -> str:
    return f"{area_key}::{task_name}"


def _interval_days(freq: float) -> int:
    if freq <= 0:
        return 9999
    if freq >= 7:
        return 1
    return max(1, round(7.0 / float(freq)))


def _load_all_card_weeks() -> list[str]:
    base = config.ROUTINE_CARDS_DIR
    if not os.path.isdir(base):
        return []
    weeks = [w for w in os.listdir(base) if w.count("-W") == 1 and os.path.isdir(os.path.join(base, w))]
    return sorted(weeks)


def _scan_completion_history() -> dict[str, list[str]]:
    history: dict[str, set[str]] = {}
    for week_key in _load_all_card_weeks():
        monday = _week_monday(week_key)
        if monday is None:
            continue
        week_dir = os.path.join(config.ROUTINE_CARDS_DIR, week_key)
        for fname in os.listdir(week_dir):
            if not fname.endswith(".json"):
                continue
            area_key = fname[:-5]
            path = os.path.join(week_dir, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    card = json.load(f)
            except Exception:
                continue
            for task in card.get("tasks", []):
                name = task.get("name")
                if not name:
                    continue
                key = _task_key(area_key, name)
                days = task.get("days") or []
                for day_idx in range(min(7, len(days))):
                    row = days[day_idx] or []
                    if any(bool(v) for v in row):
                        history.setdefault(key, set()).add((monday + timedelta(days=day_idx)).isoformat())
    return {k: sorted(v) for k, v in history.items()}


def _current_defs(selected: date) -> list[dict[str, Any]]:
    routines = load_routines()
    order = routines.get("area_order", [])
    areas = routines.get("areas", {})
    area_order = {k: i for i, k in enumerate(order)}
    out = []
    for area_key, area in areas.items():
        for idx, raw in enumerate(area.get("tasks", []) or []):
            name = raw.get("name")
            if not name:
                continue
            freq = float(effective_weekly_freq(raw) or 0)
            if freq <= 0:
                continue
            out.append({
                "key": _task_key(area_key, name),
                "area_key": area_key,
                "area_name": area.get("name", area_key),
                "area_order": area_order.get(area_key, 999),
                "task_index": idx,
                "name": name,
                "freq": freq,
                "interval_days": _interval_days(freq),
                "weight": raw.get("weight", 1),
                "on_days": raw.get("on_days") or [],
            })
    out.sort(key=lambda x: (x["area_order"], x["name"].lower()))
    return out


def _scheduled_dates_from_cards(task: dict[str, Any], start: date, end: date) -> list[date]:
    dates: list[date] = []
    wk = week_start_date(start)
    while wk <= end:
        week_key = iso_week_key(wk)
        card = get_routine_card(week_key, task["area_key"])
        if card:
            for stored in card.get("tasks", []):
                if stored.get("name") != task["name"]:
                    continue
                sched = list(stored.get("scheduled") or [])[:7]
                while len(sched) < 7:
                    sched.append(0)
                for di, count in enumerate(sched):
                    try:
                        n = int(count or 0)
                    except (TypeError, ValueError):
                        n = 0
                    if n > 0:
                        d = wk + timedelta(days=di)
                        if start <= d <= end:
                            dates.append(d)
                break
        wk += timedelta(days=7)
    return sorted(set(dates))


def _completion_dates(history: dict[str, list[str]], key: str) -> list[date]:
    out = []
    for s in history.get(key, []):
        try:
            out.append(date.fromisoformat(s))
        except ValueError:
            pass
    return sorted(out)


def dynamic_routine_context(selected: date | None = None) -> dict[str, Any]:
    selected = selected or local_today()
    today = local_today()
    start = selected - timedelta(days=21)
    end = selected + timedelta(days=21)
    history = _scan_completion_history()
    tasks = _current_defs(selected)
    sections: dict[str, dict[str, Any]] = {}
    upcoming: list[dict[str, Any]] = []
    done_today: list[dict[str, Any]] = []

    for task in tasks:
        completions = _completion_dates(history, task["key"])
        completed_on_selected = selected in completions
        last_done = max([d for d in completions if d <= selected], default=None)
        sched_dates = _scheduled_dates_from_cards(task, start, end)
        past_sched = [d for d in sched_dates if d <= selected]
        future_sched = [d for d in sched_dates if d > selected]

        if last_done:
            next_due = last_done + timedelta(days=task["interval_days"])
        elif past_sched:
            next_due = past_sched[0]
        elif future_sched:
            next_due = future_sched[0]
        else:
            next_due = selected

        is_due = next_due <= selected and not completed_on_selected
        is_upcoming = selected < next_due <= selected + timedelta(days=7)
        overdue_days = max(0, (selected - next_due).days) if is_due else 0
        item = {
            **task,
            "completed_on_selected": completed_on_selected,
            "last_done": last_done.isoformat() if last_done else None,
            "next_due": next_due.isoformat(),
            "next_due_label": _friendly_due_label(next_due, selected),
            "overdue_days": overdue_days,
            "status": "done" if completed_on_selected else ("overdue" if overdue_days > 0 else ("due" if is_due else "upcoming")),
            "selected_date": selected.isoformat(),
            "week_key": iso_week_key(week_start_date(selected)),
            "day_idx": selected.weekday(),
        }
        if completed_on_selected:
            done_today.append(item)
        elif is_due:
            sec = sections.setdefault(task["area_key"], {"area_name": task["area_name"], "items": []})
            sec["items"].append(item)
        elif is_upcoming:
            upcoming.append(item)

    ordered_sections = [
        {"area_key": k, **v}
        for k, v in sorted(sections.items(), key=lambda kv: min((it["area_order"] for it in kv[1]["items"]), default=999))
    ]
    upcoming.sort(key=lambda x: (x["next_due"], x["area_order"], x["name"].lower()))
    done_today.sort(key=lambda x: (x["area_order"], x["name"].lower()))
    due_count = sum(len(s["items"]) for s in ordered_sections)
    return {
        "selected_date": selected.isoformat(),
        "selected_label": selected.strftime("%a, %b %-d") if os.name != "nt" else selected.strftime("%a, %b %#d"),
        "today_iso": today.isoformat(),
        "sections": ordered_sections,
        "upcoming": upcoming[:20],
        "done_today": done_today,
        "due_count": due_count,
        "done_count": len(done_today),
        "legacy_week": iso_week_key(week_start_date(selected)),
    }


def _friendly_due_label(d: date, selected: date) -> str:
    delta = (d - selected).days
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Tomorrow"
    if delta == -1:
        return "Yesterday"
    if delta < 0:
        return f"{abs(delta)} days overdue"
    if delta < 7:
        return d.strftime("%a")
    return d.isoformat()


def _ensure_week_card_for_date(day: date, area_key: str):
    week_key = iso_week_key(week_start_date(day))
    cards = get_routine_cards(week_key)
    return week_key, cards.get(area_key)


def toggle_completion(area_key: str, task_name: str, day: date) -> bool:
    week_key, card = _ensure_week_card_for_date(day, area_key)
    if not card:
        return False
    day_idx = day.weekday()
    for task in card.get("tasks", []):
        if task.get("name") != task_name:
            continue
        days = task.setdefault("days", [[False] for _ in range(7)])
        while len(days) < 7:
            days.append([False])
        row = days[day_idx] or [False]
        days[day_idx] = row
        existing = next((i for i, v in enumerate(row) if v), None)
        if existing is not None:
            row[existing] = False
            save_routine_card(week_key, area_key, card)
            return False
        row[0] = True
        save_routine_card(week_key, area_key, card)
        return True
    return False


def register_dynamic_routine_routes(app) -> None:
    if getattr(app, "_dynamic_routine_routes_registered", False):
        return
    app._dynamic_routine_routes_registered = True

    @app.before_request
    def _dynamic_cards_override():
        if request.endpoint not in ("cards_page", "cards_day_page"):
            return None
        if request.args.get("legacy") == "1":
            return None
        day_str = request.args.get("date", local_today().isoformat())
        if request.endpoint == "cards_page":
            day_str = local_today().isoformat()
        try:
            selected = date.fromisoformat(day_str)
        except ValueError:
            selected = local_today()
        return render_template("routine_dynamic.html", **dynamic_routine_context(selected))

    @app.route("/api/routine-dynamic/toggle", methods=["POST"])
    def api_dynamic_routine_toggle():
        body = request.get_json(force=True) or {}
        area_key = body.get("area_key", "")
        task_name = body.get("task_name", "")
        day_str = body.get("date", local_today().isoformat())
        try:
            day = date.fromisoformat(day_str)
        except ValueError:
            return jsonify({"ok": False, "error": "invalid date"}), 400
        if not area_key or not task_name:
            return jsonify({"ok": False, "error": "missing task"}), 400
        value = toggle_completion(area_key, task_name, day)
        return jsonify({"ok": True, "value": value, "context": dynamic_routine_context(day)})
