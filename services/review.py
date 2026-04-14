"""
Handles weekly review data: storing completion notes, loading photos,
and tracking history over time.
"""

import json
import os
from datetime import date

from config import HISTORY_FILE, PHOTOS_DIR
from services.week_planner import iso_week_key


def _load_history() -> dict:
    if not os.path.exists(HISTORY_FILE):
        return {"weeks": {}}
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)


def _save_history(data: dict):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_week_review(week_key: str) -> dict | None:
    history = _load_history()
    return history.get("weeks", {}).get(week_key)


def save_week_review(week_key: str, review_data: dict):
    """
    Save review data for a week. review_data should contain:
      - tasks: dict of area_key -> [{name, completed, target, notes}]
      - reflection: str
      - suggestions_accepted: list of suggestion dicts
    """
    history = _load_history()
    history.setdefault("weeks", {})[week_key] = review_data
    _save_history(history)


def get_all_weeks() -> list[str]:
    """Return sorted list of all reviewed week keys."""
    history = _load_history()
    return sorted(history.get("weeks", {}).keys())


def get_week_photos(week_key: str) -> list[str]:
    """Return list of photo filenames for a given week."""
    week_dir = os.path.join(PHOTOS_DIR, week_key)
    if not os.path.isdir(week_dir):
        return []
    extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic"}
    photos = []
    for f in sorted(os.listdir(week_dir)):
        if os.path.splitext(f)[1].lower() in extensions:
            photos.append(f)
    return photos


def get_completion_trends(area_key: str = None, last_n_weeks: int = 8) -> list[dict]:
    """
    Get completion trends over the last N reviewed weeks.
    Returns list of {week_key, area_key, task_name, completed, target, rate}.
    """
    history = _load_history()
    all_weeks = sorted(history.get("weeks", {}).keys())
    recent = all_weeks[-last_n_weeks:] if len(all_weeks) > last_n_weeks else all_weeks

    trends = []
    for wk in recent:
        review = history["weeks"][wk]
        tasks_by_area = review.get("tasks", {})
        for ak, tasks in tasks_by_area.items():
            if area_key and ak != area_key:
                continue
            for t in tasks:
                completed = t.get("completed", 0)
                target = t.get("target", 0)
                rate = (completed / target * 100) if target > 0 else 0
                trends.append({
                    "week_key": wk,
                    "area_key": ak,
                    "task_name": t.get("name", ""),
                    "completed": completed,
                    "target": target,
                    "rate": round(rate, 1),
                })
    return trends


def generate_suggestions(week_key: str) -> list[dict]:
    """
    Analyze recent history and generate adaptive suggestions.
    Returns list of {area_key, task_name, suggestion, current_freq, suggested_freq}.
    """
    history = _load_history()
    all_weeks = sorted(history.get("weeks", {}).keys())

    if len(all_weeks) < 2:
        return []

    recent_2 = all_weeks[-2:]
    suggestions = []

    task_history = {}
    for wk in recent_2:
        review = history["weeks"][wk]
        for ak, tasks in review.get("tasks", {}).items():
            for t in tasks:
                key = (ak, t["name"])
                task_history.setdefault(key, []).append({
                    "completed": t.get("completed", 0),
                    "target": t.get("target", 0),
                })

    for (ak, task_name), entries in task_history.items():
        rates = []
        for e in entries:
            if e["target"] > 0:
                rates.append(e["completed"] / e["target"])

        if not rates:
            continue

        avg_rate = sum(rates) / len(rates)
        current_target = entries[-1]["target"]

        if avg_rate < 0.4 and current_target > 1:
            suggestions.append({
                "area_key": ak,
                "task_name": task_name,
                "suggestion": "reduce",
                "reason": f"Averaging {avg_rate:.0%} completion over last {len(rates)} weeks",
                "current_freq": current_target,
                "suggested_freq": max(1, current_target - 1),
            })
        elif all(r >= 1.0 for r in rates) and len(rates) >= 2:
            suggestions.append({
                "area_key": ak,
                "task_name": task_name,
                "suggestion": "increase",
                "reason": f"100% completion for {len(rates)} consecutive weeks",
                "current_freq": current_target,
                "suggested_freq": current_target + 1,
            })

    return suggestions
