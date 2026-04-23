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


# Slot → list of eligible FantasyCalc positions (in priority order). Anything not
# in this map falls back to the slot name itself.
_SLOT_ELIGIBLE: dict[str, tuple[str, ...]] = {
    "QB": ("QB",),
    "RB": ("RB",),
    "WR": ("WR",),
    "TE": ("TE",),
    "FLEX": ("RB", "WR", "TE"),
    "WRRB_FLEX": ("RB", "WR"),
    "REC_FLEX": ("WR", "TE"),
    "SUPER_FLEX": ("QB", "RB", "WR", "TE"),
    "SUPERFLEX": ("QB", "RB", "WR", "TE"),
    "SFLEX": ("QB", "RB", "WR", "TE"),
    "K": ("K",),
    "DEF": ("DEF",),
    "DST": ("DEF",),
    "IDP_FLEX": ("DL", "LB", "DB"),
    "LB": ("LB",),
    "DL": ("DL",),
    "DB": ("DB",),
}

_STARTER_SLOTS = {
    "QB", "RB", "WR", "TE", "FLEX", "WRRB_FLEX", "REC_FLEX",
    "SUPER_FLEX", "SUPERFLEX", "SFLEX",
}


def _slot_display(slot: str) -> str:
    """Turn raw Sleeper slot keys into human labels."""
    s = (slot or "").upper()
    return {
        "SUPER_FLEX": "SFLEX",
        "SUPERFLEX": "SFLEX",
        "WRRB_FLEX": "W/R",
        "REC_FLEX": "W/T",
    }.get(s, s)


def _positional_tiers(vmap: dict[str, dict]) -> dict[str, dict]:
    """
    Compute elite/solid/adequate thresholds per FantasyCalc position using the
    current dataset. Returns {pos: {"elite": v, "solid": v, "adequate": v}}.
    """
    per_pos: dict[str, list[float]] = {}
    for info in vmap.values():
        pos = (info.get("pos") or "").upper()
        if pos not in ("QB", "RB", "WR", "TE"):
            continue
        try:
            val = float(info.get("value") or 0)
        except (TypeError, ValueError):
            continue
        if val <= 0:
            continue
        per_pos.setdefault(pos, []).append(val)
    out: dict[str, dict] = {}
    for pos, vals in per_pos.items():
        vals.sort(reverse=True)
        # Rough league-wide starter demand in a 12-team superflex:
        # QB ~24 starters (12 QB + 12 SFlex), RB/WR ~24-36, TE ~12.
        n = len(vals)
        def _at(i: int) -> float:
            i = max(0, min(n - 1, i))
            return vals[i]
        if pos == "QB":
            out[pos] = {
                "elite": _at(5),       # top-6 QBs = elite
                "solid": _at(15),      # ~QB16
                "adequate": _at(27),   # last startable in superflex
            }
        elif pos == "RB":
            out[pos] = {
                "elite": _at(7),
                "solid": _at(17),
                "adequate": _at(29),
            }
        elif pos == "WR":
            out[pos] = {
                "elite": _at(11),
                "solid": _at(23),
                "adequate": _at(41),
            }
        elif pos == "TE":
            out[pos] = {
                "elite": _at(3),
                "solid": _at(7),
                "adequate": _at(13),
            }
    return out


def _tier_for(value: float, pos: str, tiers: dict[str, dict]) -> str:
    t = tiers.get((pos or "").upper())
    if not t:
        return "unknown"
    if value >= t["elite"]:
        return "elite"
    if value >= t["solid"]:
        return "solid"
    if value >= t["adequate"]:
        return "adequate"
    return "weak"


def _owned_player_ids(snapshot: dict) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for row in snapshot.get("starters") or []:
        if row.get("empty"):
            continue
        pl = row.get("player") or {}
        pid = pl.get("id")
        if pid and str(pid) not in seen:
            seen.add(str(pid))
            ids.append(str(pid))
    for field in ("bench", "reserve", "taxi"):
        for pl in snapshot.get(field) or []:
            pid = pl.get("id")
            if pid and str(pid) not in seen:
                seen.add(str(pid))
                ids.append(str(pid))
    return ids


