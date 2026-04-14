"""Persist Web Push subscription objects (JSON file)."""

from __future__ import annotations

import json
import os
import threading

import config

_lock = threading.Lock()


def _load_raw() -> list[dict]:
    path = config.PUSH_SUBSCRIPTIONS_FILE
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_raw(subs: list[dict]) -> None:
    path = config.PUSH_SUBSCRIPTIONS_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(subs, f, indent=2)
    os.replace(tmp, path)


def list_subscriptions() -> list[dict]:
    with _lock:
        return list(_load_raw())


def add_subscription(sub: dict) -> None:
    """sub is PushSubscription.toJSON() shape: endpoint + keys."""
    endpoint = sub.get("endpoint")
    if not endpoint:
        return
    with _lock:
        subs = _load_raw()
        subs = [s for s in subs if s.get("endpoint") != endpoint]
        subs.append(sub)
        _save_raw(subs)


def remove_subscription(endpoint: str) -> bool:
    with _lock:
        subs = _load_raw()
        n = len(subs)
        subs = [s for s in subs if s.get("endpoint") != endpoint]
        if len(subs) == n:
            return False
        _save_raw(subs)
        return True
