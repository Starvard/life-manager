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


def search_nfl_rookies_for_draft(
    query: str, limit: int = 12
) -> list[dict]:
    """
    Local search over cached slim /players/nfl: years_exp == 0, QB/RB/WR/TE.
    """
    q = (query or "").strip().lower()
    lim = max(1, min(30, int(limit or 12)))
    cache_path = os.path.join(config.DATA_DIR, "fantasy", "sleeper_players_nfl.json")
    players_map = sleeper_client.load_players_nfl_cached(cache_path) or {}
    out: list[dict] = []
    for pid, p in players_map.items():
        if not isinstance(p, dict):
            continue
        ye = p.get("years_exp")
        is_rookie = False
        if ye in (0, "0"):
            is_rookie = True
        else:
            try:
                if int(ye) == 0:
                    is_rookie = True
            except (TypeError, ValueError):
                pass
        if not is_rookie:
            continue
        pos = (p.get("position") or "").upper()
        if pos not in ("QB", "RB", "WR", "TE"):
            continue
        fn = (p.get("first_name") or "").strip()
        ln = (p.get("last_name") or "").strip()
        name = f"{fn} {ln}".strip() or (p.get("full_name") or "").strip() or str(pid)
        if q and (q not in name.lower() and q not in str(pid).lower()):
            continue
        out.append({
            "id": str(pid),
            "name": name,
            "pos": pos,
            "team": (p.get("team") or "") or "",
        })
    out.sort(key=lambda x: x["name"].lower())
    return out[:lim]


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


def _snake_pick_in_round(
    draft_type: str, n_teams: int, round_num: int, team_draft_slot: int
) -> int:
    """
    1-based pick index within a round. team_draft_slot = column (1 = first in round 1 in linear).
    """
    n = max(0, n_teams)
    if n <= 0 or round_num < 1 or team_draft_slot < 1:
        return max(1, team_draft_slot)
    t = (draft_type or "").lower()
    if t != "snake":
        return min(team_draft_slot, n)
    if round_num % 2 == 1:
        return min(team_draft_slot, n)
    return n - team_draft_slot + 1


def _enrich_draft_picks_sleeper_slots(
    my_picks: list[dict],
    league_id: str,
    league_season: str,
) -> None:
    """
    Set display_slot (e.g. 1.01) from the league's rookie/draft order + snake math.
    Mutates my_picks in place. Safe no-op on API miss.
    """
    if not my_picks or not league_id or not str(league_season).strip():
        return
    try:
        league_drafts = sleeper_client.fetch_league_drafts(league_id)
    except Exception:
        return
    cands = [d for d in (league_drafts or []) if str(d.get("season") or "") == str(league_season).strip()]
    if not cands and league_drafts:
        cands = list(league_drafts)
    if not cands:
        return
    st_rank = ("pre_draft", "drafting", "in_season", "complete", "")

    def _score(d: dict) -> int:
        st = (d.get("status") or "").lower()
        try:
            return st_rank.index(st)
        except ValueError:
            return 99

    cands.sort(key=_score)
    dmeta = cands[0]
    did = dmeta.get("draft_id")
    if not did:
        return
    dfull = sleeper_client.fetch_draft(str(did)) or {}
    stod = dfull.get("slot_to_roster_id")
    if not isinstance(stod, dict) or not stod:
        return
    n = len(stod)
    d_type = str(dfull.get("type") or "snake")
    r_to_s: dict[int, int] = {}
    for k, v in stod.items():
        try:
            sk = int(k)
        except (TypeError, ValueError):
            continue
        try:
            rid = int(v) if v is not None else None
        except (TypeError, ValueError):
            rid = None
        if rid is not None:
            r_to_s[rid] = sk
    for p in my_picks:
        orig = p.get("original_roster_id")
        if orig is None:
            continue
        try:
            oi = int(orig)
        except (TypeError, ValueError):
            continue
        my_slot = r_to_s.get(oi)
        if not my_slot or my_slot < 1:
            continue
        rnum = int(p.get("round") or 0)
        if rnum < 1:
            continue
        pin = _snake_pick_in_round(d_type, n, rnum, my_slot)
        p["display_slot"] = f"{rnum}.{pin:02d}"
        p["sleeper_draft_id"] = str(did)
        p["label"] = (
            f"{p.get('season', '')} {p['display_slot']}"
            + (f" (from {p.get('original_team_label')})" if p.get("original_team_label") else "")
        )


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
    _enrich_draft_picks_sleeper_slots(my_picks, league_id, str(league.get("season") or season))
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