def _player_meta_from_snapshot(pid: str, snapshot: dict) -> dict | None:
    sid = str(pid)
    for row in snapshot.get("starters") or []:
        pl = row.get("player") or {}
        if pl and str(pl.get("id", "")) == sid:
            return pl
    for field in ("bench", "reserve", "taxi"):
        for pl in snapshot.get(field) or []:
            if pl and str(pl.get("id", "")) == sid:
                return pl
    return None


def _years_exp_from_fcrow(row: dict) -> int | None:
    pl = row.get("player") or {}
    ye = pl.get("yearsExp")
    if ye is None:
        return None
    try:
        return int(ye)
    except (TypeError, ValueError):
        return None


def _rookie_qb_wr_rb_te_from_rows(
    rows: list[dict], limit: int = 6
) -> list[dict]:
    """
    Rookies (yearsExp == 0) at QB/RB/WR/TE, highest value first, for model suggestions.
    """
    out: list[dict] = []
    cands: list[tuple[float, str, str, str]] = []
    for row in rows:
        pl = row.get("player") or {}
        pos = (pl.get("position") or "").upper()
        if pos not in ("QB", "RB", "WR", "TE"):
            continue
        if _years_exp_from_fcrow(row) != 0:
            continue
        sid = pl.get("sleeperId")
        if not sid:
            continue
        try:
            val = float(row.get("value") or 0)
        except (TypeError, ValueError):
            val = 0.0
        name = pl.get("name") or str(sid)
        cands.append((-val, str(sid), name, pos))
    cands.sort()
    for _neg, sid, name, pos in cands[: max(0, int(limit or 0))]:
        out.append({
            "player_id": sid,
            "name": name,
            "pos": pos,
        })
    return out


def _fc_name_for_sleeper_pick(
    season: str, display_slot: str | None, rnum: int, pick_in_round: int
) -> str:
    if display_slot and re.match(r"^\d+\.\d{1,2}$", display_slot.strip()):
        return f"{str(season).strip()} Pick {display_slot.strip()}"
    if rnum >= 1 and pick_in_round >= 1:
        return f"{str(season).strip()} Pick {rnum}.{pick_in_round:02d}"
    return ""


def _rookie_suggestions_for_pick(
    rows: list[dict],
    season: str,
    display_slot: str | None,
) -> tuple[dict | None, list[dict], str, str, str | None]:
    """
    (top_rookie, alternates(2), action_line, model_note, fc_error)

    Binds 1.01/1.02 in FantasyCalc to a pick token name when possible; otherwise
    uses top model rookie as a generic early-R1 stand-in.
    """
    season = str(season).strip()
    pslot = (display_slot or "").strip() if display_slot else ""
    p_in_r = 1
    m = re.match(r"^(\d+)\.(\d{1,2})$", pslot)
    if m:
        rnd_x = int(m.group(1))
        p_in_r = int(m.group(2))
    else:
        rnd_x = 1

    roster = _rookie_qb_wr_rb_te_from_rows(rows, limit=8)
    top0 = roster[0] if roster else None
    alts = roster[1:3] if len(roster) > 1 else []
    if not top0:
        return (
            None, [], "No rookie rows in the model — try syncing after FantasyCalc updates.",
            "FantasyCalc has no 0-exp QB/RB/WR/TE rows.", None,
        )

    fc_lbl = _fc_name_for_sleeper_pick(season, pslot, rnd_x, p_in_r)
    matched_val: float | None = None
    for row in rows:
        pl = row.get("player") or {}
        if pl.get("position") != "PICK":
            continue
        n = (pl.get("name") or "").strip()
        if not fc_lbl or n != fc_lbl:
            continue
        try:
            matched_val = float(row.get("value") or 0)
        except (TypeError, ValueError):
            matched_val = 0.0
        break

    if fc_lbl and matched_val is not None:
        note = (
            f"FantasyCalc’s pick token {fc_lbl} is the closest match to your {pslot} slot. "
            f"Top 0-year prospect in the data right now: {top0.get('name')} — often aligned with 1.01, but check your own ranks before draft day."
        )
    elif rnd_x <= 1:
        note = (
            f"Model leans {top0.get('name')} ({top0.get('pos')}) among 0-year QB/RB/WR/TE in FantasyCalc — use as a planning stand-in, not a lock."
        )
    else:
        note = (
            f"Later pick — model highlights {top0.get('name')} as a reference rookie; your board thins a lot in R{rnd_x}."
        )

    aline = f"Leaning draft: {top0.get('name')} — compare to {', '.join(x.get('name') for x in alts) if alts else 'the rest of your list'}."
    return (top0, alts, aline, note, fc_lbl or None)


