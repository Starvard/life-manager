"""
Online recipe search powered by TheMealDB free public API
(https://www.themealdb.com/api.php). No key required for the test endpoint.

Used by `/api/recipes/search-online` so users can search & import recipes
straight into Home Recipes. Falls back to an empty list if the network is
unavailable.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from urllib.error import URLError

_BASE = "https://www.themealdb.com/api/json/v1/1"
_TIMEOUT = 8


def _http_json(url: str) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LifeManager-Recipes/1.0"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
    except (URLError, TimeoutError, ValueError, OSError):
        return None


def _meal_to_recipe(meal: dict) -> dict:
    """Convert TheMealDB meal payload to our internal recipe shape."""
    ingredients = []
    for i in range(1, 21):
        name = (meal.get(f"strIngredient{i}") or "").strip()
        if not name:
            continue
        measure = (meal.get(f"strMeasure{i}") or "").strip()
        ingredients.append({
            "name": name,
            "qty": measure,
            "unit": "",
        })

    instructions_text = (meal.get("strInstructions") or "").strip()
    raw_steps = [s.strip() for s in instructions_text.replace("\r\n", "\n").split("\n") if s.strip()]
    if len(raw_steps) <= 1 and instructions_text:
        raw_steps = [s.strip() for s in instructions_text.split(". ") if s.strip()]
    instructions = []
    for step in raw_steps:
        clean = step.lstrip("0123456789.) -").strip()
        if clean:
            instructions.append(clean)

    tags_str = (meal.get("strTags") or "").strip()
    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
    category = (meal.get("strCategory") or "").strip()
    area = (meal.get("strArea") or "").strip()
    if category and category not in tags:
        tags.append(category)
    if area and area not in tags:
        tags.append(area)

    return {
        "external_id": meal.get("idMeal"),
        "name": (meal.get("strMeal") or "Untitled").strip(),
        "image_url": (meal.get("strMealThumb") or "").strip(),
        "source": "TheMealDB",
        "source_url": (meal.get("strSource") or meal.get("strYoutube") or "").strip(),
        "ingredients": ingredients,
        "instructions": instructions,
        "tags": tags,
        "servings": "",
        "prep_time": "",
        "cook_time": "",
        "notes": "",
    }


def search_online(query: str, limit: int = 12) -> dict:
    q = (query or "").strip()
    if not q:
        return {"ok": True, "results": [], "query": q, "source": "TheMealDB"}
    url = f"{_BASE}/search.php?s={urllib.parse.quote(q)}"
    data = _http_json(url)
    if data is None:
        return {
            "ok": False,
            "error": "Could not reach TheMealDB. Check your connection or add the recipe manually.",
            "results": [],
            "query": q,
        }
    meals = data.get("meals") or []
    results = [_meal_to_recipe(m) for m in meals[:limit]]
    return {
        "ok": True,
        "results": results,
        "count": len(results),
        "query": q,
        "source": "TheMealDB",
        "source_url": "https://www.themealdb.com",
    }


def lookup_online(external_id: str) -> dict | None:
    eid = (external_id or "").strip()
    if not eid:
        return None
    url = f"{_BASE}/lookup.php?i={urllib.parse.quote(eid)}"
    data = _http_json(url)
    if not data:
        return None
    meals = data.get("meals") or []
    if not meals:
        return None
    return _meal_to_recipe(meals[0])
