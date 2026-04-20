"""
Build a normalized Sleeper snapshot for the fantasy UI (roster + league context).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import config
from services import sleeper_client


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _pick_league(
    leagues: list[dict],
    league_id: str | None,
    name_hint: str | None,
) -> dict | None:
    if not leagues:
        return None
    lid = _norm(league_id or "")
    if lid:
        for lg in leagues:
            if str(lg.get("league_id", "")) == lid:
                return lg
    hint = _norm(name_hint or "")
    if hint:
        for lg in leagues:
            if hint in _norm(str(lg.get("name", ""))):
                return lg
    return leagues[0]


def _player_label(players_map: dict | None, pid: str) -> dict:
    pid = str(pid)
    p = (players_map or {}).get(pid) if players_map else None
    if not p:
        return {"id": pid, "name": f"Player {pid}", "pos": "", "team": ""}
    fn = (p.get("first_name") or "").strip()
    ln = (p.get("last_name") or "").strip()
    name = f"{fn} {ln}".strip() or (p.get("full_name") or "").strip() or pid
    return {
        "id": pid,
        "name": name,
        "pos": (p.get("position") or "") or "",
        "team": (p.get("team") or "") or "",
    }


def _team_name_for_roster(rosters: list[dict], users: list[dict], roster_id: int | None) -> str:
    if roster_id is None:
        return ""
    oid = None
    for r in rosters:
        if r.get("roster_id") == roster_id:
            oid = str(r.get("owner_id", ""))
            break
    if not oid:
        return f"Roster {roster_id}"
    for u in users:
        if str(u.get("user_id", "")) == oid:
            meta = u.get("metadata") or {}
            if isinstance(meta, dict) and meta.get("team_name"):
                return str(meta["team_name"])
            return str(u.get("display_name") or f"Roster {roster_id}")
    return f"Roster {roster_id}"


def _my_draft_picks(
    traded_picks: list[dict],
    my_roster_id: int | None,
    rosters: list[dict],
    users: list[dict],
) -> list[dict]:
    """Picks currently owned by my roster (Sleeper traded_picks API)."""
    if my_roster_id is None:
        return []
    out: list[dict] = []
    for row in traded_picks:
        if row.get("owner_id") != my_roster_id:
            continue
        rid = row.get("roster_id")
        season = str(row.get("season", ""))
        rnd = row.get("round")
        try:
            rnum = int(rnd) if rnd is not None else 0
        except (TypeError, ValueError):
            rnum = 0
        orig_team = _team_name_for_roster(rosters, users, rid)
        label = f"{season} · Round {rnum}"
        if rid != my_roster_id:
            label += f" (from {orig_team})"
        out.append({
            "season": season,
            "round": rnum,
            "original_roster_id": rid,
            "original_team_label": orig_team if rid != my_roster_id else None,
            "label": label,
            "pick_key": f"{season}-r{rnum}-slot{rid}",
        })
    out.sort(key=lambda x: (x["season"], x["round"], x.get("original_roster_id") or 0))
    return out


def _slot_rows(
    roster_positions: list[str],
    starters: list[str] | None,
    players_map: dict | None,
) -> list[dict]:
    starters = starters or []
    rows = []
    n = max(len(roster_positions), len(starters))
    for i in range(n):
        slot = roster_positions[i] if i < len(roster_positions) else "FLEX"
        pid = starters[i] if i < len(starters) else None
        if pid in (None, "0"):
            rows.append({
                "slot": slot,
                "empty": True,
                "player": None,
            })
        else:
            rows.append({
                "slot": slot,
                "empty": False,
                "player": _player_label(players_map, str(pid)),
            })
    return rows


def sync_team(settings: dict) -> dict:
    if os.environ.get("LM_DISABLE_FANTASY", "").lower() in ("1", "true", "yes"):
        return {"ok": False, "error": "Fantasy is disabled on this deployment (LM_DISABLE_FANTASY=1)."}
    username = (settings.get("sleeper_username") or "").strip()
    if not username:
        return {"ok": False, "error": "Set a Sleeper username in settings."}

    sport = (settings.get("sport") or "nfl").strip() or "nfl"
    season = str(settings.get("season") or datetime.now().year).strip()

    user = sleeper_client.fetch_user_by_username(username)
    if not user:
        return {"ok": False, "error": f'Sleeper user "{username}" not found.'}

    user_id = str(user.get("user_id", ""))
    if not user_id:
        return {"ok": False, "error": "Sleeper returned no user id."}

    leagues = sleeper_client.fetch_user_leagues(user_id, sport, season)
    if not leagues:
        return {
            "ok": False,
            "error": f"No {sport.upper()} leagues for {season} on this account.",
        }

    league = _pick_league(
        leagues,
        settings.get("league_id"),
        settings.get("league_name_hint"),
    )
    if not league:
        return {"ok": False, "error": "Could not pick a league."}

    league_id = str(league.get("league_id", ""))
    rosters = sleeper_client.fetch_league_rosters(league_id)
    users = sleeper_client.fetch_league_users(league_id)
    traded_picks = sleeper_client.fetch_league_traded_picks(league_id)

    my_roster = None
    for r in rosters:
        if str(r.get("owner_id", "")) == user_id:
            my_roster = r
            break
    if not my_roster:
        return {"ok": False, "error": "No roster found for your user in this league."}

    team_name = None
    for u in users:
        if str(u.get("user_id", "")) == user_id:
            meta = u.get("metadata") or {}
            if isinstance(meta, dict):
                team_name = meta.get("team_name")
            break

    cache_path = os.path.join(config.DATA_DIR, "fantasy", "sleeper_players_nfl.json")
    players_map = sleeper_client.load_players_nfl_cached(cache_path)

    roster_positions = league.get("roster_positions") or []
    player_ids = my_roster.get("players") or []
    starters = my_roster.get("starters") or []
    reserve = my_roster.get("reserve") or []
    taxi = my_roster.get("taxi") or []

    starter_rows = _slot_rows(roster_positions, starters, players_map)

    bench_ids = [pid for pid in player_ids if pid not in starters and pid not in reserve and pid not in taxi]
    bench = [_player_label(players_map, str(pid)) for pid in bench_ids]
    res_list = [_player_label(players_map, str(pid)) for pid in reserve]
    taxi_list = [_player_label(players_map, str(pid)) for pid in taxi]

    rs = my_roster.get("settings") or {}
    my_rid = my_roster.get("roster_id")
    my_picks = _my_draft_picks(traded_picks, my_rid, rosters, users)
    synced_at = datetime.now(timezone.utc).isoformat()

    # Release the big players_map ref before constructing the snapshot so
    # peak RSS during the JSON dump is lower on tiny VMs.
    import gc as _gc

    snapshot = {
        "synced_at": synced_at,
        "user": {
            "user_id": user_id,
            "username": user.get("username"),
            "display_name": user.get("display_name"),
        },
        # Used for league-wide trade suggestions (same payloads Sleeper returns)
        "league_rosters": rosters,
        "league_users": users,
        "league": {
            "league_id": league_id,
            "name": league.get("name"),
            "season": league.get("season"),
            "status": league.get("status"),
            "previous_league_id": league.get("previous_league_id"),
            "roster_positions": roster_positions,
        },
        "team": {
            "name": team_name,
            "roster_id": my_roster.get("roster_id"),
            "record": (my_roster.get("metadata") or {}).get("record"),
            "settings": {
                "wins": rs.get("wins"),
                "losses": rs.get("losses"),
                "ties": rs.get("ties"),
                "fpts": rs.get("fpts"),
                "fpts_decimal": rs.get("fpts_decimal"),
                "waiver_budget_used": rs.get("waiver_budget_used"),
                "waiver_position": rs.get("waiver_position"),
            },
        },
        "starters": starter_rows,
        "bench": bench,
        "reserve": res_list,
        "taxi": taxi_list,
        "draft_picks": my_picks,
        "players_resolved": bool(players_map),
    }
    players_map = None  # noqa: F841 (drop local ref to help GC)
    _gc.collect()
    return {"ok": True, "snapshot": snapshot}
