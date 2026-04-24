"""Service package startup patches."""

from __future__ import annotations

import importlib
from datetime import timedelta


def _install_routine_card_completion_patch() -> None:
    """Treat any checked routine dot as the task's real completion day.

    The card scheduler uses each task's last completion date to decide when the
    next weekly or sub-weekly card should become due. The original scan only
    counted checked cells that were already scheduled cells. That made late
    completions behave like they happened on the old scheduled day, or not count
    at all when clicked in an unscheduled/bonus cell.
    """

    cs = importlib.import_module("services.card_store")

    def merge_last_completed_from_this_card(card, week_key, acc, as_of):
        monday = cs._monday_from_week_key(week_key)
        if monday is None:
            return
        area_key = card.get("area_key")
        if not area_key:
            return
        for task in card.get("tasks", []):
            task_name = task.get("name")
            if not task_name:
                continue
            days = task.get("days") or []
            for day_idx in range(min(7, len(days))):
                day_date = monday + timedelta(days=day_idx)
                if day_date > as_of:
                    continue
                row = days[day_idx] if day_idx < len(days) else []
                if any(bool(v) for v in (row or [])):
                    key = (area_key, task_name)
                    prev = acc.get(key)
                    acc[key] = day_date if prev is None else max(prev, day_date)

    def collect_last_completed_before_week(before_week_key):
        cutoff = cs._monday_from_week_key(before_week_key)
        if cutoff is None:
            return {}
        base = cs.config.ROUTINE_CARDS_DIR
        if not cs.os.path.isdir(base):
            return {}

        try:
            dir_mtime = cs.os.path.getmtime(base)
        except OSError:
            dir_mtime = None
        cache_key = before_week_key
        with cs._last_completed_cache_lock:
            cached = cs._last_completed_cache.get(cache_key)
            if cached is not None and cached[0] == dir_mtime:
                return cached[1]

        acc = {}
        for week_name in cs.os.listdir(base):
            if week_name.count("-W") != 1:
                continue
            week_monday = cs._monday_from_week_key(week_name)
            if week_monday is None or week_monday >= cutoff:
                continue
            week_dir = cs.os.path.join(base, week_name)
            if not cs.os.path.isdir(week_dir):
                continue
            for fname in cs.os.listdir(week_dir):
                if not fname.endswith(".json"):
                    continue
                area_key = fname[:-5]
                card = cs._load_json(cs.os.path.join(week_dir, fname))
                if not card:
                    continue
                for task in card.get("tasks", []):
                    task_name = task.get("name")
                    if not task_name:
                        continue
                    days = task.get("days") or []
                    for day_idx in range(min(7, len(days))):
                        row = days[day_idx] if day_idx < len(days) else []
                        if any(bool(v) for v in (row or [])):
                            done_day = week_monday + timedelta(days=day_idx)
                            key = (area_key, task_name)
                            prev = acc.get(key)
                            if prev is None or done_day > prev:
                                acc[key] = done_day

        with cs._last_completed_cache_lock:
            cs._last_completed_cache[cache_key] = (dir_mtime, acc)
        return acc

    cs._merge_last_completed_from_this_card = merge_last_completed_from_this_card
    cs._collect_last_completed_before_week = collect_last_completed_before_week


_install_routine_card_completion_patch()
