"""
FantasyCalc public values API (used for dynasty trade math).

Dynasty Calc (dynastycalc.com) does not publish a documented public API for its
proprietary model; FantasyCalc exposes JSON at api.fantasycalc.com with sleeperId
on each player for mapping. Values are cached under data/fantasy/.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

import config

VALUES_URL = "https://api.fantasycalc.com/values/current"


def _cache_path(settings_key: str) -> str:
    safe = "".join(c if c.isalnum() else "_" for c in settings_key)[:120]
    return os.path.join(config.DATA_DIR, "fantasy", f"fantasycalc_values_{safe}.json")


def fetch_dynasty_values(
    num_qbs: int = 2,
    num_teams: int = 12,
    ppr: float = 1.0,
    max_age_seconds: int = 86400 * 2,
) -> tuple[list[dict] | None, str | None]:
    """
    Returns (rows, error_message). Rows match FantasyCalc's array of {player, value, ...}.
    """
    params = {
        "isDynasty": "true",
        "numQbs": str(num_qbs),
        "numTeams": str(num_teams),
        "ppr": str(ppr),
    }
    q = urllib.parse.urlencode(params)
    url = f"{VALUES_URL}?{q}"
    settings_key = f"d{num_qbs}_t{num_teams}_p{ppr}"
    path = _cache_path(settings_key)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    now = time.time()
    if os.path.isfile(path):
        try:
            if now - os.path.getmtime(path) < max_age_seconds:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data, None
        except (json.JSONDecodeError, OSError):
            pass

    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "LifeManager/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120.0) as resp:
            raw = resp.read()
        data = json.loads(raw.decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    stale = json.load(f)
                if isinstance(stale, list):
                    return stale, f"Using cached values (fetch failed: {e})"
            except (json.JSONDecodeError, OSError):
                pass
        return None, str(e)

    if not isinstance(data, list):
        return None, "Unexpected FantasyCalc response"

    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path)
    except OSError:
        pass

    return data, None


def values_by_sleeper_id(rows: list[dict]) -> dict[str, dict]:
    """Map Sleeper player id string -> {value, name, pos, age, overall_rank, player_obj}."""
    out: dict[str, dict] = {}
    for row in rows:
        pl = row.get("player") or {}
        sid = pl.get("sleeperId")
        if not sid:
            continue
        sid = str(sid)
        try:
            val = float(row.get("value") or 0)
        except (TypeError, ValueError):
            val = 0.0
        age = pl.get("maybeAge")
        try:
            age_f = float(age) if age is not None else None
        except (TypeError, ValueError):
            age_f = None
        out[sid] = {
            "value": val,
            "name": pl.get("name") or sid,
            "pos": pl.get("position") or "",
            "age": age_f,
            "overall_rank": row.get("overallRank"),
            "raw": row,
        }
    return out
