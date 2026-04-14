"""Weighted routine scores (scheduled + partial credit for early/extra dots).

Model
-----
- **Scheduled** dots (indices ``0 .. scheduled[day]-1``) count at full task weight
  toward both earned and possible.
- **Extra** dots on that day (the optional slot(s) when ``len(days[day]) > scheduled``)
  count at ``BONUS_CREDIT_RATIO`` (default 0.4)—so doing something early or off-plan
  helps, but not as much as hitting the plan.
- Scores stay in **0–100%** of (scheduled + bonus) capacity.

Carryover dots are part of ``scheduled``; if JSON ever has ``scheduled[d]`` longer than
``days[d]``, :func:`services.card_store._repair_task_grid_for_scheduled` extends rows
on load so fills count.
"""

from __future__ import annotations

from datetime import date

DAY_LABELS_SHORT = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
DAY_LABELS_LONG = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

# Credit for fills on unscheduled / extra slots (per unit of task weight).
BONUS_CREDIT_RATIO = 0.4


def task_weight(task: dict) -> float:
    try:
        w = float(task.get("weight", 1) or 1)
        return w if w > 0 else 1.0
    except (TypeError, ValueError):
        return 1.0


def _sched_int(sched: list, di: int) -> int:
    if di < 0 or di >= len(sched):
        return 0
    try:
        return max(0, int(sched[di]))
    except (TypeError, ValueError):
        return 0


def _aggregate_task_list(
    task_list: list[dict],
    day_idx: int | None,
    *,
    include_bonus: bool,
) -> tuple[float, float, float]:
    """
    Returns (earned, possible, scheduled_possible_only).

    When include_bonus is False, possible == scheduled_possible_only (bonus slots ignored).
    """
    earned = possible = 0.0
    sched_possible = 0.0
    r = BONUS_CREDIT_RATIO

    for task in task_list:
        w = task_weight(task)
        sched = list(task.get("scheduled") or [])
        while len(sched) < 7:
            sched.append(0)
        days = task.get("days") or []
        dis = range(7) if day_idx is None else [day_idx]
        for di in dis:
            if di < 0 or di > 6:
                continue
            sc = _sched_int(sched, di)
            row = days[di] if di < len(days) else []
            nrow = len(row)
            for doi in range(sc):
                sched_possible += w
                possible += w
                filled = bool(row[doi]) if doi < nrow else False
                if filled:
                    earned += w
            if include_bonus:
                for doi in range(sc, nrow):
                    bp = w * r
                    possible += bp
                    if row[doi]:
                        earned += bp

    return earned, possible, sched_possible


def _aggregate_cards(
    cards: dict,
    day_idx: int | None,
    *,
    include_bonus: bool,
) -> tuple[float, float, float]:
    e = p = s = 0.0
    for card in cards.values():
        e1, p1, s1 = _aggregate_task_list(
            card.get("tasks", []), day_idx, include_bonus=include_bonus
        )
        e += e1
        p += p1
        s += s1
        e2, p2, s2 = _aggregate_task_list(
            card.get("extra_tasks", []), day_idx, include_bonus=include_bonus
        )
        e += e2
        p += p2
        s += s2
    return e, p, s


def week_scheduled_weight_total(cards: dict) -> float:
    """Sum of task weights over all scheduled dots this week (no bonus slots)."""
    _, _, s = _aggregate_cards(cards, None, include_bonus=False)
    return s


def weighted_week_score(cards: dict) -> tuple[float, float, int | None]:
    earned, possible, _ = _aggregate_cards(cards, None, include_bonus=True)
    if possible <= 0:
        return 0.0, 0.0, None
    return earned, possible, int(round(earned / possible * 100))


def weighted_day_score(cards: dict, day_idx: int) -> tuple[float, float, int | None]:
    if day_idx < 0 or day_idx > 6:
        return 0.0, 0.0, None
    earned, possible, _ = _aggregate_cards(cards, day_idx, include_bonus=True)
    if possible <= 0:
        return 0.0, 0.0, None
    return earned, possible, int(round(earned / possible * 100))


def daily_breakdown_weighted(cards: dict) -> list[int | None]:
    out: list[int | None] = []
    for di in range(7):
        _, _, pct = weighted_day_score(cards, di)
        out.append(pct)
    return out


def week_day_summary(cards: dict) -> dict:
    row = daily_breakdown_weighted(cards)
    scored = [(i, p) for i, p in enumerate(row) if p is not None]
    out: dict = {
        "active_days": len(scored),
        "best_idx": None,
        "best_pct": None,
        "best_short": None,
        "low_idx": None,
        "low_pct": None,
        "low_short": None,
        "avg_pct": None,
    }
    if not scored:
        return out
    bi, bp = max(scored, key=lambda x: x[1])
    out["best_idx"] = bi
    out["best_pct"] = bp
    out["best_short"] = DAY_LABELS_SHORT[bi]
    li, lp = min(scored, key=lambda x: x[1])
    out["low_idx"] = li
    out["low_pct"] = lp
    out["low_short"] = DAY_LABELS_SHORT[li]
    out["avg_pct"] = int(round(sum(p for _, p in scored) / len(scored)))
    return out


def today_score_banner_context(cards: dict) -> dict:
    week_start = next((c.get("week_start") for c in cards.values()), None)
    idx = today_weekday_index(week_start) if week_start else None
    if idx is None:
        return {
            "cards_today_in_week": False,
            "cards_today_label": "",
            "cards_today_score_pct": None,
        }
    _, _, pct = weighted_day_score(cards, idx)
    return {
        "cards_today_in_week": True,
        "cards_today_label": DAY_LABELS_LONG[idx],
        "cards_today_score_pct": pct,
    }


def today_weekday_index(week_start_iso: str, today: date | None = None) -> int | None:
    if today is None:
        today = date.today()
    try:
        monday = date.fromisoformat(week_start_iso[:10])
    except ValueError:
        return None
    delta = (today - monday).days
    if 0 <= delta <= 6:
        return delta
    return None