def _extra_pool_for_assumptions(
    state: dict, vmap: dict[str, dict]
) -> list[dict]:
    plan = (state.get("plan") or {}) if isinstance(state.get("plan"), dict) else {}
    if not plan.get("project_rookies_into_lineup"):
        return []
    raw = plan.get("assumed_rookies")
    if not isinstance(raw, dict) or not raw:
        return []
    snap = state.get("cached_snapshot")
    if not isinstance(snap, dict):
        return []
    out: list[dict] = []
    board = (state.get("rebuild_board") or {}).get("assets") or {}
    for aid, entry in raw.items():
        if not isinstance(aid, str) or not aid.startswith("k-"):
            continue
        ast = board.get(aid)
        if not isinstance(ast, dict) or ast.get("kind") != "pick":
            continue
        e = entry if isinstance(entry, dict) else {}
        pid = str((e or {}).get("sleeper_player_id") or "").strip()
        if not pid or pid == "0":
            continue
        info = vmap.get(pid) or {}
        pos = (info.get("pos") or "").upper()
        try:
            val = float(info.get("value") or 0)
        except (TypeError, ValueError):
            val = 0.0
        if not pos:
            continue
        name = info.get("name") or f"Player {pid}"
        out.append({
            "id": pid, "pos": pos, "value": val, "name": name, "team": "",
            "assumed": True, "assumed_from_pick_aid": aid,
        })
    return out


def apply_lineup_projection(
    state: dict,
    vmap: dict[str, dict] | None = None,
    tiers: dict[str, dict] | None = None,
) -> dict:
    """
    Recompute `best_lineup_with_assumptions` from plan.assumed_rookies.
    Pass vmap + tiers from generate_rebuild_plan to avoid a second values fetch.
    """
    snap = state.get("cached_snapshot")
    if not isinstance(snap, dict):
        return state
    plan = (state.get("plan") or {}) if isinstance(state.get("plan"), dict) else {}
    if not plan.get("project_rookies_into_lineup") or not isinstance(
        (plan.get("assumed_rookies") or {}), dict
    ) or not plan.get("assumed_rookies"):
        state["best_lineup_with_assumptions"] = None
        state["best_lineup_with_assumptions_at"] = None
        return state
    if vmap is None or tiers is None:
        s = (state.get("settings") or {})
        num_qbs = int(s.get("valuation_num_qbs") or 2)
        num_teams = int(s.get("valuation_num_teams") or 12)
        ppr = float(s.get("valuation_ppr") or 1.0)
        rows, _ = fantasycalc_client.fetch_dynasty_values(
            num_qbs=num_qbs, num_teams=num_teams, ppr=ppr
        )
        if not rows:
            state["best_lineup_with_assumptions"] = None
            state["best_lineup_with_assumptions_at"] = None
            return state
        vmap = fantasycalc_client.values_by_sleeper_id(rows)
        tiers = _positional_tiers(vmap)
    extra = _extra_pool_for_assumptions(state, vmap)  # type: ignore
    if not extra:
        state["best_lineup_with_assumptions"] = None
        state["best_lineup_with_assumptions_at"] = None
        return state
    state["best_lineup_with_assumptions"] = build_best_lineup(
        snap, vmap, tiers, extra_pool=extra
    )
    state["best_lineup_with_assumptions_at"] = datetime.now(timezone.utc).isoformat()
    return state


