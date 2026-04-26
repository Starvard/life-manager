"""Simple room-based cleaning checklist storage.

The checklist itself is intentionally static and clean. Completed state is
stored separately under DATA_DIR so deploys can update the template without
destroying checkmarks.
"""

from __future__ import annotations

import json
import os
import re
import threading
from copy import deepcopy
from typing import Any

import config

_lock = threading.Lock()

STATE_FILE = os.path.join(config.DATA_DIR, "cleaning_checklist.json")


def _slug(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


ROOMS: list[dict[str, Any]] = [
    {
        "name": "Primary Bathroom",
        "note": "Former BR1 / office-side bathroom.",
        "tasks": [
            "Wipe window glass, frame, and sill",
            "Clean picture frames",
            "Scrub sink and counter",
            "Scrub toilet: bowl, base, tank, and behind",
            "Scrub tub/shower: walls, grout, and floor",
            "Clean mirror and backsplash",
            "Spot-clean walls near switches and fixtures",
            "Scrub baseboards",
            "Clean door and door frame",
            "Wipe switches and handles",
            "Vacuum edges and mop floor",
        ],
    },
    {
        "name": "Kitchen",
        "tasks": [
            "Clear and clean countertops",
            "Clean backsplash",
            "Degrease cabinet fronts and hardware",
            "Scrub sink",
            "Clean microwave inside and out",
            "Wipe fridge exterior",
            "Wipe stove and range hood",
            "Clean window, sill, and picture frames",
            "Scrub baseboards and kickplates",
            "Spot-clean walls around cooking zones",
            "Clean switches and door frame",
            "Mop floor",
        ],
    },
    {
        "name": "Living Room",
        "tasks": [
            "Clean windows, frames, and sills",
            "Clean picture frames and wall art",
            "Wipe down furniture",
            "Dust/wipe electronics",
            "Scrub baseboards",
            "Spot-clean walls and corners",
            "Clean doors and frames",
            "Wipe switches and handles",
            "Vacuum floor and edges",
            "Mop or damp-clean floor",
        ],
    },
    {
        "name": "Stairs",
        "tasks": [
            "Vacuum each step and landing thoroughly",
            "Spot-clean walls and handrail",
            "Scrub baseboards and corners",
            "Clean light switches and trim at top and bottom",
        ],
    },
    {
        "name": "Mudroom",
        "tasks": [
            "Wipe door, frame, and handle",
            "Clean window and picture frames",
            "Wipe down furniture",
            "Scrub baseboards and corners",
            "Spot-clean walls",
            "Wipe switches",
            "Vacuum thoroughly",
            "Mop floor",
        ],
    },
    {
        "name": "Bedroom 2",
        "tasks": [
            "Wipe window and picture frames",
            "Wipe nightstand, dresser, and shelves",
            "Scrub baseboards",
            "Spot-clean walls",
            "Clean switches and handles",
            "Clean door and frame",
            "Vacuum and edge-clean",
            "Mop or damp-clean floor",
        ],
    },
    {
        "name": "Bedroom 2 Bathroom",
        "tasks": [
            "Clean window and picture frames",
            "Scrub sink and counter",
            "Scrub toilet",
            "Scrub tub/shower",
            "Clean mirror and backsplash",
            "Spot-clean walls",
            "Scrub baseboards",
            "Clean door and switches",
            "Vacuum edges and mop floor",
        ],
    },
    {
        "name": "Bedroom 3",
        "note": "Former office.",
        "tasks": [
            "Wipe window glass, frame, and sill",
            "Clean picture frames and wall art",
            "Wipe furniture surfaces",
            "Wipe shelves, chair legs, and any desk surfaces",
            "Scrub baseboards and wall corners",
            "Spot-clean walls, especially near light switches",
            "Clean light switch and door handle",
            "Clean door and door frame",
            "Vacuum floor and edges thoroughly",
            "Mop or damp-wipe floor",
        ],
    },
    {
        "name": "Bedroom 3 Bathroom",
        "tasks": [
            "Wipe window and picture frames",
            "Scrub sink and counter",
            "Scrub toilet",
            "Scrub tub/shower",
            "Clean mirror and backsplash",
            "Spot-clean walls",
            "Scrub baseboards",
            "Clean door and switches",
            "Vacuum and mop floor",
        ],
    },
]


def _rooms_with_ids() -> list[dict[str, Any]]:
    rooms = deepcopy(ROOMS)
    for room in rooms:
        room_id = _slug(room["name"])
        room["id"] = room_id
        task_objs = []
        for task in room["tasks"]:
            task_id = f"{room_id}:{_slug(task)}"
            task_objs.append({"id": task_id, "name": task})
        room["tasks"] = task_objs
    return rooms


def _default_state() -> dict[str, Any]:
    return {"version": 1, "completed": {}}


def _load_state() -> dict[str, Any]:
    if not os.path.isfile(STATE_FILE):
        return _default_state()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            return _default_state()
        completed = raw.get("completed")
        if not isinstance(completed, dict):
            completed = {}
        return {
            "version": 1,
            "completed": {str(k): bool(v) for k, v in completed.items()},
        }
    except (OSError, json.JSONDecodeError):
        return _default_state()


def _save_state(state: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp, STATE_FILE)


def get_cleaning_state() -> dict[str, Any]:
    with _lock:
        state = _load_state()

    rooms = _rooms_with_ids()
    completed = state.get("completed", {})
    total = 0
    done = 0
    for room in rooms:
        room_total = len(room["tasks"])
        room_done = 0
        for task in room["tasks"]:
            is_done = bool(completed.get(task["id"]))
            task["done"] = is_done
            if is_done:
                room_done += 1
        total += room_total
        done += room_done
        room["total"] = room_total
        room["done"] = room_done
        room["percent"] = round((room_done / room_total) * 100) if room_total else 0

    return {
        "rooms": rooms,
        "total": total,
        "done": done,
        "remaining": max(0, total - done),
        "percent": round((done / total) * 100) if total else 0,
    }


def set_task_done(task_id: str, done: bool) -> bool:
    valid_ids = {
        task["id"]
        for room in _rooms_with_ids()
        for task in room["tasks"]
    }
    if task_id not in valid_ids:
        return False

    with _lock:
        state = _load_state()
        completed = state.setdefault("completed", {})
        if done:
            completed[task_id] = True
        else:
            completed.pop(task_id, None)
        _save_state(state)
    return True


def clear_room(room_id: str) -> bool:
    valid_rooms = {room["id"] for room in _rooms_with_ids()}
    if room_id not in valid_rooms:
        return False
    prefix = f"{room_id}:"
    with _lock:
        state = _load_state()
        completed = state.setdefault("completed", {})
        for task_id in list(completed.keys()):
            if task_id.startswith(prefix):
                completed.pop(task_id, None)
        _save_state(state)
    return True


def reset_all() -> None:
    with _lock:
        _save_state(_default_state())
