"""Navigation visibility (sidebar + mobile bottom tabs), stored as JSON under data/."""

from __future__ import annotations

import copy
import json
import os
import threading

import config

_lock = threading.Lock()
_cache: tuple[float | None, dict] | None = None

NAV_TAB_KEYS: tuple[str, ...] = (
    "home",
    "cards",
    "baby",
    "cleaning",
    "budget",
    "fantasy",
    "recipes",
    "research",
    "game",
)

# Home is where hidden tabs can be restored, so it is intentionally not hideable.
HIDEABLE_NAV_TAB_KEYS: tuple[str, ...] = tuple(k for k in NAV_TAB_KEYS if k != "home")

NAV_TAB_LABELS: dict[str, str] = {
    "home": "Home",
    "cards": "Routines",
    "baby": "Baby",
    "cleaning": "Cleaning",
    "budget": "Budget",
    "fantasy": "Fantasy",
    "recipes": "Recipes",
    "research": "Research",
    "game": "Cat Dash",
}

DEFAULT_STATE: dict = {
    "version": 3,
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
        if k in HIDEABLE_NAV_TAB_KEYS and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _mtime(path: str) -> float | None:
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def _copy_state(data: dict) -> dict:
    out = copy.deepcopy(data)
    out["hidden"] = _normalize_hidden(out.get("hidden"))
    return out


def _load() -> dict:
    global _cache
    path = config.NAV_PREFS_FILE
    mtime = _mtime(path)
    if _cache is not None and _cache[0] == mtime:
        return _copy_state(_cache[1])

    if not os.path.isfile(path):
        out = dict(DEFAULT_STATE)
    else:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                out = dict(DEFAULT_STATE)
            else:
                out = dict(DEFAULT_STATE)
                out.update(data)
        except (json.JSONDecodeError, OSError):
            out = dict(DEFAULT_STATE)

    out = _copy_state(out)
    _cache = (mtime, _copy_state(out))
    return out


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
    global _cache
    norm = _normalize_hidden(hidden)
    with _lock:
        data = _load()
        data["hidden"] = norm
        _save(data)
        _cache = (_mtime(config.NAV_PREFS_FILE), _copy_state(data))
        return list(norm)