def build_best_lineup(
    snapshot: dict,
    vmap: dict[str, dict],
    tiers: dict[str, dict],
    extra_pool: list[dict] | None = None,
) -> dict:
    """
    Greedy best-lineup builder: for each starting slot in league.roster_positions,
    pick the highest-value eligible owned player not yet assigned.

    Returns {"slots": [ {slot, label, player_id, name, pos, team, value, tier, is_weak, is_empty} ], ... }.
    """
    league = snapshot.get("league") or {}
    roster_positions = league.get("roster_positions") or []

    owned = _owned_player_ids(snapshot)
    # Seed candidate pool with (pid, pos, value, name, team) rows.
    pool: list[dict] = []
    for pid in owned:
        info = vmap.get(pid) or {}
        pos = (info.get("pos") or "").upper()
        try:
            val = float(info.get("value") or 0)
        except (TypeError, ValueError):
            val = 0.0
        meta = _player_meta_from_snapshot(pid, snapshot) or {}
        name = info.get("name") or meta.get("name") or f"Player {pid}"
        team = meta.get("team") or ""
        if not pos:
            pos = (meta.get("pos") or "").upper()
        pool.append({
            "id": pid, "pos": pos, "value": val, "name": name, "team": team,
        })

    seen = {c["id"] for c in pool}
    for c in extra_pool or []:
        if not c or c.get("id") in seen:
            continue
        seen.add(c["id"])
        pool.append({
            "id": c["id"],
            "pos": c.get("pos") or "",
            "value": float(c.get("value") or 0),
            "name": c.get("name") or f"Player {c.get('id')}",
            "team": c.get("team") or "",
            "assumed": c.get("assumed"),
            "assumed_from_pick_aid": c.get("assumed_from_pick_aid"),
        })

    used: set[str] = set()
    slots_out: list[dict] = []

    for slot_raw in roster_positions:
        slot = (slot_raw or "").upper()
        if slot in ("BN", "IR", "TAXI"):
            continue
        if slot not in _STARTER_SLOTS and slot not in _SLOT_ELIGIBLE:
            # Non-offensive starter slots (K/DEF/IDP) — skip for weakness analysis
            # but still show them so the top card feels complete.
            if slot not in ("K", "DEF", "DST"):
                continue
        eligible = _SLOT_ELIGIBLE.get(slot, (slot,))
        # Pick highest value eligible not yet used
        best = None
        for cand in pool:
            if cand["id"] in used:
                continue
            if cand["pos"] not in eligible:
                continue
            if best is None or cand["value"] > best["value"]:
                best = cand
        if best is None:
            slots_out.append({
                "slot": slot_raw,
                "label": _slot_display(slot),
                "is_empty": True,
                "is_weak": True,
                "tier": "empty",
                "player_id": None,
                "name": "",
                "pos": "",
                "team": "",
                "value": 0,
                "is_assumed": False,
            })
            continue
        used.add(best["id"])
        tier = _tier_for(best["value"], best["pos"], tiers)
        is_weak = tier in ("weak", "unknown", "empty")
        slot_row = {
            "slot": slot_raw,
            "label": _slot_display(slot),
            "is_empty": False,
            "is_weak": is_weak,
            "tier": tier,
            "player_id": best["id"],
            "name": best["name"],
            "pos": best["pos"],
            "team": best["team"],
            "value": best["value"],
        }
        if best.get("assumed"):
            slot_row["is_assumed"] = True
            slot_row["assumed_from_pick_aid"] = best.get("assumed_from_pick_aid")
        else:
            slot_row["is_assumed"] = False
        slots_out.append(slot_row)

    # Also surface top unused bench asset (for trade or promote context)
    bench_leftovers = [c for c in pool if c["id"] not in used]
    bench_leftovers.sort(key=lambda c: -c["value"])

    return {
        "slots": slots_out,
        "bench_top": [
            {
                "player_id": c["id"], "name": c["name"], "pos": c["pos"],
                "team": c["team"], "value": c["value"],
                "tier": _tier_for(c["value"], c["pos"], tiers),
            }
            for c in bench_leftovers[:5]
        ],
    }


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


