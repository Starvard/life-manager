"""
HTTP helpers for the public Sleeper API (https://docs.sleeper.com/).

No API key required. Uses urllib (stdlib) to avoid extra dependencies.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

SLEEPER_BASE = "https://api.sleeper.app/v1"


def _get_json(url: str, timeout: float = 45.0) -> Any:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "LifeManager/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def fetch_user_by_username(username: str) -> dict | None:
    username = (username or "").strip()
    if not username:
        return None
    try:
        data = _get_json(f"{SLEEPER_BASE}/user/{urllib.parse.quote(username)}")
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def fetch_user_leagues(user_id: str, sport: str, season: str | int) -> list[dict]:
    uid = (user_id or "").strip()
    if not uid:
        return []
    try:
        data = _get_json(f"{SLEEPER_BASE}/user/{uid}/leagues/{sport}/{season}")
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def fetch_league_rosters(league_id: str) -> list[dict]:
    lid = (league_id or "").strip()
    if not lid:
        return []
    try:
        data = _get_json(f"{SLEEPER_BASE}/league/{lid}/rosters")
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def fetch_league_users(league_id: str) -> list[dict]:
    lid = (league_id or "").strip()
    if not lid:
        return []
    try:
        data = _get_json(f"{SLEEPER_BASE}/league/{lid}/users")
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def load_players_nfl_cached(cache_path: str, max_age_seconds: int = 86400) -> dict | None:
    """
    Sleeper's full NFL players map is large (~JSON several MB). Cache on disk and refresh periodically.
    Returns None if fetch fails and no cache exists.
    """
    d = os.path.dirname(cache_path)
    if d:
        os.makedirs(d, exist_ok=True)
    now = time.time()
    if os.path.isfile(cache_path):
        try:
            age = now - os.path.getmtime(cache_path)
            if age < max_age_seconds:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, OSError):
            pass

    try:
        data = _get_json(f"{SLEEPER_BASE}/players/nfl", timeout=120.0)
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, OSError):
        if os.path.isfile(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return None

    if isinstance(data, dict):
        try:
            tmp = cache_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(tmp, cache_path)
        except OSError:
            pass
        return data
    return None
