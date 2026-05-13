"""Read/write helpers for ``routines.yaml``.

``load_routines`` is hot — it is called from every dashboard / cards / API
request, sometimes multiple times in the same request via ``card_store``.
Re-parsing YAML each time was a measurable CPU + memory cost on Fly.io's
256 MB shared-CPU instance, so we cache the parsed dict and invalidate
based on file mtime.
"""

import copy
import os
import shutil
import threading

import yaml

from config import ROUTINES_BUNDLED_FILE, ROUTINES_FILE
from services.routine_daily_restore import restore_may10_daily_routines


_cache_lock = threading.Lock()
_cached_mtime: float | None = None
_cached_data: dict | None = None

RESTORE_HOME_RECURRING_MIGRATION = "restore_home_recurring_tasks_2026_04_29"
RESTORED_HOME_RECURRING_TASKS = [
    {"name": "Deep Clean Upstairs", "weight": 2.0, "freq": 0.5},
    {"name": "Deep Clean Downstairs", "weight": 2.0, "freq": 0.5},
    {"name": "HVAC Maintenance", "weight": 1.5, "freq": 0.038},
    {"name": "Knife Sharpening", "weight": 1.0, "freq": 0.077},
]


def _ensure_routines_file() -> None:
    """Seed the persistent routines.yaml from the bundled image copy on first run.

    On Fly.io the user-editable file lives on the persistent volume
    (``LM_DATA_DIR``) so edits survive machine restarts. The bundled file in
    the repo image is only used as a first-boot template.
    """
    if os.path.exists(ROUTINES_FILE):
        return
    if ROUTINES_FILE == ROUTINES_BUNDLED_FILE:
        return
    if os.path.exists(ROUTINES_BUNDLED_FILE):
        os.makedirs(os.path.dirname(ROUTINES_FILE), exist_ok=True)
        shutil.copy2(ROUTINES_BUNDLED_FILE, ROUTINES_FILE)


def _load_from_disk() -> dict:
    _ensure_routines_file()
    if not os.path.exists(ROUTINES_FILE):
        return {"areas": {}}
    with open(ROUTINES_FILE, "r") as f:
        return yaml.safe_load(f) or {"areas": {}}


def _write_to_disk(data: dict) -> None:
    os.makedirs(os.path.dirname(ROUTINES_FILE) or ".", exist_ok=True)
    with open(ROUTINES_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _apply_one_time_routine_repairs(data: dict) -> bool:
    """Apply small, one-time data repairs to the persistent routine config.

    This is intentionally guarded by a migration marker so restored tasks do
    not keep coming back if the user later deletes them from the inline editor.
    """
    migrations = data.setdefault("_migrations", [])
    changed = False

    if RESTORE_HOME_RECURRING_MIGRATION not in migrations:
        areas = data.setdefault("areas", {})
        home = areas.setdefault("home", {"name": "Home", "tasks": []})
        home.setdefault("name", "Home")
        tasks = home.setdefault("tasks", [])
        by_name = {str(t.get("name", "")).strip().lower(): t for t in tasks if isinstance(t, dict)}

        for default_task in RESTORED_HOME_RECURRING_TASKS:
            key = default_task["name"].strip().lower()
            existing = by_name.get(key)
            if existing is None:
                tasks.append(copy.deepcopy(default_task))
                by_name[key] = tasks[-1]
                changed = True
                continue

            # Older versions had some long-interval tasks only as freq_per_year.
            # The current inline recurring UI works from freq, so add a weekly
            # equivalent while preserving any existing fields.
            if "freq" not in existing:
                existing["freq"] = default_task["freq"]
                changed = True
            if "weight" not in existing and "weight" in default_task:
                existing["weight"] = default_task["weight"]
                changed = True

        migrations.append(RESTORE_HOME_RECURRING_MIGRATION)
        changed = True

    if restore_may10_daily_routines(data):
        changed = True

    return changed


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
        if _apply_one_time_routine_repairs(data):
            _write_to_disk(data)
            try:
                mtime = os.path.getmtime(ROUTINES_FILE)
            except OSError:
                mtime = None
        _cached_data = data
        _cached_mtime = mtime
        return data


def save_routines(data):
    global _cached_mtime, _cached_data
    _write_to_disk(data)
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
