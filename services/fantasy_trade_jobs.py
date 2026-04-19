"""
Background refresh for fantasy trade suggestions (FantasyCalc + Sleeper snapshot).
"""

from __future__ import annotations

import fcntl
import os

import config
from services import sleeper_client
from services.fantasy_store import apply_trade_error, apply_trade_refresh, load_state
from services.fantasy_trade_engine import run_trade_refresh

LOCK_PATH = os.path.join(config.FANTASY_DIR, ".trade_refresh.lock")


def refresh_trade_suggestions() -> dict:
    """
    Recompute trade ideas from cached Sleeper league data + FantasyCalc values.
    Safe to call from a scheduler; uses an exclusive lock so only one run at a time.
    """
    if os.environ.get("LM_DISABLE_FANTASY", "").lower() in ("1", "true", "yes"):
        return {"ok": False, "skipped": True, "reason": "fantasy disabled"}
    os.makedirs(config.FANTASY_DIR, exist_ok=True)
    lock_f = None
    try:
        lock_f = open(LOCK_PATH, "a+")
        try:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"ok": False, "skipped": True, "reason": "lock busy"}

        state = load_state()
        snap = state.get("cached_snapshot")
        if not snap:
            apply_trade_error("Sync Sleeper first, then refresh trades.")
            return {"ok": False, "error": "no snapshot"}

        rosters = snap.get("league_rosters")
        users = snap.get("league_users")
        if not rosters or not users:
            apply_trade_error("Re-sync Sleeper: league roster data missing (update Life Manager).")
            return {"ok": False, "error": "stale snapshot"}

        uid = (snap.get("user") or {}).get("user_id")
        lid = (snap.get("league") or {}).get("league_id")
        if not uid or not lid:
            apply_trade_error("Invalid cached league snapshot.")
            return {"ok": False, "error": "bad snapshot"}

        s = state.get("settings") or {}
        valuation_settings = {
            "num_qbs": s.get("valuation_num_qbs", 2),
            "num_teams": s.get("valuation_num_teams", 12),
            "ppr": s.get("valuation_ppr", 1.0),
            "strategy": s.get("trade_strategy", "rebuild"),
        }

        cache_path = os.path.join(config.DATA_DIR, "fantasy", "sleeper_players_nfl.json")
        players_map = sleeper_client.load_players_nfl_cached(cache_path)

        result = run_trade_refresh(
            str(lid),
            rosters,
            users,
            str(uid),
            players_map,
            valuation_settings,
        )
        if result.get("ok"):
            apply_trade_refresh(result)
        else:
            apply_trade_error(result.get("error") or "Trade refresh failed.")
        # Drop large refs before releasing the lock to keep peak RSS in check.
        players_map = None  # noqa: F841
        rosters = None  # noqa: F841
        users = None  # noqa: F841
        import gc as _gc
        _gc.collect()
        return result
    finally:
        if lock_f is not None:
            try:
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                lock_f.close()
            except OSError:
                pass
