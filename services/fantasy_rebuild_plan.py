"""
Auto-generate rebuild plan text and per-asset trade targets (FantasyCalc dynasty values).

Runs after each Sleeper sync; overwrites desired_upgrade / plan_target on the rebuild board.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from services import fantasycalc_client


def _horizon_note(years: int) -> str:
    y = max(1, min(7, int(years or 3)))
    return f"{y}-year window"


def _pick_rows_for_season_round(rows: list[dict], season: str, rnd: int) -> list[dict]:
    """FantasyCalc pick names like '2026 Pick 1.01'. Match season + first-round digit group."""
    out = []
    season = str(season)
    for row in rows:
        pl = row.get("player") or {}
        if pl.get("position") != "PICK":
            continue
        name = (pl.get("name") or "").strip()
        m = re.match(r"^(\d{4})\s+Pick\s+(\d+)\.(\d+)", name)
        if not m:
            continue
        if m.group(1) != season:
            continue
        if int(m.group(2)) != rnd:
            continue
        out.append(row)
    return out


def _median_pick_value(rows: list[dict]) -> float | None:
    vals = []
    for row in rows:
        try:
            vals.append(float(row.get("value") or 0))
        except (TypeError, ValueError):
            pass
    if not vals:
        return None
    vals.sort()
    return vals[len(vals) // 2]


def _find_player_upgrade(
    my_id: str,
    vmap: dict[str, dict],
    horizon_years: int,
) -> tuple[str, str]:
    """
    Returns (plan_target_name, one_line_rationale).
    Avoids "swap young for slightly younger" noise: young QBs/skill often default to KEEP unless
    a clear tier-up (higher value) or materially younger elite appears.
    """
    me = vmap.get(str(my_id))
    if not me:
        return ("(no value data — sync again)", "FantasyCalc has no value for this player yet.")

    my_pos = (me.get("pos") or "").upper()
    my_val = float(me.get("value") or 0)
    my_age = me.get("age")
    try:
        my_age_f = float(my_age) if my_age is not None else None
    except (TypeError, ValueError):
        my_age_f = None

    my_name = me.get("name") or str(my_id)
    h = _horizon_note(horizon_years)

    def _young_cornerstone() -> bool:
        """Sophomore / young QB or very young skill — default hold, not lateral swap."""
        if my_pos == "QB" and my_age_f is not None and my_age_f <= 26.0:
            return True
        if my_pos in ("RB", "WR", "TE") and my_age_f is not None and my_age_f <= 23.5:
            return True
        return False

    # Positions we try to match (superflex: QB counts)
    pos_ok = {my_pos} if my_pos else set()
    if my_pos in ("RB", "WR", "TE"):
        pos_ok.add("FLEX")
    if not pos_ok:
        pos_ok = {"QB", "RB", "WR", "TE"}

    def _candidate_allowed(info: dict, val: float, age_f: float | None) -> bool:
        """Stricter when we're already holding youth — need real upgrade, not Cam-for-Cam."""
        if not _young_cornerstone():
            return my_val <= 0 or (0.72 <= val / my_val <= 1.35)
        # Young cornerstone: only suggest if clearly better tier OR much younger + not downgraded
        if my_val <= 0:
            return False
        ratio = val / my_val
        if ratio >= 1.18:
            return True
        if age_f is not None and my_age_f is not None:
            if (my_age_f - age_f) >= 2.5 and ratio >= 0.92:
                return True
        return False

    candidates: list[tuple[float, float, str, str]] = []
    for sid, info in vmap.items():
        if sid == str(my_id):
            continue
        pos = (info.get("pos") or "").upper()
        if pos not in pos_ok and my_pos and pos != my_pos:
            continue
        try:
            val = float(info.get("value") or 0)
        except (TypeError, ValueError):
            continue
        if val < 400:
            continue
        age = info.get("age")
        try:
            age_f = float(age) if age is not None else None
        except (TypeError, ValueError):
            age_f = None
        if not _candidate_allowed(info, val, age_f):
            continue
        youth = 0.0
        if my_age_f is not None and age_f is not None:
            youth = my_age_f - age_f
        elif age_f is not None:
            youth = 28.0 - age_f
        name = info.get("name") or sid
        candidates.append((youth, val, sid, name))

    if _young_cornerstone() and not candidates:
        return (
            "KEEP — young build-around piece",
            f"{my_name} is young enough to anchor a {h} window; do not lateral for a similar-age profile. "
            "Only move for a clear tier-up or a package that improves the rest of the roster.",
        )

    if not candidates:
        if my_val < 1200:
            return (
                "Add draft capital or package up",
                f"{my_name} is lower tier — target a {h} upside piece by attaching picks or pairing with another asset.",
            )
        return (
            "Consolidate or buy 2027/2028 capital",
            f"Few 1:1 comps in band — pivot to acquiring extra 1sts/2nds or a younger profile in {h}.",
        )

    # Prefer higher tier (value), then youth
    candidates.sort(key=lambda x: (-x[1], -x[0]))
    _, _, _, target_name = candidates[0]
    reason = (
        f"Rebuild ({h}): only showing swaps that look like a real upgrade on paper at {my_pos or 'this spot'} "
        f"(not a same-tier age shuffle). Confirm in your league before offering."
    )
    return (target_name, reason)


