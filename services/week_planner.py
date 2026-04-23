"""
Determines which tasks appear on a given week's cards and how many dots
each task gets per day.

Key design: a GLOBAL scheduler assigns periodic tasks (1-6x/week) across
all areas simultaneously, so they spread across different days instead
of all landing on the same day.

Frequency rules:
  freq >= 7   -> appears every day, dots_per_day = freq / 7
  1 <= freq < 7 -> scheduled across the week via load balancer
  freq < 1    -> appears every week (for recording) but only gets
                 a dot on the weeks it's "due"
  freq_per_year -> converted to weekly freq internally

Optional per-task ``on_days``: list of weekday indices 0=Monday .. 6=Sunday.
When set, dots are pinned to those days instead of auto-scheduling (daily
tasks still ignore ``on_days``).
"""

import math
from datetime import date, timedelta

from services.local_time import local_today

# Optional (area_key, task_name) -> most recent calendar day any scheduled dot was completed.
LastCompletedMap = dict[tuple[str, str], date]


def iso_week_key(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def week_start_date(d: date) -> date:
    return d - timedelta(days=d.weekday())


def upcoming_week_monday(d: date) -> date:
    """On Sunday, return tomorrow (next Monday). Otherwise return this week's Monday."""
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return week_start_date(d)


def task_weight_value(task: dict) -> float:
    """Importance multiplier for scoring (default 1)."""
    try:
        w = float(task.get("weight", 1) or 1)
        return w if w > 0 else 1.0
    except (TypeError, ValueError):
        return 1.0


def effective_weekly_freq(task: dict) -> float:
    if "freq" in task:
        return task["freq"]
    if "freq_per_year" in task:
        return task["freq_per_year"] / 52.0
    return 0


def should_appear_this_week(
    task: dict,
    week_date: date,
    *,
    last_completed: date | None = None,
) -> bool:
    """For sub-weekly tasks (freq < 1), decide if this is a 'due' week.

    When ``last_completed`` is known, the next due window is anchored to it —
    so completing a task early actually pushes the next reminder forward.
    (E.g. Knife Sharpening at ``freq_per_year: 4`` = every ~13 weeks: if you
    sharpen 2 months early, the task stays quiet for the next ~13 weeks from
    that completion instead of rearming on the original name-hash cadence.)

    Without ``last_completed`` we fall back to the deterministic
    ``week_num % period`` pattern so brand-new calendars still surface every
    sub-weekly task on *some* week.
    """
    freq = effective_weekly_freq(task)
    if freq <= 0:
        return False
    if freq >= 1:
        return True
    period = max(1, round(1.0 / freq))

    if last_completed is not None:
        monday = week_start_date(week_date)
        done_monday = week_start_date(last_completed)
        weeks_since = (monday - done_monday).days // 7
        if weeks_since < 0:
            return False
        return weeks_since >= period

    week_num = week_date.isocalendar()[1]
    offset = sum(ord(c) for c in task["name"]) % period
    return (week_num % period) == offset


def _normalize_on_days(raw) -> list[int] | None:
    """Return sorted unique weekday indices 0=Mon..6=Sun, or None to use auto-schedule."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        raw = [int(raw)]
    if not raw:
        return None
    out: list[int] = []
    for x in raw:
        try:
            i = int(x)
            if 0 <= i <= 6:
                out.append(i)
        except (TypeError, ValueError):
            continue
    return sorted(set(out)) if out else None


def _dots_from_fixed_days(n_dots: int, on_days: list[int]) -> list[int]:
    """Place n_dots on the given weekdays; cycle if n_dots > len(on_days)."""
    days = sorted({d for d in on_days if 0 <= d <= 6})
    if not days:
        return [0] * 7
    dots = [0] * 7
    if n_dots <= len(days):
        for d in days[:n_dots]:
            dots[d] = 1
    else:
        for i in range(n_dots):
            dots[days[i % len(days)]] += 1
    return dots


def _distribute_daily(freq: float) -> list[int]:
    """For freq >= 7, distribute dots evenly across 7 days."""
    base = int(freq // 7)
    extra = round(freq - base * 7)
    dots = [base] * 7
    if extra > 0:
        step = 7 / extra
        for i in range(extra):
            idx = int(round(i * step)) % 7
            dots[idx] += 1
    return dots


def _schedule_periodic_global(
    tasks_to_schedule: list[dict], day_loads: list[float] | None = None
) -> None:
    """
    Assign dots across the week using a spacing-first algorithm.

    For each task, an evenly-spaced base pattern is generated, then all 7
    rotations are scored against the global day-load totals.  The rotation
    with the lowest cumulative load wins.  This guarantees that a task
    with freq=4 gets roughly every-other-day spacing (gaps of 2,2,2,1)
    instead of clustering on consecutive days.

    Tasks are processed most-constrained-first (highest count).
    Mutates each task dict in place, setting task["dots"].
    """
    if day_loads is None:
        day_loads = [0.0] * 7
    ordered = sorted(tasks_to_schedule, key=lambda t: -t["_count"])

    for task in ordered:
        count = task["_count"]
        if count <= 0:
            task["dots"] = [0] * 7
            continue
        if count >= 7:
            task["dots"] = [1] * 7
            for d in range(7):
                day_loads[d] += 1
            continue

        gap = 7.0 / count
        base = [int(i * gap) for i in range(count)]

        best_days = None
        best_score = float("inf")
        for offset in range(7):
            rotated = [(d + offset) % 7 for d in base]
            if len(set(rotated)) < count:
                continue
            score = sum(day_loads[d] for d in rotated)
            if score < best_score:
                best_score = score
                best_days = rotated

        if best_days is None:
            best_days = base

        dots = [0] * 7
        for d in best_days:
            dots[d] = 1
            day_loads[d] += 1
        task["dots"] = dots


def _scheduled_day_indices(dots: list[int]) -> list[int]:
    return sorted(d for d in range(7) if d < len(dots) and dots[d] > 0)


def _rotate_pattern_days(base_days: list[int], offset: int) -> list[int]:
    return sorted(((d + offset) % 7) for d in base_days)


def _all_rotations(base_days: list[int]) -> list[list[int]]:
    if not base_days:
        return []
    seen: set[tuple[int, ...]] = set()
    out: list[list[int]] = []
    for r in range(7):
        rot = _rotate_pattern_days(base_days, r)
        key = tuple(rot)
        if key not in seen:
            seen.add(key)
            out.append(rot)
    return out


def _dots_from_day_indices(days_hit: list[int]) -> list[int]:
    dots = [0] * 7
    for d in days_hit:
        if 0 <= d <= 6:
            dots[d] = 1
    return dots


def _nudge_periodic_for_last_completion(
    task: dict,
    monday: date,
    last_completed: date | None,
    as_of: date,
) -> None:
    """
    Shift 1 <= freq < 7 dot pattern based on the last time any scheduled dot
    was completed (no on_days — fixed weekday tasks stay pinned).

    - If the weekly (rounded count == 1) habit was already done this ISO week,
      drop scheduled dots for the rest of the week.
    - Otherwise pick a rotation of the global pattern so every scheduled day
      is strictly after ``last_completed`` on the calendar, and the first slot
      is close to last + (7/n) days.
    """
    freq = float(task.get("freq") or 0)
    if not (1 <= freq < 7):
        return
    if task.get("on_days"):
        return
    n = max(1, round(freq))
    dots = list(task.get("dots") or [0] * 7)
    while len(dots) < 7:
        dots.append(0)
    dots = dots[:7]
    base_days = _scheduled_day_indices(dots)
    if not base_days:
        return

    if last_completed is None:
        task["dots"] = dots
        return

    week_end = monday + timedelta(days=6)
    if last_completed > week_end:
        task["dots"] = dots
        return

    if n == 1:
        if monday <= last_completed <= week_end:
            task["dots"] = [0] * 7
        return

    gap_days = max(1, round(7.0 / float(n)))
    ideal_next = last_completed + timedelta(days=gap_days)
    rotations = _all_rotations(base_days)
    best: list[int] | None = None
    best_score = float("inf")
    as_di = (as_of - monday).days

    for rot in rotations:
        slot_dates = [monday + timedelta(days=d) for d in rot]
        strict_ok = all(sd > last_completed for sd in slot_dates)
        if strict_ok:
            first_date = min(sd for sd in slot_dates)
            score = float(abs((first_date - ideal_next).days))
        else:
            future = [sd for sd in slot_dates if sd > last_completed]
            if not future:
                continue
            first_date = min(future)
            score = 50.0 + float(abs((first_date - ideal_next).days))

        if 0 <= as_di <= 6 and rot:
            if not any(d <= as_di for d in rot):
                score += 30.0

        if score < best_score:
            best_score = score
            best = rot

    if best is not None:
        task["dots"] = _dots_from_day_indices(best)
    else:
        task["dots"] = dots


def plan_week(
    areas: dict,
    target_date: date | None = None,
    *,
    last_completed: LastCompletedMap | None = None,
    as_of_date: date | None = None,
) -> list[dict]:
    """
    Build the full week plan with globally-balanced scheduling.

    ALL tasks from every area are included in the output, even if they
    have 0 dots this week (so the user can record unscheduled completions).
    """
    if target_date is None:
        target_date = local_today()

    monday = week_start_date(target_date)
    wk = iso_week_key(target_date)
    as_of = as_of_date if as_of_date is not None else local_today()

    # Collect every task, tag with scheduling metadata
    all_tasks = []
    for key, area in areas.items():
        for task in area.get("tasks", []):
            freq = effective_weekly_freq(task)
            if freq <= 0:
                continue
            lc = last_completed.get((key, task["name"])) if last_completed else None
            all_tasks.append({
                "area_key": key,
                "name": task["name"],
                "freq": freq,
                "weight": task_weight_value(task),
                "is_due": should_appear_this_week(
                    task, target_date, last_completed=lc
                ),
                "on_days": _normalize_on_days(task.get("on_days")),
            })

    # Phase 1: daily tasks (freq >= 7) get dots on every day
    for t in all_tasks:
        if t["freq"] >= 7:
            t["dots"] = _distribute_daily(t["freq"])

    day_loads = [0.0] * 7
    for t in all_tasks:
        if "dots" in t:
            for d in range(7):
                day_loads[d] += t["dots"][d]

    # Phase 2: periodic tasks (1 <= freq < 7)
    periodic = [t for t in all_tasks if 1 <= t["freq"] < 7]
    free_periodic = []
    for t in periodic:
        n = round(t["freq"])
        od = t.get("on_days")
        if od:
            t["dots"] = _dots_from_fixed_days(n, od)
            for d in range(7):
                day_loads[d] += t["dots"][d]
        else:
            t["_count"] = n
            free_periodic.append(t)
    _schedule_periodic_global(free_periodic, day_loads)

    if last_completed:
        for t in free_periodic:
            key = (t["area_key"], t["name"])
            lc = last_completed.get(key)
            _nudge_periodic_for_last_completion(t, monday, lc, as_of)

    # Phase 3: sub-weekly (freq < 1) — 1 dot on due weeks, optional fixed weekday
    sub_weekly_due = [t for t in all_tasks if t["freq"] < 1 and t["is_due"]]
    free_sw = []
    for t in sub_weekly_due:
        od = t.get("on_days")
        if od:
            t["dots"] = _dots_from_fixed_days(1, od)
            for d in range(7):
                day_loads[d] += t["dots"][d]
        else:
            t["_count"] = 1
            free_sw.append(t)
    _schedule_periodic_global(free_sw, day_loads)

    sub_weekly_not_due = [t for t in all_tasks if t["freq"] < 1 and not t["is_due"]]
    for t in sub_weekly_not_due:
        t["dots"] = [0] * 7

    # Build area-grouped output
    plans = []
    for key, area in areas.items():
        plan = {
            "key": key,
            "name": area.get("name", key),
            "week_key": wk,
            "week_start": monday.isoformat(),
            "tasks": [],
        }
        for t in all_tasks:
            if t["area_key"] == key:
                row = {
                    "name": t["name"],
                    "freq": t["freq"],
                    "dots": t["dots"],
                    "weight": t.get("weight", 1.0),
                }
                plan["tasks"].append(row)
        plans.append(plan)

    return plans
