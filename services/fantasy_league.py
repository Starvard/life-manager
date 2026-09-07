"""
League-wide dynasty context: power rankings, contention verdict, trade tape.

Uses FantasyCalc values + the Sleeper snapshot (rosters, prior year, trades).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _team_label(users_by_id: dict[str, dict], owner_id: str, roster_id: Any) -> str:
    u = users_by_id.get(str(owner_id) or "") or {}
    meta = u.get("metadata") or {}
    if isinstance(meta, dict) and meta.get("team_name"):
        return str(meta["team_name"])
    return str(u.get("display_name") or f"Team {roster_id}")


def _fc_pack(pid: str, vmap: dict[str, dict]) -> dict[str, Any]:
    info = vmap.get(str(pid)) or {}
    try:
        val = float(info.get("value") or 0)
    except (TypeError, ValueError):
        val = 0.0
    age = info.get("age")
    try:
        age_f = float(age) if age is not None else None
    except (TypeError, ValueError):
        age_f = None
    return {
        "player_id": str(pid),
        "name": info.get("name") or f"Player {pid}",
        "pos": (info.get("pos") or "").upper(),
        "age": age_f,
        "value": round(val, 1),
        "overall_rank": info.get("overall_rank"),
    }


def _pick_outlook(prior_wins: int | None) -> str:
    if prior_wins is None:
        return ""
    try:
        w = int(prior_wins)
    except (TypeError, ValueError):
        return ""
    if w <= 3:
        return "likely early"
    if w >= 10:
        return "likely late"
    return "mid-range"


def _ms_to_iso(ms: Any) -> str | None:
    try:
        n = int(ms)
    except (TypeError, ValueError):
        return None
    if n > 10**12:
        n = n / 1000.0
    try:
        return datetime.fromtimestamp(n, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _decode_trade(
    raw: dict,
    rosters: list[dict],
    users_by_id: dict[str, dict],
    my_roster_id: Any,
    vmap: dict[str, dict],
) -> dict[str, Any] | None:
    rids = raw.get("roster_ids") or []
    if not isinstance(rids, list) or len(rids) < 2:
        return None
    roster_by_id = {r.get("roster_id"): r for r in rosters}
    adds = raw.get("adds") or {}
    if not isinstance(adds, dict):
        adds = {}
    picks = raw.get("draft_picks") or []
    faab = raw.get("waiver_budget") or []

    teams: list[dict[str, Any]] = []
    involves_me = my_roster_id in rids
    for rid in rids:
        rr = roster_by_id.get(rid)
        oid = str((rr or {}).get("owner_id") or "")
        name = _team_label(users_by_id, oid, rid)
        got_players = []
        for pid, dest in adds.items():
            try:
                dest_i = int(dest)
            except (TypeError, ValueError):
                dest_i = dest
            if dest_i == rid or dest == rid:
                got_players.append(_fc_pack(str(pid), vmap))
        got_players.sort(key=lambda p: -float(p.get("value") or 0))
        got_picks: list[str] = []
        for dp in picks:
            if not isinstance(dp, dict):
                continue
            if dp.get("owner_id") != rid:
                continue
            season = dp.get("season")
            rnd = dp.get("round")
            orig = dp.get("roster_id")
            label = f"{season} R{rnd}"
            if orig is not None and orig != rid:
                orig_r = roster_by_id.get(orig)
                orig_oid = str((orig_r or {}).get("owner_id") or "")
                orig_name = _team_label(users_by_id, orig_oid, orig)
                label += f" ({orig_name})"
            got_picks.append(label)
        faab_in = 0
        for row in faab:
            if isinstance(row, dict) and row.get("receiver") == rid:
                try:
                    faab_in += int(row.get("amount") or 0)
                except (TypeError, ValueError):
                    pass
        teams.append({
            "roster_id": rid,
            "team_name": name,
            "is_mine": rid == my_roster_id,
            "players": got_players,
            "picks": got_picks,
            "faab": faab_in,
        })

    return {
        "transaction_id": raw.get("transaction_id"),
        "created": raw.get("created"),
        "created_iso": _ms_to_iso(raw.get("created")),
        "week": raw.get("week"),
        "league_id": raw.get("league_id"),
        "involves_me": involves_me,
        "teams": teams,
    }


def _classify_assets(
    my_assets: list[dict],
    horizon_years: int,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Return (hold, sell_now, shop) with a why line on each."""
    ranked = sorted(my_assets, key=lambda a: -float(a.get("value") or 0))
    hold: list[dict] = []
    sell: list[dict] = []
    shop: list[dict] = []
    hold_ids: set[str] = set()

    for i, a in enumerate(ranked):
        pid = a.get("player_id")
        pos = (a.get("pos") or "").upper()
        age = a.get("age")
        val = float(a.get("value") or 0)
        name = a.get("name") or pid
        if val <= 0:
            continue

        young_qb = pos == "QB" and age is not None and age <= 26.5 and val >= 1500
        young_skill = pos in ("RB", "WR", "TE") and age is not None and age <= 23.5 and val >= 1200
        franchise = i < 2 and val >= 3000
        if franchise or young_qb or young_skill:
            why = "Cornerstone — do not shop."
            if young_qb:
                why = "Young QB lottery ticket in superflex. Hold."
            elif young_skill:
                why = "Young skill piece that fits a multi-year window. Hold."
            elif i == 0:
                why = "Best asset on the roster. Hold unless a massive overpay."
            hold.append({**a, "why": why})
            hold_ids.add(str(pid))

    for a in ranked:
        pid = str(a.get("player_id") or "")
        if pid in hold_ids:
            continue
        pos = (a.get("pos") or "").upper()
        if pos not in ("QB", "RB", "WR", "TE"):
            continue
        age = a.get("age")
        val = float(a.get("value") or 0)
        if val < 250:
            continue

        sell_vet = False
        why = ""
        if age is not None and age >= 31:
            sell_vet = True
            why = f"Age {age:.0f} — win-now leftover. Sell to a contender."
        elif age is not None and age >= 29:
            sell_vet = True
            why = f"Age {age:.0f} {pos} — does not fit a {horizon_years}-year rebuild. Move this season."
        elif age is not None and age >= 27.5 and pos in ("RB", "TE") and val < 2200:
            sell_vet = True
            why = f"Aging {pos} with limited leftover window. Package to a playoff team."

        if sell_vet:
            sell.append({**a, "why": why})
            continue

        if val >= 700:
            shop.append({
                **a,
                "why": "Fine as depth or trade filler — do not attach a 1st to move this.",
            })

    return hold[:6], sell[:8], shop[:8]


