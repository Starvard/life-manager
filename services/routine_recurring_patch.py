"""Runtime safety patch for rare recurring routine tasks.

This keeps long-interval tasks robust without disturbing the daily fast path:
- If a sub-weekly task was due in a prior week and never completed, it carries
  forward into the current generated card as due.
- Manual completions on an unscheduled rare-recurring row count as a real
  completion, so the next due window moves forward.

Kept separate from card_store.py so the hot card code stays stable and small.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import config
from services.local_time import local_today


def _safe_freq(task: dict) -> float:
    try:
        return float(task.get("freq") or 0)
    except (TypeError, ValueError):
        return 0.0


def _row_has_fill(row) -> bool:
    return any(bool(v) for v in (row or []))


def _task_has_any_fill(task: dict) -> bool:
    return any(_row_has_fill(row) for row in (task.get("days") or []))


def _scheduled_count(sched: list[int], day_idx: int) -> int:
    try:
        return max(0, int(sched[day_idx]))
    except (IndexError, TypeError, ValueError):
        return 0


def _iter_prior_week_cards(cs, before_week_key: str):
    cutoff = cs._monday_from_week_key(before_week_key)
    if cutoff is None:
        return
    base = config.ROUTINE_CARDS_DIR
    if not os.path.isdir(base):
        return

    weeks: list[tuple[date, str]] = []
    for wk_name in os.listdir(base):
        if wk_name.count("-W") != 1:
            continue
        wk_mon = cs._monday_from_week_key(wk_name)
        if wk_mon is None or wk_mon >= cutoff:
            continue
        weeks.append((wk_mon, wk_name))

    for wk_mon, wk_name in sorted(weeks):
        wk_dir = os.path.join(base, wk_name)
        if not os.path.isdir(wk_dir):
            continue
        for fname in sorted(os.listdir(wk_dir)):
            if not fname.endswith(".json"):
                continue
            area_key = fname[:-5]
            card = cs._load_json(os.path.join(wk_dir, fname))
            if card:
                yield wk_mon, area_key, card


def _collect_unfinished_subweekly_due(cs, before_week_key: str) -> dict[tuple[str, str], date]:
    """Return rare recurring tasks that became due earlier and remain undone."""
    outstanding: dict[tuple[str, str], date] = {}

    for wk_mon, area_key_from_file, card in _iter_prior_week_cards(cs, before_week_key) or []:
        area_key = card.get("area_key") or area_key_from_file
        if not area_key:
            continue

        for task in card.get("tasks", []) or []:
            name = task.get("name")
            freq = _safe_freq(task)
            if not name or not (0 < freq < 1):
                continue

            key = (area_key, name)
            sched = cs._sched_seven(task.get("scheduled"))
            days = task.get("days") or []

            for day_idx in range(7):
                row = days[day_idx] if day_idx < len(days) else []
                day_date = wk_mon + timedelta(days=day_idx)

                # Any checkmark on a rare recurring task counts as completion,
                # even if the UI row was a 0-scheduled / watch row.
                if _row_has_fill(row):
                    outstanding.pop(key, None)
                    continue

                if _scheduled_count(sched, day_idx) > 0:
                    outstanding.setdefault(key, day_date)

    return outstanding


def _carry_unfinished_subweekly_due_into_card(cs, card: dict, week_key: str) -> bool:
    area_key = card.get("area_key")
    week_start = cs._monday_from_week_key(week_key)
    if not area_key or week_start is None:
        return False

    outstanding = _collect_unfinished_subweekly_due(cs, week_key)
    if not outstanding:
        return False

    today = local_today()
    if week_start <= today <= week_start + timedelta(days=6):
        carry_day = (today - week_start).days
    elif today < week_start:
        carry_day = 0
    else:
        carry_day = 6

    changed = False
    for task in card.get("tasks", []) or []:
        name = task.get("name")
        freq = _safe_freq(task)
        if not name or not (0 < freq < 1):
            continue
        key = (area_key, name)
        if key not in outstanding:
            continue
        if _task_has_any_fill(task):
            continue

        sched = cs._sched_seven(task.get("scheduled"))
        if sum(sched) > 0:
            continue

        target = [0] * 7
        target[carry_day] = 1
        task["scheduled"] = target
        task["days"] = cs._rebuild_days_preserving_fills(task.get("days") or [], target)
        task["overdue_from"] = outstanding[key].isoformat()
        changed = True

    return changed


def install() -> None:
    import services.card_store as cs

    if getattr(cs, "_rare_recurring_patch_installed", False):
        return

    original_merge = cs._merge_last_completed_from_this_card
    original_reconcile_subweekly = cs._reconcile_sub_weekly_tasks_with_last_completion
    original_generate = cs._generate_routine_cards

    def patched_merge_last_completed_from_this_card(card, week_key, acc, as_of):
        original_merge(card, week_key, acc, as_of)
        week_start = cs._monday_from_week_key(week_key)
        area_key = card.get("area_key")
        if week_start is None or not area_key:
            return
        for task in card.get("tasks", []) or []:
            name = task.get("name")
            if not name or not (0 < _safe_freq(task) < 1):
                continue
            for day_idx, row in enumerate(task.get("days") or []):
                day_date = week_start + timedelta(days=day_idx)
                if day_date > as_of:
                    continue
                if _row_has_fill(row):
                    key = (area_key, name)
                    prev = acc.get(key)
                    acc[key] = day_date if prev is None else max(prev, day_date)

    def patched_reconcile_sub_weekly_tasks_with_last_completion(card, week_key):
        changed = original_reconcile_subweekly(card, week_key)
        if _carry_unfinished_subweekly_due_into_card(cs, card, week_key):
            changed = True
        return changed

    def patched_generate_routine_cards(week_key, target_date):
        cards = original_generate(week_key, target_date)
        for area_key, card in cards.items():
            if _carry_unfinished_subweekly_due_into_card(cs, card, week_key):
                cs._save_json(cs._routine_path(week_key, area_key), card)
        return cards

    cs._merge_last_completed_from_this_card = patched_merge_last_completed_from_this_card
    cs._reconcile_sub_weekly_tasks_with_last_completion = patched_reconcile_sub_weekly_tasks_with_last_completion
    cs._generate_routine_cards = patched_generate_routine_cards
    cs._rare_recurring_patch_installed = True
