"""
Local JSON storage for fantasy football planning (Sleeper snapshot + notes).

File: data/fantasy/sleeper_fantasy.json
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import date

import config

DEFAULT_USERNAME = "starvard"
DEFAULT_LEAGUE_NAME_HINT = "Sergio Dipp"

_file_lock = threading.Lock()
DEFAULT_STATE: dict = {
    "version": 2,
    "settings": {
        "sleeper_username": DEFAULT_USERNAME,
        "sport": "nfl",
        "season": str(date.today().year),
        "league_id": "",
        "league_name_hint": DEFAULT_LEAGUE_NAME_HINT,
        # Match FantasyCalc query (Sergio Dipp is superflex 12)
        "valuation_num_qbs": 2,
        "valuation_num_teams": 12,
        "valuation_ppr": 1.0,
        "trade_strategy": "rebuild",
    },
    "plan": {
        "draft_notes": "",
        "trade_targets": "",
        "rebuild_notes": "",
        "trade_ideas": [],
    },
    "last_sync": None,
    "cached_snapshot": None,
    "trade_suggestions": None,
    "last_trade_refresh": None,
    "last_trade_error": None,
}


def _path() -> str:
    d = os.path.join(config.DATA_DIR, "fantasy")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "sleeper_fantasy.json")


def load_state() -> dict:
    path = _path()
    with _file_lock:
        if not os.path.isfile(path):
            state = json.loads(json.dumps(DEFAULT_STATE))
            _write_unlocked(path, state)
            return state
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}
    if not isinstance(data, dict):
        data = {}
    merged = json.loads(json.dumps(DEFAULT_STATE))
    merged.update(data)
    if "settings" in data and isinstance(data["settings"], dict):
        merged["settings"] = {**merged["settings"], **data["settings"]}
    if "plan" in data and isinstance(data["plan"], dict):
        merged["plan"] = {**merged["plan"], **data["plan"]}
    for k in ("trade_suggestions", "last_trade_refresh", "last_trade_error"):
        if k in data:
            merged[k] = data[k]
    return merged


def save_state(state: dict):
    path = _path()
    with _file_lock:
        _write_unlocked(path, state)


def _write_unlocked(path: str, state: dict):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def update_settings(updates: dict) -> dict:
    state = load_state()
    s = state.setdefault("settings", {})
    for k, v in updates.items():
        if v is None:
            continue
        if k in ("sleeper_username", "sport", "season", "league_id", "league_name_hint", "trade_strategy"):
            s[k] = str(v).strip() if isinstance(v, str) else v
        elif k == "valuation_num_qbs":
            try:
                s[k] = max(1, min(2, int(v)))
            except (TypeError, ValueError):
                pass
        elif k == "valuation_num_teams":
            try:
                s[k] = max(8, min(16, int(v)))
            except (TypeError, ValueError):
                pass
        elif k == "valuation_ppr":
            try:
                s[k] = float(v)
            except (TypeError, ValueError):
                pass
    save_state(state)
    return state


def update_plan(updates: dict) -> dict:
    state = load_state()
    p = state.setdefault("plan", {})
    for k in ("draft_notes", "trade_targets", "rebuild_notes"):
        if k in updates and updates[k] is not None:
            p[k] = str(updates[k])
    if "trade_ideas" in updates and isinstance(updates["trade_ideas"], list):
        p["trade_ideas"] = updates["trade_ideas"]
    save_state(state)
    return state


def add_trade_idea(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        return load_state()
    state = load_state()
    ideas = state.setdefault("plan", {}).setdefault("trade_ideas", [])
    ideas.append({"id": str(uuid.uuid4()), "text": text, "created": date.today().isoformat()})
    save_state(state)
    return state


def remove_trade_idea(idea_id: str) -> dict:
    state = load_state()
    ideas = state.setdefault("plan", {}).setdefault("trade_ideas", [])
    state["plan"]["trade_ideas"] = [i for i in ideas if i.get("id") != idea_id]
    save_state(state)
    return state


def apply_sync_snapshot(snapshot: dict):
    state = load_state()
    state["last_sync"] = snapshot.get("synced_at")
    state["cached_snapshot"] = snapshot
    save_state(state)


def apply_trade_refresh(payload: dict):
    """Store result from fantasy_trade_engine.run_trade_refresh."""
    state = load_state()
    state["trade_suggestions"] = payload
    state["last_trade_refresh"] = payload.get("generated_at")
    state["last_trade_error"] = None
    save_state(state)


def apply_trade_error(message: str):
    state = load_state()
    state["last_trade_error"] = message
    save_state(state)