def _parse_pick_slot(name: str) -> tuple[int, int] | None:
    """Return (round, pick_in_round) from FantasyCalc pick name '2026 Pick 1.01'."""
    m = re.match(r"^(\d{4})\s+Pick\s+(\d+)\.(\d+)", (name or "").strip())
    if not m:
        return None
    return int(m.group(2)), int(m.group(3))


def _top_rookie_pick_names(rows: list[dict], season: str, rnd: int, limit: int = 6) -> list[str]:
    """Highest-valued rookie pick rows for a season/round (by FantasyCalc)."""
    season = str(season)
    cands: list[tuple[float, str]] = []
    for row in rows:
        pl = row.get("player") or {}
        if pl.get("position") != "PICK":
            continue
        name = (pl.get("name") or "").strip()
        slot = _parse_pick_slot(name)
        if not slot or slot[0] != rnd:
            continue
        if not name.startswith(season):
            continue
        try:
            val = float(row.get("value") or 0)
        except (TypeError, ValueError):
            val = 0.0
        cands.append((val, name))
    cands.sort(key=lambda x: -x[0])
    return [n for _, n in cands[:limit]]


def _draft_capital_summary(snapshot: dict, season: str) -> str:
    picks = snapshot.get("draft_picks") or []
    if not picks:
        return ""
    by_r: dict[int, int] = {}
    for p in picks:
        if str(p.get("season") or "") != season:
            continue
        try:
            r = int(p.get("round") or 0)
        except (TypeError, ValueError):
            r = 0
        if r <= 0:
            continue
        by_r[r] = by_r.get(r, 0) + 1
    if not by_r:
        return ""
    parts = [f"{by_r[r]}×R{r}" for r in sorted(by_r)]
    return f"{season} capital: " + ", ".join(parts)


def _target_depth_by_pos(num_qbs: int) -> dict[str, int]:
    """Rough roster targets for a rebuild (offense only)."""
    qb_t = 4 if num_qbs >= 2 else 2
    return {"QB": qb_t, "RB": 4, "WR": 5, "TE": 2}


def _weak_starter_counts(best_lineup: dict | None) -> dict[str, int]:
    out = {"QB": 0, "RB": 0, "WR": 0, "TE": 0}
    if not best_lineup or not isinstance(best_lineup, dict):
        return out
    for s in best_lineup.get("slots") or []:
        if not isinstance(s, dict):
            continue
        if not s.get("is_weak") and not s.get("is_empty"):
            continue
        pos = (s.get("pos") or "").upper()
        if pos in out:
            out[pos] += 1
    return out


def _count_owned_by_pos(snapshot: dict, vmap: dict[str, dict]) -> dict[str, int]:
    counts = {"QB": 0, "RB": 0, "WR": 0, "TE": 0}
    for pid in _owned_player_ids(snapshot):
        info = vmap.get(str(pid)) or {}
        pos = (info.get("pos") or "").upper()
        if pos in counts:
            counts[pos] += 1
        else:
            meta = _player_meta_from_snapshot(str(pid), snapshot) or {}
            p2 = (meta.get("pos") or "").upper()
            if p2 in counts:
                counts[p2] += 1
    return counts


def _best_owned_at_pos(snapshot: dict, vmap: dict[str, dict], pos: str, tiers: dict[str, dict]) -> dict | None:
    pos = pos.upper()
    best = None
    best_val = -1.0
    for pid in _owned_player_ids(snapshot):
        info = vmap.get(str(pid)) or {}
        meta = _player_meta_from_snapshot(str(pid), snapshot) or {}
        p = (info.get("pos") or "").upper()
        if p != pos:
            p = (meta.get("pos") or "").upper()
        if p != pos:
            continue
        try:
            val = float(info.get("value") or 0)
        except (TypeError, ValueError):
            val = 0.0
        if val > best_val:
            best_val = val
            name = info.get("name") or meta.get("name") or f"Player {pid}"
            best = {"name": name, "value": val, "tier": _tier_for(val, pos, tiers)}
    return best


