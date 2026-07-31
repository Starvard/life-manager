"""
Pup Patrol Cat Dash — leaderboard storage.

Stores up to N high scores as a JSON list under data/pup_patrol_scores.json.
Each entry: {name, score, ts}.
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

import config

_lock = threading.Lock()

MAX_SCORES = 50
NAME_MAX_LEN = 16

DEFAULT_STATE: dict = {"version": 1, "scores": []}


def _path() -> str:
    return os.path.join(config.DATA_DIR, "pup_patrol_scores.json")


def _load() -> dict:
    p = _path()
    if not os.path.isfile(p):
        return {"version": 1, "scores": []}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"version": 1, "scores": []}
        scores = data.get("scores")
        if not isinstance(scores, list):
            scores = []
        clean: list[dict] = []
        for s in scores:
            if not isinstance(s, dict):
                continue
            try:
                score = int(s.get("score", 0))
            except (TypeError, ValueError):
                continue
            name = str(s.get("name", "")).strip()[:NAME_MAX_LEN] or "Anon"
            ts = s.get("ts")
            if not isinstance(ts, (int, float)):
                ts = time.time()
            clean.append({"name": name, "score": score, "ts": float(ts)})
        return {"version": 1, "scores": clean}
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "scores": []}


def _save(data: dict) -> None:
    p = _path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, p)


def _sorted_top(scores: list[dict], limit: int = MAX_SCORES) -> list[dict]:
    return sorted(scores, key=lambda s: (-int(s.get("score", 0)), float(s.get("ts", 0))))[:limit]


def list_top_scores(limit: int = 10) -> list[dict]:
    with _lock:
        data = _load()
        return _sorted_top(list(data.get("scores", [])), limit=limit)


def add_score(name: str, score: int) -> dict[str, Any]:
    """Append a score. Returns {ok, rank, top: [...]}. Rank is 1-based among all stored."""
    try:
        score_int = int(score)
    except (TypeError, ValueError):
        return {"ok": False, "error": "invalid_score"}
    if score_int < 0 or score_int > 10_000_000:
        return {"ok": False, "error": "invalid_score"}
    clean_name = (name or "").strip()[:NAME_MAX_LEN] or "Anon"
    entry = {"name": clean_name, "score": score_int, "ts": time.time()}
    with _lock:
        data = _load()
        all_scores = list(data.get("scores", []))
        all_scores.append(entry)
        all_scores = _sorted_top(all_scores, limit=MAX_SCORES)
        data["scores"] = all_scores
        _save(data)
        rank = next(
            (i + 1 for i, s in enumerate(all_scores) if s is entry or (
                s["name"] == entry["name"]
                and s["score"] == entry["score"]
                and abs(s["ts"] - entry["ts"]) < 0.01
            )),
            None,
        )
        return {
            "ok": True,
            "rank": rank,
            "top": all_scores[:10],
        }