def _verdict(
    rank: int,
    n_teams: int,
    playoff_teams: int,
    weak_starters: int,
    prior_wins: int | None,
    gap_to_playoff: float,
) -> tuple[str, str]:
    """Return (verdict_key, title)."""
    forced_rebuild = (
        prior_wins is not None
        and prior_wins <= 4
        and rank >= max(8, n_teams - 3)
    )
    if forced_rebuild or rank >= n_teams - 1 or (rank >= 9 and gap_to_playoff > 8000):
        return (
            "rebuild",
            "Full rebuild — you are not a 2026 contender",
        )
    if rank <= 3 and weak_starters <= 1:
        return ("compete", "Compete window is open")
    if rank <= playoff_teams and weak_starters <= 3:
        return ("bubble", "Bubble — one good offseason from a real window")
    if rank <= playoff_teams + 2:
        return ("bubble", "Just outside the mix — do not force it")
    return ("rebuild", "Rebuild — roster value is well behind the pack")


def build_league_landscape(
    snapshot: dict,
    vmap: dict[str, dict],
    best_lineup: dict | None = None,
    horizon_years: int = 3,
) -> dict[str, Any]:
    """
    Compact league context for the Dynasty page. Safe to send to the browser.
    """
    rosters = snapshot.get("league_rosters") or []
    users = snapshot.get("league_users") or []
    users_by_id = {str(u.get("user_id")): u for u in users if u.get("user_id")}
    my_user_id = str((snapshot.get("user") or {}).get("user_id") or "")
    my_rid = (snapshot.get("team") or {}).get("roster_id")
    league = snapshot.get("league") or {}
    try:
        playoff_teams = int((league.get("settings") or {}).get("playoff_teams") or 6)
    except (TypeError, ValueError):
        playoff_teams = 6

    prior = snapshot.get("prior_season") or {}
    prior_by_owner = prior.get("by_owner") if isinstance(prior.get("by_owner"), dict) else {}
    prior_season = str(prior.get("season") or "")

    teams_out: list[dict[str, Any]] = []
    my_assets: list[dict] = []
    my_rank = 0
    my_value = 0.0

    for r in rosters:
        oid = str(r.get("owner_id") or "")
        rid = r.get("roster_id")
        pids = [str(p) for p in (r.get("players") or []) if p is not None]
        packed = [_fc_pack(pid, vmap) for pid in pids]
        packed.sort(key=lambda p: -float(p.get("value") or 0))
        total = sum(float(p.get("value") or 0) for p in packed)
        ages = [p["age"] for p in packed if p.get("age") is not None]
        avg_age = round(sum(ages) / len(ages), 1) if ages else None
        qbs = [p for p in packed if p.get("pos") == "QB"][:3]
        rec = prior_by_owner.get(oid) or {}
        is_mine = oid == my_user_id
        row = {
            "roster_id": rid,
            "owner_id": oid,
            "team_name": _team_label(users_by_id, oid, rid),
            "is_mine": is_mine,
            "roster_value": round(total, 1),
            "player_count": len(pids),
            "avg_age": avg_age,
            "top_assets": packed[:5],
            "qbs": qbs,
            "prior_wins": rec.get("wins"),
            "prior_losses": rec.get("losses"),
            "prior_fpts": rec.get("fpts"),
        }
        teams_out.append(row)
        if is_mine:
            my_assets = packed
            my_value = total
            my_rid = rid

    teams_out.sort(key=lambda t: -float(t.get("roster_value") or 0))
    for i, t in enumerate(teams_out, 1):
        t["rank"] = i
        if t.get("is_mine"):
            my_rank = i

    n_teams = len(teams_out) or 12
    leader = teams_out[0] if teams_out else None
    cutoff_idx = min(playoff_teams, n_teams) - 1
    cutoff = teams_out[cutoff_idx] if teams_out and cutoff_idx >= 0 else None
    leader_value = float((leader or {}).get("roster_value") or 0)
    cutoff_value = float((cutoff or {}).get("roster_value") or 0)
    gap_to_leader = round(max(0.0, leader_value - my_value), 1)
    gap_to_playoff = round(max(0.0, cutoff_value - my_value), 1)

    weak_starters = 0
    if isinstance(best_lineup, dict):
        for s in best_lineup.get("slots") or []:
            if s.get("is_weak") or s.get("is_empty"):
                weak_starters += 1

    my_prior = None
    if my_user_id and my_user_id in prior_by_owner:
        my_prior = prior_by_owner[my_user_id]
    prior_wins = None
    if isinstance(my_prior, dict) and my_prior.get("wins") is not None:
        try:
            prior_wins = int(my_prior.get("wins"))
        except (TypeError, ValueError):
            prior_wins = None

    verdict, title = _verdict(
        my_rank or n_teams,
        n_teams,
        playoff_teams,
        weak_starters,
        prior_wins,
        gap_to_playoff,
    )

    hold, sell, shop = _classify_assets(my_assets, horizon_years)

    future_picks = []
    for p in snapshot.get("draft_picks") or []:
        orig = p.get("original_roster_id")
        orig_team = next((t for t in teams_out if t.get("roster_id") == orig), None)
        outlook = _pick_outlook((orig_team or {}).get("prior_wins"))
        future_picks.append({
            "season": p.get("season"),
            "round": p.get("round"),
            "label": p.get("label"),
            "original_team_label": p.get("original_team_label"),
            "is_own_original": bool(p.get("is_own_original")),
            "outlook": outlook,
            "pick_key": p.get("pick_key"),
        })

    next_season = None
    seasons = sorted({str(p.get("season")) for p in future_picks if p.get("season")})
    if seasons:
        next_season = seasons[0]
    next_firsts = [
        p for p in future_picks
        if str(p.get("season")) == next_season and int(p.get("round") or 0) == 1
    ]
    own_next_first = any(p.get("is_own_original") for p in next_firsts)
    missing_mid = []
    if next_season:
        have_rounds = {
            int(p.get("round") or 0)
            for p in future_picks
            if str(p.get("season")) == next_season and p.get("is_own_original")
        }
        for rnd in (2, 3, 4):
            if rnd not in have_rounds:
                missing_mid.append(f"{next_season} R{rnd}")

    lines: list[str] = []
    if my_prior and prior_season:
        lines.append(
            f"{prior_season} finish: {my_prior.get('wins', '—')}-{my_prior.get('losses', '—')}"
            + (f", {my_prior.get('fpts')} pts." if my_prior.get("fpts") is not None else ".")
        )
    if my_rank:
        lines.append(
            f"Roster value rank {my_rank} of {n_teams} "
            f"(≈{round(my_value):,} vs ≈{round(leader_value):,} at the top)."
        )
    if gap_to_playoff > 0 and verdict != "compete":
        cut_name = (cutoff or {}).get("team_name") or f"{playoff_teams}th"
        lines.append(
            f"About {round(gap_to_playoff):,} dynasty points behind the current "
            f"{playoff_teams}-team playoff-value line ({cut_name})."
        )
    if verdict == "rebuild":
        lines.append(
            "Treat this season as development: start the youth, sell aging production "
            "to contenders, and do not trade future 1sts for win-now pieces."
        )
    elif verdict == "bubble":
        lines.append(
            "You can be opportunistic, but one bad QB/WR hole still separates you from a real window."
        )
    else:
        lines.append("Hold the core and buy aging production if the price is a 2nd or less.")

    if hold:
        lines.append("Hold: " + ", ".join(h.get("name") for h in hold[:4]) + ".")
    if sell:
        lines.append(
            "Sell this year: " + ", ".join(s.get("name") for s in sell[:4])
            + " — contenders will overpay vs your window."
        )
    if next_firsts:
        bits = []
        for p in next_firsts:
            bit = p.get("label") or f"{p.get('season')} 1st"
            if p.get("outlook"):
                bit += f" ({p['outlook']})"
            bits.append(bit)
        lines.append("Upcoming 1sts: " + "; ".join(bits) + ".")
    if not own_next_first and next_season:
        lines.append(f"You do not own your own {next_season} 1st — stop moving first-round capital.")
    if missing_mid:
        lines.append(
            "Already moved: " + ", ".join(missing_mid)
            + ". Do not keep bleeding mid-round picks for veterans."
        )

    raw_trades = snapshot.get("league_trades") or []
    tape: list[dict] = []
    for raw in raw_trades:
        decoded = _decode_trade(raw, rosters, users_by_id, my_rid, vmap)
        if decoded:
            tape.append(decoded)
    tape.sort(key=lambda t: (not t.get("involves_me"), -(t.get("created") or 0)))
    tape = tape[:24]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "verdict_title": title,
        "verdict_lines": lines,
        "my_rank": my_rank,
        "n_teams": n_teams,
        "playoff_teams": playoff_teams,
        "my_roster_value": round(my_value, 1),
        "leader_value": round(leader_value, 1),
        "leader_name": (leader or {}).get("team_name"),
        "playoff_cutoff_value": round(cutoff_value, 1),
        "gap_to_leader": gap_to_leader,
        "gap_to_playoff": gap_to_playoff,
        "weak_starters": weak_starters,
        "prior_season": prior_season or None,
        "prior_record": my_prior,
        "teams": teams_out,
        "hold": hold,
        "sell_now": sell,
        "shop": shop,
        "future_picks": future_picks,
        "trade_tape": tape,
        "sleeper_trades_url": (
            f"https://sleeper.com/leagues/{league.get('league_id')}/trades"
            if league.get("league_id") else None
        ),
    }
