"""
Home Recipes module — file-backed storage for recipes, grocery list,
pantry/inventory, and the weekly menu.

Files (under data/recipes/):
    recipes.json     list[recipe]
    grocery.json     {"items": [item]}
    inventory.json   {"items": [item]}
    meal_plan.json   {"weeks": {"YYYY-Www": {"breakfast": [entry], "lunch": [...], "dinner": [...]}}}

The "menu" model deliberately avoids per-day slots: each week has a small
pool of breakfasts / lunches / dinners that the household picks from. This
matches the "1-2 breakfasts, 1-2 lunches, 4-6 dinners" workflow.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, date, timedelta

import config

RECIPES_DIR = os.path.join(config.DATA_DIR, "recipes")
RECIPES_FILE = os.path.join(RECIPES_DIR, "recipes.json")
GROCERY_FILE = os.path.join(RECIPES_DIR, "grocery.json")
INVENTORY_FILE = os.path.join(RECIPES_DIR, "inventory.json")
MEAL_PLAN_FILE = os.path.join(RECIPES_DIR, "meal_plan.json")

MENU_SLOTS = ["breakfast", "lunch", "dinner"]
MENU_SLOT_TARGETS = {
    "breakfast": {"min": 1, "max": 2},
    "lunch": {"min": 1, "max": 2},
    "dinner": {"min": 4, "max": 6},
}
DEFAULT_CATEGORIES = [
    "Produce",
    "Meat & Seafood",
    "Dairy",
    "Bakery",
    "Pantry",
    "Frozen",
    "Beverages",
    "Snacks",
    "Household",
    "Other",
]

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(path: str) -> threading.Lock:
    with _locks_guard:
        if path not in _locks:
            _locks[path] = threading.Lock()
        return _locks[path]


def _ensure_dir():
    os.makedirs(RECIPES_DIR, exist_ok=True)


def _load(path: str, default):
    _ensure_dir()
    with _lock_for(path):
        if not os.path.isfile(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default


def _save(path: str, data):
    _ensure_dir()
    with _lock_for(path):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


# ── Recipes ──────────────────────────────────────────────────────

def list_recipes() -> list[dict]:
    data = _load(RECIPES_FILE, [])
    if not isinstance(data, list):
        return []
    return data


def get_recipe(recipe_id: str) -> dict | None:
    for r in list_recipes():
        if r.get("id") == recipe_id:
            return r
    return None


def _normalize_ingredient(raw) -> dict | None:
    """Coerce ingredient input to {name, qty, unit}."""
    if isinstance(raw, str):
        name = raw.strip()
        if not name:
            return None
        return {"name": name, "qty": "", "unit": ""}
    if not isinstance(raw, dict):
        return None
    name = (raw.get("name") or "").strip()
    if not name:
        return None
    return {
        "name": name,
        "qty": str(raw.get("qty", "")).strip(),
        "unit": (raw.get("unit") or "").strip(),
    }


def _normalize_instruction(raw) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()
    return s or None


def _coerce_recipe(payload: dict, *, existing: dict | None = None) -> dict:
    base: dict = dict(existing) if existing else {}
    base.setdefault("id", _new_id())
    base.setdefault("created", _now_iso())
    base["updated"] = _now_iso()

    base["name"] = (payload.get("name") or base.get("name") or "Untitled recipe").strip() or "Untitled recipe"
    base["source"] = (payload.get("source") or base.get("source") or "manual").strip()
    base["source_url"] = (payload.get("source_url") or base.get("source_url") or "").strip()
    base["image_url"] = (payload.get("image_url") or base.get("image_url") or "").strip()
    base["servings"] = (payload.get("servings") or base.get("servings") or "").strip() if isinstance(
        payload.get("servings", base.get("servings", "")), str
    ) else str(payload.get("servings") or base.get("servings") or "")
    base["prep_time"] = (payload.get("prep_time") or base.get("prep_time") or "").strip()
    base["cook_time"] = (payload.get("cook_time") or base.get("cook_time") or "").strip()
    base["notes"] = payload.get("notes", base.get("notes", "")) or ""
    tags = payload.get("tags", base.get("tags", []))
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    base["tags"] = [t for t in (tags or []) if isinstance(t, str)]

    ingredients = payload.get("ingredients", base.get("ingredients", []))
    if isinstance(ingredients, str):
        ingredients = [i for i in ingredients.splitlines() if i.strip()]
    norm = []
    for raw in ingredients or []:
        n = _normalize_ingredient(raw)
        if n:
            norm.append(n)
    base["ingredients"] = norm

    instructions = payload.get("instructions", base.get("instructions", []))
    if isinstance(instructions, str):
        instructions = [s for s in instructions.split("\n") if s.strip()]
    base["instructions"] = [s for s in (
        _normalize_instruction(x) for x in (instructions or [])
    ) if s]
    return base


def create_recipe(payload: dict) -> dict:
    recipe = _coerce_recipe(payload)
    recipes = list_recipes()
    recipes.append(recipe)
    _save(RECIPES_FILE, recipes)
    return recipe


def update_recipe(recipe_id: str, payload: dict) -> dict | None:
    recipes = list_recipes()
    for i, r in enumerate(recipes):
        if r.get("id") == recipe_id:
            updated = _coerce_recipe(payload, existing=r)
            updated["id"] = recipe_id
            recipes[i] = updated
            _save(RECIPES_FILE, recipes)
            return updated
    return None


def delete_recipe(recipe_id: str) -> bool:
    recipes = list_recipes()
    new = [r for r in recipes if r.get("id") != recipe_id]
    if len(new) == len(recipes):
        return False
    _save(RECIPES_FILE, new)
    return True


def search_recipes_local(query: str) -> list[dict]:
    q = (query or "").strip().lower()
    if not q:
        return list_recipes()
    out = []
    for r in list_recipes():
        hay = " ".join([
            r.get("name", ""),
            " ".join(r.get("tags", []) or []),
            " ".join(i.get("name", "") for i in r.get("ingredients", [])),
        ]).lower()
        if q in hay:
            out.append(r)
    return out


# ── Grocery list ─────────────────────────────────────────────────

def _load_grocery() -> dict:
    data = _load(GROCERY_FILE, {"items": []})
    if not isinstance(data, dict):
        data = {"items": []}
    data.setdefault("items", [])
    return data


def list_grocery() -> list[dict]:
    return _load_grocery().get("items", [])


def add_grocery_item(payload: dict) -> dict:
    item = {
        "id": _new_id(),
        "name": (payload.get("name") or "").strip(),
        "qty": str(payload.get("qty", "")).strip(),
        "unit": (payload.get("unit") or "").strip(),
        "category": (payload.get("category") or "Other").strip(),
        "checked": bool(payload.get("checked", False)),
        "recipe_id": payload.get("recipe_id") or None,
        "added": _now_iso(),
    }
    if not item["name"]:
        raise ValueError("name required")
    data = _load_grocery()
    data["items"].append(item)
    _save(GROCERY_FILE, data)
    return item


def update_grocery_item(item_id: str, payload: dict) -> dict | None:
    data = _load_grocery()
    for it in data["items"]:
        if it.get("id") == item_id:
            for key in ("name", "qty", "unit", "category"):
                if key in payload:
                    it[key] = str(payload[key]).strip() if payload[key] is not None else ""
            if "checked" in payload:
                it["checked"] = bool(payload["checked"])
            _save(GROCERY_FILE, data)
            return it
    return None


def delete_grocery_item(item_id: str) -> bool:
    data = _load_grocery()
    before = len(data["items"])
    data["items"] = [it for it in data["items"] if it.get("id") != item_id]
    if len(data["items"]) == before:
        return False
    _save(GROCERY_FILE, data)
    return True


def clear_grocery_checked() -> int:
    data = _load_grocery()
    keep = [it for it in data["items"] if not it.get("checked")]
    removed = len(data["items"]) - len(keep)
    data["items"] = keep
    _save(GROCERY_FILE, data)
    return removed


def add_recipe_ingredients_to_grocery(recipe_id: str) -> dict:
    """Push every ingredient of the recipe onto the grocery list, skipping
    items already in inventory or already on the list.

    Returns {added, on_hand, on_list, skipped, recipe_name}.
    `skipped` = `on_hand + on_list` (kept for backwards compatibility)."""
    recipe = get_recipe(recipe_id)
    if not recipe:
        return {"added": 0, "on_hand": 0, "on_list": 0, "skipped": 0, "error": "Recipe not found"}

    inv_names = {(i.get("name") or "").lower().strip() for i in list_inventory()}
    data = _load_grocery()
    existing_names = {(it.get("name") or "").lower().strip() for it in data["items"]}
    added, on_hand, on_list = 0, 0, 0
    for ing in recipe.get("ingredients", []):
        name = (ing.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in inv_names:
            on_hand += 1
            continue
        if key in existing_names:
            on_list += 1
            continue
        item = {
            "id": _new_id(),
            "name": name,
            "qty": str(ing.get("qty", "")).strip(),
            "unit": (ing.get("unit") or "").strip(),
            "category": "Other",
            "checked": False,
            "recipe_id": recipe_id,
            "added": _now_iso(),
        }
        data["items"].append(item)
        existing_names.add(key)
        added += 1
    _save(GROCERY_FILE, data)
    return {
        "added": added,
        "on_hand": on_hand,
        "on_list": on_list,
        "skipped": on_hand + on_list,
        "recipe_name": recipe.get("name", ""),
    }


def move_checked_grocery_to_inventory() -> dict:
    """Convert all checked grocery items into inventory entries; remove from grocery.
    Returns {moved, skipped}."""
    data = _load_grocery()
    inv = _load_inventory()
    moved = 0
    keep = []
    inv_names = {(i.get("name") or "").lower().strip(): i for i in inv["items"]}
    for it in data["items"]:
        if it.get("checked"):
            name = it.get("name", "").strip()
            if not name:
                continue
            existing = inv_names.get(name.lower())
            if existing:
                # bump quantity if both have numeric qty same unit
                existing["updated"] = _now_iso()
                if it.get("qty"):
                    if existing.get("qty") and existing.get("unit") == it.get("unit"):
                        try:
                            existing["qty"] = str(float(existing["qty"]) + float(it["qty"]))
                        except (TypeError, ValueError):
                            existing["qty"] = (existing.get("qty") or "") + " + " + str(it.get("qty"))
                    else:
                        existing["qty"] = str(it.get("qty"))
                        existing["unit"] = it.get("unit", "")
            else:
                inv["items"].append({
                    "id": _new_id(),
                    "name": name,
                    "qty": str(it.get("qty", "")).strip(),
                    "unit": (it.get("unit") or "").strip(),
                    "category": (it.get("category") or "Other").strip(),
                    "expires": "",
                    "updated": _now_iso(),
                })
            moved += 1
        else:
            keep.append(it)
    data["items"] = keep
    _save(GROCERY_FILE, data)
    _save(INVENTORY_FILE, inv)
    return {"moved": moved}


# ── Inventory ────────────────────────────────────────────────────

def _load_inventory() -> dict:
    data = _load(INVENTORY_FILE, {"items": []})
    if not isinstance(data, dict):
        data = {"items": []}
    data.setdefault("items", [])
    return data


def list_inventory() -> list[dict]:
    return _load_inventory().get("items", [])


def add_inventory_item(payload: dict) -> dict:
    name = (payload.get("name") or "").strip()
    if not name:
        raise ValueError("name required")
    item = {
        "id": _new_id(),
        "name": name,
        "qty": str(payload.get("qty", "")).strip(),
        "unit": (payload.get("unit") or "").strip(),
        "category": (payload.get("category") or "Other").strip(),
        "expires": (payload.get("expires") or "").strip(),
        "updated": _now_iso(),
    }
    inv = _load_inventory()
    inv["items"].append(item)
    _save(INVENTORY_FILE, inv)
    return item


def update_inventory_item(item_id: str, payload: dict) -> dict | None:
    inv = _load_inventory()
    for it in inv["items"]:
        if it.get("id") == item_id:
            for key in ("name", "qty", "unit", "category", "expires"):
                if key in payload:
                    it[key] = str(payload[key] or "").strip() if not isinstance(
                        payload[key], (int, float)
                    ) else str(payload[key])
            it["updated"] = _now_iso()
            _save(INVENTORY_FILE, inv)
            return it
    return None


def delete_inventory_item(item_id: str) -> bool:
    inv = _load_inventory()
    before = len(inv["items"])
    inv["items"] = [it for it in inv["items"] if it.get("id") != item_id]
    if len(inv["items"]) == before:
        return False
    _save(INVENTORY_FILE, inv)
    return True


# ── Weekly Menu ──────────────────────────────────────────────────
#
# meal_plan.json shape:
#   {
#     "weeks": {
#       "2026-W17": {
#         "breakfast": [entry, ...],
#         "lunch":     [entry, ...],
#         "dinner":    [entry, ...]
#       }
#     }
#   }
#
# An entry is {id, recipe_id|null, name, notes}.
# Weeks are ISO week keys ("YYYY-Www").

def iso_week_key(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def current_week_key() -> str:
    return iso_week_key(date.today())


def _empty_week() -> dict:
    return {slot: [] for slot in MENU_SLOTS}


def _normalize_week_key(week_key: str | None) -> str:
    if not week_key:
        return current_week_key()
    wk = str(week_key).strip()
    # very loose validation; expects "YYYY-Www"
    if "-W" not in wk:
        return current_week_key()
    return wk


def _migrate_legacy_plan(data: dict) -> dict:
    """Convert pre-v2 {days: {YYYY-MM-DD: {slot: [entries]}}} into the new
    weekly-menu shape. Each legacy entry becomes a single pool entry on
    the ISO week containing that date. Idempotent / safe to call repeatedly."""
    if not isinstance(data, dict):
        return {"weeks": {}, "version": 2}
    if "weeks" in data and isinstance(data.get("weeks"), dict):
        data.setdefault("version", 2)
        return data
    days = data.get("days") or {}
    weeks: dict[str, dict] = {}
    for day_str, day_entry in (days or {}).items():
        try:
            d = date.fromisoformat(day_str)
        except (TypeError, ValueError):
            continue
        wk = iso_week_key(d)
        bucket = weeks.setdefault(wk, _empty_week())
        if not isinstance(day_entry, dict):
            continue
        for slot, entries in day_entry.items():
            if slot not in MENU_SLOTS:
                continue
            for e in entries or []:
                if not isinstance(e, dict):
                    continue
                # de-dupe within the same slot/week by recipe_id (or by name)
                rid = e.get("recipe_id")
                name = (e.get("name") or "").strip()
                if not (rid or name):
                    continue
                already = False
                for existing in bucket[slot]:
                    if rid and existing.get("recipe_id") == rid:
                        already = True
                        break
                    if not rid and existing.get("name", "").lower() == name.lower():
                        already = True
                        break
                if already:
                    continue
                bucket[slot].append({
                    "id": e.get("id") or _new_id(),
                    "recipe_id": rid or None,
                    "name": name,
                    "notes": (e.get("notes") or "").strip(),
                })
    return {"weeks": weeks, "version": 2}


def _load_meal_plan() -> dict:
    data = _load(MEAL_PLAN_FILE, {"weeks": {}, "version": 2})
    if not isinstance(data, dict):
        data = {"weeks": {}, "version": 2}
    if "weeks" not in data:
        data = _migrate_legacy_plan(data)
        _save(MEAL_PLAN_FILE, data)
    data.setdefault("weeks", {})
    return data


def get_meal_plan() -> dict:
    return _load_meal_plan()


def get_week_menu(week_key: str | None = None) -> dict:
    wk = _normalize_week_key(week_key)
    plan = _load_meal_plan()
    week = plan.get("weeks", {}).get(wk) or _empty_week()
    # ensure all slots present
    for slot in MENU_SLOTS:
        week.setdefault(slot, [])
    return {"week_key": wk, **{slot: week[slot] for slot in MENU_SLOTS}}


def add_menu_entry(week_key: str | None, slot: str, payload: dict) -> dict | None:
    if slot not in MENU_SLOTS:
        return None
    wk = _normalize_week_key(week_key)
    name = (payload.get("name") or "").strip()
    rid = payload.get("recipe_id") or None
    if not name and rid:
        rec = get_recipe(rid)
        if rec:
            name = rec.get("name", "")
    if not name:
        return None
    plan = _load_meal_plan()
    week = plan.setdefault("weeks", {}).setdefault(wk, _empty_week())
    for s in MENU_SLOTS:
        week.setdefault(s, [])
    # de-dupe: same recipe in same slot, or same free-text name in same slot
    for existing in week[slot]:
        if rid and existing.get("recipe_id") == rid:
            return existing
        if not rid and existing.get("name", "").strip().lower() == name.lower():
            return existing
    entry = {
        "id": _new_id(),
        "recipe_id": rid,
        "name": name,
        "notes": (payload.get("notes") or "").strip(),
    }
    week[slot].append(entry)
    _save(MEAL_PLAN_FILE, plan)
    return entry


def remove_menu_entry(week_key: str | None, slot: str, entry_id: str) -> bool:
    if slot not in MENU_SLOTS:
        return False
    wk = _normalize_week_key(week_key)
    plan = _load_meal_plan()
    week = plan.get("weeks", {}).get(wk)
    if not week:
        return False
    entries = week.get(slot) or []
    new_entries = [e for e in entries if e.get("id") != entry_id]
    if len(new_entries) == len(entries):
        return False
    week[slot] = new_entries
    _save(MEAL_PLAN_FILE, plan)
    return True


def clear_week_menu(week_key: str | None) -> bool:
    wk = _normalize_week_key(week_key)
    plan = _load_meal_plan()
    if wk in plan.get("weeks", {}):
        plan["weeks"][wk] = _empty_week()
        _save(MEAL_PLAN_FILE, plan)
        return True
    return False


def add_menu_to_grocery(week_key: str | None) -> dict:
    """Add ingredients from every recipe in the week's menu to the grocery
    list. Returns granular counts so the UI can show "added X / on hand Y /
    already on list Z" instead of a confusing "skipped" number."""
    wk = _normalize_week_key(week_key)
    menu = get_week_menu(wk)
    seen_recipes: set[str] = set()
    total_added = 0
    total_on_hand = 0
    total_on_list = 0
    free_text_skipped = 0
    recipe_names: list[str] = []
    for slot in MENU_SLOTS:
        for entry in menu.get(slot, []):
            rid = entry.get("recipe_id")
            if not rid:
                free_text_skipped += 1
                continue
            if rid in seen_recipes:
                continue
            seen_recipes.add(rid)
            res = add_recipe_ingredients_to_grocery(rid)
            total_added += res.get("added", 0)
            total_on_hand += res.get("on_hand", 0)
            total_on_list += res.get("on_list", 0)
            if res.get("recipe_name"):
                recipe_names.append(res["recipe_name"])
    return {
        "week_key": wk,
        "added": total_added,
        "on_hand": total_on_hand,
        "on_list": total_on_list,
        "skipped": total_on_hand + total_on_list,
        "recipes": len(seen_recipes),
        "recipe_names": recipe_names,
        "free_text_skipped": free_text_skipped,
    }
