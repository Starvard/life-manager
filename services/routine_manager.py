import yaml
import os
from config import ROUTINES_FILE


def load_routines():
    if not os.path.exists(ROUTINES_FILE):
        return {"areas": {}}
    with open(ROUTINES_FILE, "r") as f:
        return yaml.safe_load(f) or {"areas": {}}


def save_routines(data):
    with open(ROUTINES_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


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
