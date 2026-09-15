"""
Weekly results + FAAB pickup board for every Sleeper league on the account.

Uses last completed NFL week (display_week / week-1) and next-week projections.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import config
from services import sleeper_client


_SKILL = {"QB", "RB", "WR", "TE"}
_SIT = {"out", "ir", "pup", "suspended", "cov", "na", "dnr"}


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _i(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _team_label(users_by_id: dict[str, dict], owner_id: str, roster_id: Any) -> str:
    u = users_by_id.get(str(owner_id) or "") or {}
    meta = u.get("metadata") or {}
    if isinstance(meta, dict) and meta.get("team_name"):
        return str(meta["team_name"])
    return str(u.get("display_name") or f"Team {roster_id}")


def _player_meta(pid: str, players_map: dict | None) -> dict[str, Any]:
    p = (players_map or {}).get(str(pid)) if players_map else None
    if not isinstance(p, dict):
        p = {}
    fn = (p.get("first_name") or "").strip()
    ln = (p.get("last_name") or "").strip()
    name = (p.get("full_name") or "").strip() or f"{fn} {ln}".strip() or str(pid)
    return {
        "id": str(pid),
        "name": name,
        "pos": (p.get("position") or "").upper(),
        "team": p.get("team") or "",
        "years_exp": p.get("years_exp"),
        "age": p.get("age"),
        "injury": p.get("injury_status"),
        "status": p.get("status"),
    }


def score_with_settings(stat: dict | None, scoring: dict | None) -> float:
    """Apply a Sleeper league scoring_settings map to a stats/projections row."""
    if not stat or not scoring:
        return 0.0
    pts = 0.0
    for key, weight in scoring.items():
        if key not in stat:
            continue
        pts += _f(stat.get(key)) * _f(weight)
    return round(pts, 2)


def _is_sit(meta: dict) -> bool:
    inj = str(meta.get("injury") or "").strip().lower()
    st = str(meta.get("status") or "").strip().lower()
    return inj in _SIT or st in ("inactive", "injured_reserve")


def _youth_mult(meta: dict, dynasty: bool) -> float:
    if not dynasty:
        return 1.0
    ye = meta.get("years_exp")
    age = meta.get("age")
    try:
        ye_i = int(ye) if ye is not None else 99
    except (TypeError, ValueError):
        ye_i = 99
    try:
        age_f = float(age) if age is not None else None
    except (TypeError, ValueError):
        age_f = None
    if ye_i <= 1:
        return 1.35
    if ye_i <= 2:
        return 1.2
    if age_f is not None and age_f >= 32:
        return 0.2
    if age_f is not None and age_f >= 29:
        return 0.4
    return 0.85


def _completed_week(nfl: dict) -> tuple[int, int, str]:
    """
    Return (last_week, next_week, season).
    After Sunday, Sleeper's `week` is usually the upcoming week and
    `display_week` is the one that just finished.
    """
    season = str(nfl.get("season") or nfl.get("league_season") or datetime.now().year)
    week = _i(nfl.get("week"), 1)
    display = _i(nfl.get("display_week"), week)
    if display and display < week:
        last_week = max(1, display)
        next_week = max(last_week + 1, week)
    elif week <= 1:
        last_week, next_week = 1, 2
    else:
        last_week, next_week = week - 1, week
    return last_week, next_week, season


def _rostered_ids(rosters: list[dict]) -> set[str]:
    out: set[str] = set()
    for r in rosters:
        for field in ("players", "reserve", "taxi"):
            for pid in r.get(field) or []:
                if pid is not None:
                    out.add(str(pid))
    return out


def _bid_range(
    *,
    faab_left: int,
    dynasty: bool,
    urgency: float,
    waiver_pos: int,
    n_teams: int,
) -> tuple[int, int]:
    left = max(0, faab_left)
    if left <= 0:
        return (0, 0)
    if dynasty:
        cap = max(4, int(left * 0.12))
        high = int(3 + urgency * 12)
    else:
        cap = max(6, int(left * 0.30))
        high = int(6 + urgency * 22)
    # Late waiver priority has to bid up; early can shade down.
    if n_teams and waiver_pos >= max(8, n_teams - 3):
        high = int(high * 1.15)
    elif n_teams and waiver_pos <= 3:
        high = int(high * 0.85)
    high = max(1, min(left, cap, high))
    low = max(1, min(high, int(high * 0.6)))
    return (low, high)


def _pick_drop(
    my_players: list[dict],
    add_pos: str,
    dynasty: bool,
) -> dict | None:
    """Cheapest cut that is not a young cornerstone / only QB."""
    qbs = [p for p in my_players if p.get("pos") == "QB" and not p.get("on_taxi")]
    cands = []
    for p in my_players:
        if p.get("on_taxi") or p.get("on_ir"):
            continue
        if p.get("is_starter") and not _is_sit(p):
            continue
        if p.get("pos") == "QB" and len(qbs) <= (2 if dynasty else 1):
            continue
        if dynasty:
            ye = p.get("years_exp")
            try:
                if ye is not None and int(ye) <= 1 and _f(p.get("w1")) + _f(p.get("w2")) >= 8:
                    continue
            except (TypeError, ValueError):
                pass
        sit = 8 if _is_sit(p) else 0
        same = 2 if p.get("pos") == add_pos else 0
        production = _f(p.get("w1")) + 0.6 * _f(p.get("w2"))
        cands.append((sit, same, -production, p.get("id") or "", p))
    if not cands:
        return None
    cands.sort(key=lambda t: (t[0], t[1], t[2], t[3]), reverse=True)
    return cands[0][4]


def _build_league_week(
    league: dict,
    rosters: list[dict],
    users: list[dict],
    my_user_id: str,
    last_week: int,
    next_week: int,
    stats: dict,
    proj: dict,
    trending: dict[str, int],
    players_map: dict | None,
) -> dict[str, Any] | None:
    my = next((r for r in rosters if str(r.get("owner_id") or "") == my_user_id), None)
    if not my:
        return None
    users_by_id = {str(u.get("user_id")): u for u in users if u.get("user_id")}
    scoring = league.get("scoring_settings") or {}
    settings = league.get("settings") or {}
    dynasty = _i(settings.get("type")) == 2
    positions = [p for p in (league.get("roster_positions") or []) if p not in ("BN", "IR", "TAXI")]
    want_pos = set(_SKILL)
    if "K" in positions:
        want_pos.add("K")
    if "DEF" in positions:
        want_pos.add("DEF")

    faab_budget = _i(settings.get("waiver_budget"), 100)
    faab_used = _i((my.get("settings") or {}).get("waiver_budget_used"))
    faab_left = max(0, faab_budget - faab_used)
    waiver_pos = _i((my.get("settings") or {}).get("waiver_position"))
    n_teams = _i(settings.get("num_teams"), len(rosters) or 12)
    my_rid = my.get("roster_id")
    team_name = _team_label(users_by_id, my_user_id, my_rid)

    matchups = sleeper_client.fetch_league_matchups(str(league.get("league_id")), last_week)
    my_m = next((m for m in matchups if m.get("roster_id") == my_rid), None)
    opp_m = None
    if my_m:
        opp_m = next(
            (
                m for m in matchups
                if m.get("matchup_id") == my_m.get("matchup_id") and m.get("roster_id") != my_rid
            ),
            None,
        )
    my_pts = _f((my_m or {}).get("points"))
    opp_pts = _f((opp_m or {}).get("points")) if opp_m else None
    won = None
    if opp_m is not None:
        won = my_pts > opp_pts
    opp_name = None
    if opp_m:
        opp_r = next((r for r in rosters if r.get("roster_id") == opp_m.get("roster_id")), None)
        opp_name = _team_label(
            users_by_id, str((opp_r or {}).get("owner_id") or ""), opp_m.get("roster_id")
        )

    next_matchups = sleeper_client.fetch_league_matchups(str(league.get("league_id")), next_week)
    next_opp_name = None
    my_n = next((m for m in next_matchups if m.get("roster_id") == my_rid), None)
    if my_n:
        nopp = next(
            (
                m for m in next_matchups
                if m.get("matchup_id") == my_n.get("matchup_id") and m.get("roster_id") != my_rid
            ),
            None,
        )
        if nopp:
            nr = next((r for r in rosters if r.get("roster_id") == nopp.get("roster_id")), None)
            next_opp_name = _team_label(
                users_by_id, str((nr or {}).get("owner_id") or ""), nopp.get("roster_id")
            )

    pp = (my_m or {}).get("players_points") or {}
    starters = list((my_m or {}).get("starters") or my.get("starters") or [])
    starter_set = {str(x) for x in starters if x not in (None, "0")}
    taxi_set = {str(x) for x in (my.get("taxi") or [])}
    ir_set = {str(x) for x in (my.get("reserve") or [])}

    lineup = []
    for i, pid in enumerate(starters):
        slot = positions[i] if i < len(positions) else "FLEX"
        meta = _player_meta(str(pid), players_map)
        pts = pp.get(str(pid))
        if pts is None:
            pts = score_with_settings(stats.get(str(pid)) or {}, scoring)
        lineup.append({
            **meta,
            "slot": slot,
            "pts": round(_f(pts), 2),
            "is_starter": True,
        })

    mine: list[dict] = []
    for pid in my.get("players") or []:
        meta = _player_meta(str(pid), players_map)
        w1 = score_with_settings(stats.get(str(pid)) or {}, scoring)
        w2 = score_with_settings(proj.get(str(pid)) or {}, scoring)
        row = {
            **meta,
            "w1": w1,
            "w2": w2,
            "is_starter": str(pid) in starter_set,
            "on_taxi": str(pid) in taxi_set,
            "on_ir": str(pid) in ir_set,
        }
        mine.append(row)

    # Promote taxi hits in dynasty (free, often better than FAAB).
    recs: list[dict] = []
    if dynasty:
        for p in mine:
            if not p.get("on_taxi"):
                continue
            if _f(p.get("w1")) < 8 and _f(p.get("w2")) < 8:
                continue
            recs.append({
                "priority": 0,
                "action": "promote",
                "player_id": p["id"],
                "name": p["name"],
                "pos": p["pos"],
                "team": p["team"],
                "w1": p["w1"],
                "w2": p["w2"],
                "bid_low": 0,
                "bid_high": 0,
                "drop": None,
                "why": (
                    f"Taxi just scored {p['w1']:.1f} in week {last_week}. "
                    "Promote before you spend FAAB on a worse free agent."
                ),
            })

    rostered = _rostered_ids(rosters)
    max_trend = max(trending.values()) if trending else 1
    fa_rows = []
    for pid, meta0 in (players_map or {}).items():
        if str(pid) in rostered or str(pid).startswith("TEAM_"):
            continue
        meta = _player_meta(str(pid), players_map)
        if meta["pos"] not in want_pos:
            continue
        w1 = score_with_settings(stats.get(str(pid)) or {}, scoring)
        w2 = score_with_settings(proj.get(str(pid)) or {}, scoring)
        tr = trending.get(str(pid), 0)
        if meta["pos"] in ("K", "DEF"):
            if w1 < 6 and w2 < 7 and tr < max_trend * 0.15:
                continue
        elif w1 < 5 and w2 < 6.5 and tr < max_trend * 0.12:
            continue
        if dynasty and _youth_mult(meta, True) <= 0.25 and w2 < 10:
            continue
        need = 0.0
        my_pos = [x for x in mine if x.get("pos") == meta["pos"] and not x.get("on_taxi")]
        if meta["pos"] == "QB":
            best_qb_w1 = max((_f(x.get("w1")) for x in my_pos), default=0)
            best_qb_w2 = max((_f(x.get("w2")) for x in my_pos), default=0)
            if len(my_pos) <= 1 and best_qb_w2 < 11:
                need += 10
            elif len(my_pos) <= 1 and best_qb_w1 < 8 and w2 > best_qb_w2 + 3:
                need += 4
            elif dynasty and len(my_pos) < 3 and _youth_mult(meta, True) >= 1.2:
                need += 2
        if any(_is_sit(x) and x.get("pos") == meta["pos"] and x.get("is_starter") for x in mine):
            need += 8
        if meta["pos"] in ("K", "DEF"):
            mine_same = [x for x in mine if x.get("pos") == meta["pos"]]
            cur_w2 = max((_f(x.get("w2")) for x in mine_same), default=0)
            if w2 > cur_w2 + 5:
                need += 6
        youth = _youth_mult(meta, dynasty)
        heat = 10.0 * (tr / max_trend) if max_trend else 0
        score = (w1 * 1.0 + w2 * 1.15 + heat + need) * youth
        # Don't let a one-week explosion outrank a repeatable starter.
        if w1 >= 18 and w2 > 0 and w1 > w2 * 1.75:
            score *= 0.72
        fa_rows.append({
            **meta,
            "w1": w1,
            "w2": w2,
            "trend": tr,
            "score": score,
            "need": need,
        })
    fa_rows.sort(key=lambda r: -r["score"])
    # One streamer at QB / K / DEF so skill-position adds still appear.
    diversified: list[dict] = []
    seen_stream = {"QB": 0, "K": 0, "DEF": 0}
    for row in fa_rows:
        pos = row["pos"]
        if pos in seen_stream:
            if seen_stream[pos] >= 1:
                continue
            seen_stream[pos] += 1
        diversified.append(row)
        if len(diversified) >= 8:
            break
    fa_rows = diversified

    used_ids = {r.get("player_id") for r in recs}
    rank = 1
    for row in fa_rows:
        if row["id"] in used_ids:
            continue
        if rank > 6:
            break
        urgency = min(1.0, row["score"] / 42.0) * max(0.45, 1.15 - 0.15 * rank)
        low, high = _bid_range(
            faab_left=faab_left,
            dynasty=dynasty,
            urgency=urgency,
            waiver_pos=waiver_pos,
            n_teams=n_teams,
        )
        if high <= 0 and faab_left <= 0:
            continue
        drop = _pick_drop(mine, row["pos"], dynasty)
        drop_pack = None
        if drop:
            drop_pack = {"id": drop["id"], "name": drop["name"], "pos": drop["pos"]}
        bits = []
        if row["w1"] >= 8:
            bits.append(f"{row['w1']:.1f} pts in week {last_week}")
        if row["w2"] >= 7:
            bits.append(f"~{row['w2']:.1f} projected week {next_week}")
        if row["trend"] and row["trend"] >= max_trend * 0.2:
            bits.append("hottest add on Sleeper")
        if row["need"] >= 8:
            bits.append("fills a starter hole")
        elif row["need"] >= 6:
            bits.append("better stream than what you have")
        if dynasty and _youth_mult(row, True) >= 1.2:
            bits.append("fits the rebuild window")
        if dynasty and _youth_mult(row, True) <= 0.45:
            bits.append("only if you need a 1-week plug")
        why = "; ".join(bits) or "Available value on this week’s wire."
        recs.append({
            "priority": rank,
            "action": "bid",
            "player_id": row["id"],
            "name": row["name"],
            "pos": row["pos"],
            "team": row["team"],
            "w1": row["w1"],
            "w2": row["w2"],
            "bid_low": low,
            "bid_high": high,
            "drop": drop_pack,
            "why": why + ".",
        })
        used_ids.add(row["id"])
        rank += 1

    recs.sort(key=lambda r: (0 if r.get("action") == "promote" else 1, r.get("priority") or 99))

    notes = []
    rec = (my.get("settings") or {})
    notes.append(
        f"{last_week and 'Week ' + str(last_week)}: "
        + ("W" if won else "L" if won is False else "—")
        + (f" {my_pts:.1f}–{opp_pts:.1f}" if opp_m is not None else f" {my_pts:.1f} pts")
        + (f" vs {opp_name}" if opp_name else "")
        + "."
    )
    notes.append(
        f"FAAB ${faab_left} of ${faab_budget} left · waiver slot {waiver_pos or '—'}."
    )
    if next_opp_name:
        notes.append(f"Week {next_week} opponent: {next_opp_name}.")
    if dynasty:
        notes.append("Dynasty: ignore aging week-1 spikes; bid on youth or a clear starter hole.")
    else:
        notes.append("Redraft: bid to start them this week, not to stash.")

    return {
        "league_id": str(league.get("league_id")),
        "league_name": league.get("name"),
        "dynasty": dynasty,
        "team_name": team_name,
        "record": f"{_i(rec.get('wins'))}-{_i(rec.get('losses'))}",
        "faab_left": faab_left,
        "faab_budget": faab_budget,
        "waiver_pos": waiver_pos,
        "last_week": last_week,
        "next_week": next_week,
        "result": "W" if won else "L" if won is False else None,
        "my_pts": my_pts,
        "opp_pts": opp_pts,
        "opp_name": opp_name,
        "next_opp_name": next_opp_name,
        "lineup": lineup,
        "recs": recs,
        "notes": notes,
    }


def build_weekly_report(settings: dict | None = None) -> dict[str, Any]:
    settings = settings or {}
    username = (settings.get("sleeper_username") or "starvard").strip()
    sport = (settings.get("sport") or "nfl").strip() or "nfl"
    nfl = sleeper_client.fetch_nfl_state() or {}
    last_week, next_week, season = _completed_week(nfl)
    season = str(settings.get("season") or season)

    user = sleeper_client.fetch_user_by_username(username)
    if not user:
        return {"ok": False, "error": f'Sleeper user "{username}" not found.'}
    uid = str(user.get("user_id") or "")
    leagues = sleeper_client.fetch_user_leagues(uid, sport, season)
    if not leagues:
        return {"ok": False, "error": f"No {sport.upper()} leagues for {season}."}

    cache_path = os.path.join(config.DATA_DIR, "fantasy", "sleeper_players_nfl.json")
    players_map = sleeper_client.load_players_nfl_cached(cache_path)
    stats = sleeper_client.fetch_weekly_stats(season, last_week)
    proj = sleeper_client.fetch_weekly_projections(season, next_week)
    trending_raw = sleeper_client.fetch_trending_adds(48, 50)
    trending = {
        str(t.get("player_id")): _i(t.get("count"))
        for t in trending_raw
        if t.get("player_id")
    }

    boards = []
    for lg in leagues:
        lid = str(lg.get("league_id") or "")
        if not lid:
            continue
        rosters = sleeper_client.fetch_league_rosters(lid)
        users = sleeper_client.fetch_league_users(lid)
        board = _build_league_week(
            lg, rosters, users, uid, last_week, next_week,
            stats, proj, trending, players_map,
        )
        if board:
            boards.append(board)
    boards.sort(key=lambda b: (not b.get("dynasty"), b.get("league_name") or ""))

    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "season": season,
        "last_week": last_week,
        "next_week": next_week,
        "leagues": boards,
    }