def build_position_strategy(
    snapshot: dict,
    vmap: dict[str, dict],
    tiers: dict[str, dict],
    best_lineup: dict | None,
    settings: dict,
    horizon_years: int,
) -> list[dict]:
    """
    Per-position rebuild guidance: roster depth vs targets, weak starters,
    and how to use picks (trade vs draft) without locking to one player.
    """
    h = _horizon_note(horizon_years)
    try:
        current_season = str(int(settings.get("season") or datetime.now(timezone.utc).year))
    except (TypeError, ValueError):
        current_season = str(datetime.now(timezone.utc).year)
    num_qbs = int(settings.get("valuation_num_qbs") or 2)
    targets = _target_depth_by_pos(num_qbs)
    owned = _count_owned_by_pos(snapshot, vmap)
    weak_n = _weak_starter_counts(best_lineup)
    cap = _draft_capital_summary(snapshot, current_season)
    pos_order = ("QB", "RB", "WR", "TE")
    out: list[dict] = []

    for pos in pos_order:
        tgt = targets[pos]
        n = owned.get(pos, 0)
        gap = max(0, tgt - n)
        surplus = max(0, n - tgt)
        weak = weak_n.get(pos, 0)
        best = _best_owned_at_pos(snapshot, vmap, pos, tiers)

        lines: list[str] = []
        if num_qbs >= 2 and pos == "QB":
            lines.append(
                "Superflex: treat a second startable QB as a roster pillar, not a bench luxury."
            )
        if weak > 0:
            lines.append(
                f"{weak} projected starter slot(s) at {pos} look thin in the best-lineup view — "
                f"prioritize real starts over depth at other spots until this stabilizes."
            )
        if gap >= 2:
            lines.append(
                f"Depth target ~{tgt} at {pos}; you are short by about {gap}. "
                f"Use early capital (1sts / young studs) here before padding elsewhere."
            )
        elif gap == 1:
            lines.append(
                f"One credible {pos} away from a healthy rebuild core — "
                f"trade a pick package or a surplus position for a starter, or draft the best {pos} fit."
            )
        elif surplus >= 2 and (best is None or (best.get("tier") or "") in ("weak", "adequate", "unknown")):
            lines.append(
                f"You have extra {pos} bodies but no clear anchor — "
                "consolidate: package 2-for-1 or attach a pick to climb a tier instead of holding six middling names."
            )
        elif surplus >= 1 and weak == 0 and best and (best.get("tier") or "") in ("elite", "solid"):
            lines.append(
                f"Strong {pos} anchor — fine to treat extras as trade collateral or taxi cuts, "
                "not all as long-term keeps."
            )
        else:
            lines.append(
                f"About {n} rostered vs ~{tgt} target — balance draft hits with trades using your {h} lens."
            )

        if cap:
            lines.append(cap + ". Early 1sts are for premium profiles (QB/RB/WR1 types), not depth.")

        out.append({
            "pos": pos,
            "label": pos + (" / SFLEX" if pos == "QB" and num_qbs >= 2 else ""),
            "owned": n,
            "target_depth": tgt,
            "gap": gap,
            "surplus": surplus,
            "weak_starters": weak,
            "best_owned": best,
            "lines": lines,
        })
    return out


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
    tiers = _positional_tiers(vmap)
    state["best_lineup"] = build_best_lineup(snap, vmap, tiers)
    state["best_lineup_generated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        season_for_board = int(settings.get("season") or datetime.now(timezone.utc).year)
    except (TypeError, ValueError):
        season_for_board = datetime.now(timezone.utc).year
    season_board_str = str(season_for_board)
    r1_pick_names = _top_rookie_pick_names(rows, season_board_str, 1, limit=8)
    rookie_board_hint: str | None = None
    if r1_pick_names:
        sample = ", ".join(
            re.sub(r"^\d{4}\s+Pick\s+", "", nm) for nm in r1_pick_names[:6]
        )
        rookie_board_hint = (
            f"FantasyCalc's top-valued {season_board_str} R1 rookie slots (model board, not a must-draft): "
            f"{sample}. Compare to your ranks; if the model loves one name you do not, shop the pick pre-draft."
        )
    state["rookie_board_hint"] = rookie_board_hint
    state["position_strategy"] = build_position_strategy(
        snap, vmap, tiers, state["best_lineup"], settings, horizon
    )
    state["position_strategy_generated_at"] = datetime.now(timezone.utc).isoformat()

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

    lines.append("BY POSITION — depth, bench vs trade, draft capital")
    lines.append("")
    if rookie_board_hint:
        lines.append(rookie_board_hint)
        lines.append("")
    for row in state.get("position_strategy") or []:
        if not isinstance(row, dict):
            continue
        label = row.get("label") or row.get("pos") or ""
        bo = row.get("best_owned") if isinstance(row.get("best_owned"), dict) else None
        top = ""
        if bo and bo.get("name"):
            top = f" Top on roster: {bo.get('name')}"
            if bo.get("tier"):
                top += f" ({bo.get('tier')})"
        lines.append(
            f"{label}: {row.get('owned', 0)} rostered vs ~{row.get('target_depth', 0)} target depth.{top}"
        )
        for ln in row.get("lines") or []:
            lines.append(f"  • {ln}")
        lines.append("")

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
            # Model rookie board + what this pick likely targets (Sleeper 1.01 + FantasyCalc)
            ds = str(ast.get("display_slot") or "").strip()
            top_r, alts, aline, mnote, fc_tok = _rookie_suggestions_for_pick(
                rows, season, ds if ds else None
            )
            ast["model_suggested_rookie"] = top_r
            ast["model_rookie_alternates"] = alts
            ast["model_action_line"] = aline
            ast["model_note"] = mnote
            if fc_tok:
                ast["model_fc_pick_name"] = fc_tok
            lines.append(f"DRAFT PICK: {label}")
            lines.append(f"  Aim: {auto_text}")
            if top_r and top_r.get("name"):
                an = " / ".join(x.get("name") for x in (alts or []) if x and x.get("name"))
                lines.append(
                    f"  Model rookie lean: {top_r.get('name')} ({top_r.get('pos')})"
                    + (f" (also watch {an})" if an else "")
                )
            if mnote:
                lines.append(f"  {mnote}")
            lines.append("")

    ar_map = (
        {k: v for k, v in (plan.get("assumed_rookies") or {}).items()}
        if isinstance(plan.get("assumed_rookies"), dict)
        else {}
    )
    for aid2 in order:
        ast2 = assets.get(aid2)
        if not isinstance(ast2, dict) or ast2.get("kind") != "pick":
            continue
        top_r2 = ast2.get("model_suggested_rookie")
        if not isinstance(top_r2, dict) or not top_r2.get("player_id"):
            continue
        try:
            prn = int(ast2.get("round") or 0)
        except (TypeError, ValueError):
            prn = 0
        ds2 = str(ast2.get("display_slot") or "").strip()
        # Default first-round early picks to the model's top rookie if user has not chosen
        if prn == 1 and (ds2 in ("1.01", "1.02", "") or not ds2):
            ex = ar_map.get(aid2) if isinstance(ar_map.get(aid2), dict) else None
            if not (ex and ex.get("sleeper_player_id")):
                ar_map[aid2] = {
                    "sleeper_player_id": str(top_r2.get("player_id") or "").strip(),
                    "name": str(top_r2.get("name") or "").strip(),
                    "source": "model_default",
                }
    if ar_map:
        plan["assumed_rookies"] = ar_map

    if not plan.get("project_rookies_into_lineup") and ar_map:
        plan["project_rookies_into_lineup"] = True

    apply_lineup_projection(state, vmap, tiers)

    doc = "\n".join(lines).strip()
    plan["rebuild_plan_doc"] = doc
    plan["rebuild_plan_generated_at"] = datetime.now(timezone.utc).isoformat()
    return state
