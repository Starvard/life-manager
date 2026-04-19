"""Read/write helpers for ``routines.yaml``.

``load_routines`` is hot — it is called from every dashboard / cards / API
request, sometimes multiple times in the same request via ``card_store``.
Re-parsing YAML each time was a measurable CPU + memory cost on Fly.io's
256 MB shared-CPU instance, so we cache the parsed dict and invalidate
based on file mtime.
"""

import copy
import os
import threading

import yaml

from config import ROUTINES_FILE


_cache_lock = threading.Lock()
_cached_mtime: float | None = None
_cached_data: dict | None = None


def _load_from_disk() -> dict:
    if not os.path.exists(ROUTINES_FILE):
        return {"areas": {}}
    with open(ROUTINES_FILE, "r") as f:
        return yaml.safe_load(f) or {"areas": {}}


def load_routines():
    """Return the parsed routines dict.

    Result is cached and invalidated when ``routines.yaml`` mtime changes.
    The cached object is shared between callers, so callers should treat the
    return value as read-mostly. Mutating callers go through ``save_routines``
    which refreshes the cache atomically.
    """
    global _cached_mtime, _cached_data
    try:
        mtime = os.path.getmtime(ROUTINES_FILE)
    except OSError:
        mtime = None

    with _cache_lock:
        if _cached_data is not None and _cached_mtime == mtime:
            return _cached_data
        data = _load_from_disk()
        _cached_data = data
        _cached_mtime = mtime
        return data


def save_routines(data):
    global _cached_mtime, _cached_data
    with open(ROUTINES_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    with _cache_lock:
        _cached_data = copy.deepcopy(data)
        try:
            _cached_mtime = os.path.getmtime(ROUTINES_FILE)
        except OSError:
            _cached_mtime = None


def get_area(area_key):
    data = load_routines()
    return data.get("areas", {}).get(area_key)


def update_area(area_key, area_data):
    data = load_routines()
    data.setdefault("areas", {})[area_key] = area_data
    save_routines(data)


def delete_area(area_key):
    data = load_routines()
    data.get("areas", {}).pop(area_key, None)
    save_routines(data)


def add_task(area_key, task):
    data = load_routines()
    area = data.get("areas", {}).get(area_key)
    if area is None:
        return False
    area.setdefault("tasks", []).append(task)
    save_routines(data)
    return True


def remove_task(area_key, task_index):
    data = load_routines()
    area = data.get("areas", {}).get(area_key)
    if area is None:
        return False
    tasks = area.get("tasks", [])
    if 0 <= task_index < len(tasks):
        tasks.pop(task_index)
        save_routines(data)
        return True
    return False


def update_task(area_key, task_index, task_data):
    data = load_routines()
    area = data.get("areas", {}).get(area_key)
    if area is None:
        return False
    tasks = area.get("tasks", [])
    if 0 <= task_index < len(tasks):
        tasks[task_index] = task_data
        save_routines(data)
        return True
    return False
