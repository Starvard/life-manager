"""Navigation visibility (sidebar + mobile bottom tabs), stored as JSON under data/."""

from __future__ import annotations

import json
import os
import threading

import config

_lock = threading.Lock()

# Keys must match data-nav-tab on links in base.html (except "edit" is the Routines page).
NAV_TAB_KEYS: tuple[str, ...] = (
    "home",
    "cards",
    "baby",
    "budget",
    "fantasy",
    "recipes",
    "research",
    "game",
    "edit",
)

NAV_TAB_LABELS: dict[str, str] = {
    "home": "Home",
    "cards": "Cards",
    "baby": "Baby",
    "budget": "Budget",
    "fantasy": "Fantasy",
    "recipes": "Recipes",
    "research": "Research",
    "game": "Pup Patrol Cat Dash",
    "edit": "Edit (routines)",
}

DEFAULT_STATE: dict = {
    "version": 1,
    "hidden": [],
}


def _normalize_hidden(raw: list | None) -> list[str]:
    if not raw:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for x in raw:
        if not isinstance(x, str):
            continue
        k = x.strip().lower()
        if k in NAV_TAB_KEYS and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _load() -> dict:
    path = config.NAV_PREFS_FILE
    if not os.path.isfile(path):
        return dict(DEFAULT_STATE)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return dict(DEFAULT_STATE)
        out = dict(DEFAULT_STATE)
        out.update(data)
        hidden = out.get("hidden")
        if isinstance(hidden, list):
            out["hidden"] = _normalize_hidden(hidden)
        else:
            out["hidden"] = []
        return out
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_STATE)


def _save(data: dict) -> None:
    path = config.NAV_PREFS_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def get_hidden_nav_tabs() -> list[str]:
    with _lock:
        return list(_load().get("hidden") or [])


def set_hidden_nav_tabs(hidden: list[str]) -> list[str]:
    """Replace hidden tab list. Unknown keys are dropped. Returns normalized list."""
    norm = _normalize_hidden(hidden)
    # Keep at least one tab visible so the app stays reachable (Edit restores visibility).
    if len(norm) >= len(NAV_TAB_KEYS):
        norm = norm[: len(NAV_TAB_KEYS) - 1]
    with _lock:
        data = _load()
        data["hidden"] = norm
        _save(data)
        return norm