def _pick_plan_line(
    season: str,
    rnd: int,
    median_val: float | None,
    horizon_years: int,
    current_season: int,
) -> tuple[str, str]:
    """
    Return (plan_target, rationale) for a draft pick. Gives clearer keep-vs-trade
    advice for the upcoming rookie draft (especially early 1sts).
    """
    h = _horizon_note(horizon_years)
    try:
        season_i = int(season)
    except (TypeError, ValueError):
        season_i = 0
    is_upcoming = season_i == current_season

    if is_upcoming and rnd == 1:
        tier = (
            f" Median dynasty value for a round-1 pick this year is ~{median_val:.0f} in FantasyCalc."
            if median_val is not None else ""
        )
        target = f"Decide NOW: hit on rookie vs. trade pre-draft"
        rationale = (
            "Rookie draft is imminent. Two paths — pick one this week:"
            "\n  • KEEP: spend the pick on a top-of-class WR/RB or QB (your 1.01/1.02 slot supports this)."
            "\n  • TRADE PRE-DRAFT: convert the pick into an established young cornerstone (WR1/RB1/QB1) "
            "or bundle with another asset to consolidate up."
            f"{tier} Shop the league now while pick value peaks."
        )
        return (target, rationale)

    if is_upcoming and rnd == 2:
        target = f"{season} R2 — rookie flier or trade filler"
        rationale = (
            "Late-1/early-2 rookie tier is noisy. Either use it on a developmental WR/RB you like, "
            "or attach to a 1st to jump tiers in the upcoming draft / pre-draft trade."
        )
        return (target, rationale)

    tier = ""
    if median_val is not None:
        tier = f" Rough median dynasty value for this round slot in FantasyCalc: ~{median_val:.0f}."
    target = f"{season} R{rnd} — deploy as trade capital"
    rationale = (
        f"{tier} In a {h} rebuild, prioritize moving this into proven youth or earlier 1sts "
        f"(especially {season_i + 1 if season_i else '+1'}/+2 picks) rather than holding to the draft unless you love the class."
    )
    return (target, rationale)


def generate_rebuild_plan(state: dict) -> dict:
    """
    Mutate and return state with:
    - plan.rebuild_plan_doc, plan.rebuild_plan_generated_at
    - rebuild_board.assets[*].plan_target, plan_rationale, desired_upgrade (auto text)
    """
    snap = state.get("cached_snapshot")
    if not isinstance(snap, dict):
        return state

    settings = state.get("settings") or {}
    plan = state.setdefault("plan", {})
    horizon = int(plan.get("rebuild_horizon_years") or 3)
    horizon = max(1, min(7, horizon))

    num_qbs = int(settings.get("valuation_num_qbs") or 2)
    num_teams = int(settings.get("valuation_num_teams") or 12)
    ppr = float(settings.get("valuation_ppr") or 1.0)

    rows, warn = fantasycalc_client.fetch_dynasty_values(
        num_qbs=num_qbs, num_teams=num_teams, ppr=ppr
    )
    if not rows:
        plan["rebuild_plan_doc"] = (
            "Could not load FantasyCalc values to generate targets. "
            + (warn or "Check network and sync again.")
        )
        plan["rebuild_plan_generated_at"] = datetime.now(timezone.utc).isoformat()
        return state

    vmap = fantasycalc_client.values_by_sleeper_id(rows)
    board = state.setdefault("rebuild_board", {})
    assets = board.setdefault("assets", {})
    order = board.get("order") or []

    lines: list[str] = []
    lines.append(f"DYNASTY REBUILD PLAN ({_horizon_note(horizon).upper()})")
    lines.append("")
    lines.append(
        "Auto-generated from your Sleeper roster + FantasyCalc dynasty values. "
        "Use as a living trade script; confirm with Dynasty Calc / league context."
    )
    if warn:
        lines.append("")
        lines.append(f"Note: {warn}")
    lines.append("")

    try:
        current_season = int(settings.get("season") or datetime.now(timezone.utc).year)
    except (TypeError, ValueError):
        current_season = datetime.now(timezone.utc).year

    def _apply_auto(ast: dict, target: str, rationale: str, auto_text: str):
        """Write auto plan fields, preserving any user-edited desired_upgrade."""
        ast["plan_target"] = target
        ast["plan_rationale"] = rationale
        prev_auto = str(ast.get("_auto_desired_upgrade") or "")
        prev_desired = str(ast.get("desired_upgrade") or "")
        user_edited = prev_desired and prev_desired != prev_auto
        if not user_edited:
            ast["desired_upgrade"] = auto_text
        ast["_auto_desired_upgrade"] = auto_text

    for aid in order:
        ast = assets.get(aid)
        if not isinstance(ast, dict):
            continue
        kind = ast.get("kind")
        if kind == "player":
            pid = str(ast.get("player_id") or "")
            tgt, why = _find_player_upgrade(pid, vmap, horizon)
            auto_text = f"Target: {tgt}. {why}"
            _apply_auto(ast, tgt, why, auto_text)
            group = ast.get("group") or ""
            slot = ast.get("slot") or ""
            label = f"{group}" + (f" ({slot})" if slot else "")
            lines.append(f"{label.upper()}")
            lines.append(f"  Player ID: {pid}")
            lines.append(f"  Aim: {auto_text}")
            lines.append("")
        elif kind == "pick":
            pk = str(ast.get("pick_key") or "")
            label = str(ast.get("label") or pk)
            season = ""
            rnd = 0
            m = re.match(r"^(\d{4})-r(\d+)-", pk)
            if m:
                season, rnd = m.group(1), int(m.group(2))
            prs = _pick_rows_for_season_round(rows, season, rnd) if season else []
            med = _median_pick_value(prs) if prs else None
            tgt, why = _pick_plan_line(season, rnd, med, horizon, current_season)
            auto_text = f"{tgt}. {why}"
            _apply_auto(ast, tgt, why, auto_text)
            lines.append(f"DRAFT PICK: {label}")
            lines.append(f"  Aim: {auto_text}")
            lines.append("")

    doc = "\n".join(lines).strip()
    plan["rebuild_plan_doc"] = doc
    plan["rebuild_plan_generated_at"] = datetime.now(timezone.utc).isoformat()
    return state
