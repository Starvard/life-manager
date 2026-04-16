"""
Heuristic dynasty trade suggestions using FantasyCalc values + full Sleeper league rosters.

Not financial advice; for planning only. Dynasty Calc cannot be queried programmatically
(their model is proprietary); we use FantasyCalc's public values as the quantitative layer.
"""

from __future__ import annotations

import itertools
from typing import Any

from services import fantasycalc_client


def _roster_player_ids(roster: dict) -> set[str]:
    out: set[str] = set()
    for key in ("players", "reserve", "taxi"):
        for pid in roster.get(key) or []:
            if pid is not None:
                out.add(str(pid))
    return out


def _team_label(users_by_id: dict[str, dict], owner_id: str, roster_id: int | None) -> str:
    u = users_by_id.get(owner_id) or {}
    meta = u.get("metadata") or {}
    if isinstance(meta, dict) and meta.get("team_name"):
        return str(meta["team_name"])
    return u.get("display_name") or f"Team {roster_id}"


def build_league_context(
    rosters: list[dict],
    users: list[dict],
    my_user_id: str,
) -> tuple[dict[str, Any], dict[str, dict]]:
    users_by_id = {str(u.get("user_id")): u for u in users if u.get("user_id")}

    teams: list[dict[str, Any]] = []
    my_ids: set[str] = set()

    for r in rosters:
        oid = str(r.get("owner_id", ""))
        rid = r.get("roster_id")
        pids = _roster_player_ids(r)
        if oid == my_user_id:
            my_ids = pids
        teams.append({
            "roster_id": rid,
            "owner_id": oid,
            "team_name": _team_label(users_by_id, oid, rid),
            "player_ids": sorted(pids),
            "is_mine": oid == my_user_id,
        })

    return {
        "teams": teams,
        "my_player_ids": sorted(my_ids),
    }, users_by_id


def _player_display(pid: str, sleeper_meta: dict | None) -> dict[str, Any]:
    if not sleeper_meta:
        return {"id": pid, "name": f"Player {pid}", "pos": "", "team": ""}
    fn = (sleeper_meta.get("first_name") or "").strip()
    ln = (sleeper_meta.get("last_name") or "").strip()
    name = f"{fn} {ln}".strip() or (sleeper_meta.get("full_name") or "").strip() or pid
    return {
        "id": pid,
        "name": name,
        "pos": (sleeper_meta.get("position") or "") or "",
        "team": (sleeper_meta.get("team") or "") or "",
    }


def generate_suggestions(
    my_user_id: str,
    league_teams: list[dict],
    value_by_sid: dict[str, dict],
    players_map: dict | None,
    strategy: str = "rebuild",
    max_suggestions: int = 18,
) -> list[dict[str, Any]]:
    """
    strategy: "rebuild" favors moving older assets for youth/picks; "balanced" is looser.
    """
    strategy = (strategy or "rebuild").lower()
    my_team = next((t for t in league_teams if t.get("is_mine")), None)
    if not my_team:
        return []

    my_ids = set(my_team.get("player_ids") or [])
    others = [t for t in league_teams if not t.get("is_mine")]

    def val_info(pid: str) -> dict | None:
        return value_by_sid.get(str(pid))

    def total_value(pids: list[str]) -> float:
        s = 0.0
        for p in pids:
            vi = val_info(p)
            if vi:
                s += float(vi.get("value") or 0)
        return s

    # Classify my roster
    my_with_val: list[tuple[str, dict]] = []
    for pid in my_ids:
        vi = val_info(pid)
        if vi and float(vi.get("value") or 0) > 0:
            my_with_val.append((pid, vi))
    my_with_val.sort(key=lambda x: -x[1]["value"])

    my_starters_set = set()  # we don't have starter slots here; use top by value as "core"
    core_cut = max(3, min(8, len(my_with_val) // 2))
    core_ids = {pid for pid, _ in my_with_val[:core_cut]}

    suggestions: list[dict[str, Any]] = []

    def add_suggestion(
        partner_name: str,
        partner_owner: str,
        give_ids: list[str],
        get_ids: list[str],
        tag: str,
        note: str,
    ):
        give_total = total_value(give_ids)
        get_total = total_value(get_ids)
        if give_total <= 0 or get_total <= 0:
            return
        ratio = get_total / give_total if give_total else 0
        suggestions.append({
            "tag": tag,
            "partner_team": partner_name,
            "partner_owner_id": partner_owner,
            "you_send": [_pack(pid) for pid in give_ids],
            "you_receive": [_pack(pid) for pid in get_ids],
            "value_send": round(give_total, 1),
            "value_receive": round(get_total, 1),
            "fairness_ratio": round(ratio, 3),
            "note": note,
        })

    def _pack(pid: str) -> dict[str, Any]:
        vi = val_info(pid) or {}
        sm = (players_map or {}).get(str(pid)) if players_map else None
        base = _player_display(str(pid), sm)
        base["fantasy_value"] = round(float(vi.get("value") or 0), 1)
        base["age"] = vi.get("age")
        return base

    band_lo, band_hi = (0.78, 1.22) if strategy == "rebuild" else (0.85, 1.18)
    pkg_lo, pkg_hi = (0.80, 1.15)

    # My movable pieces: non-core or older in rebuild
    movable: list[str] = []
    for pid, vi in my_with_val:
        age = vi.get("age")
        is_old = age is not None and age >= 27.0
        if pid not in core_ids or is_old:
            movable.append(pid)
    if not movable:
        movable = [pid for pid, _ in my_with_val[core_cut:]] or [pid for pid, _ in my_with_val[-5:]]

    # --- Pair search: 1 for 1, or 2 for 1 ---
    for opp in others:
        opp_ids = list(opp.get("player_ids") or [])
        opp_name = opp.get("team_name") or "Opponent"
        oid = opp.get("owner_id") or ""

        opp_assets = [(pid, val_info(pid)) for pid in opp_ids if val_info(pid)]
        opp_assets.sort(key=lambda x: -float(x[1].get("value") or 0))

        for me in movable[:12]:
            me_v = val_info(me)
            if not me_v:
                continue
            me_val = float(me_v.get("value") or 0)
            if me_val < 300:
                continue

            # Single for single
            for them, them_v in opp_assets[:20]:
                if them == me:
                    continue
                tv = float(them_v.get("value") or 0)
                if tv < 400:
                    continue
                if band_lo <= tv / me_val <= band_hi:
                    tag = "veteran_for_youth" if (
                        strategy == "rebuild"
                        and me_v.get("age") is not None
                        and them_v.get("age") is not None
                        and me_v["age"] > them_v["age"] + 2
                    ) else "value_swap"
                    add_suggestion(
                        opp_name, oid, [me], [them], tag,
                        "Single-player swap in a typical fairness band (FantasyCalc dynasty values).",
                    )

            # Two pieces for one upgrade
            for a, b in itertools.combinations(movable[:10], 2):
                pair_val = total_value([a, b])
                if pair_val < 800:
                    continue
                for them, them_v in opp_assets[:15]:
                    tv = float(them_v.get("value") or 0)
                    ratio = tv / pair_val if pair_val else 0
                    if pkg_lo <= ratio <= pkg_hi:
                        add_suggestion(
                            opp_name, oid, [a, b], [them], "package_consolidation",
                            "Consolidate depth into one asset; verify roster construction after.",
                        )
                        break

    # Dedupe by signature
    seen: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for s in suggestions:
        key = "|".join(sorted(f"{p['id']}" for p in s["you_send"])) + "=>" + "|".join(
            sorted(f"{p['id']}" for p in s["you_receive"])
        ) + "@" + s["partner_owner_id"]
        if key in seen:
            continue
        seen.add(key)
        uniq.append(s)

    # Sort: prefer better fairness near 1.0, then higher receive value
    def score(s: dict[str, Any]) -> tuple:
        r = s.get("fairness_ratio") or 0
        return (-abs(1.0 - r), -float(s.get("value_receive") or 0))

    uniq.sort(key=score)
    return uniq[:max_suggestions]


def run_trade_refresh(
    league_id: str,
    rosters: list[dict],
    users: list[dict],
    my_user_id: str,
    players_map: dict | None,
    valuation_settings: dict[str, Any],
) -> dict[str, Any]:
    num_qbs = int(valuation_settings.get("num_qbs") or 2)
    num_teams = int(valuation_settings.get("num_teams") or 12)
    ppr = float(valuation_settings.get("ppr") or 1.0)
    strategy = str(valuation_settings.get("strategy") or "rebuild")

    rows, warn = fantasycalc_client.fetch_dynasty_values(
        num_qbs=num_qbs, num_teams=num_teams, ppr=ppr
    )
    if not rows:
        return {
            "ok": False,
            "error": warn or "Could not load FantasyCalc values.",
        }

    vmap = fantasycalc_client.values_by_sleeper_id(rows)
    ctx, _ = build_league_context(rosters, users, my_user_id)
    teams = ctx["teams"]

    sugs = generate_suggestions(
        my_user_id, teams, vmap, players_map, strategy=strategy
    )

    from datetime import datetime, timezone

    return {
        "ok": True,
        "warning": warn,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "league_id": league_id,
        "valuation": {
            "source": "FantasyCalc",
            "source_url": "https://fantasycalc.com",
            "num_qbs": num_qbs,
            "num_teams": num_teams,
            "ppr": ppr,
            "strategy": strategy,
        },
        "suggestions": sugs,
        "disclaimer": (
            "Suggestions use FantasyCalc public dynasty values mapped by Sleeper player id. "
            "They are heuristics for discussion, not a guarantee. "
            "Cross-check trades on Dynasty Calc or your league chat."
        ),
    }
