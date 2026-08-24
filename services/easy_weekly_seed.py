"""Easy weekly meal plan seed — simple breakfasts/lunches/dinners + grocery.

Bump SEED_ID when regenerating a new week so the menu and grocery list refresh
once on deploy/startup without overwriting later edits every restart.

Household meal preferences (keep this format on the Recipes tab):
- Menu slots: Breakfast / Lunch / Dinner / Snacks (a pool, not per-day boxes)
- Lunch is leftovers from dinner, plus a kid plate
- Each dinner = dinner + next-day lunch for 2 adults + 1 kid ≈ 5–6 servings
- Easy, leftover-friendly; pack lunch containers before sitting down
- No cottage cheese; extra vegetables; prefer sheet-pan / pasta-pot over skillet
- Snacks: lots, specific, mixed (healthy / filling / sweet / savory / treats)
- Grocery list has amounts; pantry staples already checked stay checked
"""

from __future__ import annotations

from services import recipes_store

# Week of Aug 24, 2026 (ISO 2026-W35)
WEEK_KEY = "2026-W35"
SEED_ID = "easy-weekly-2026-w35-v1"

FAMILY_DINNER_SERVINGS = "5–6"
FAMILY_DINNER_NOTE = (
    "Cook enough for dinner + tomorrow’s lunch: 2 adults + 1 kid ≈ 5–6 servings. "
    "Portion leftovers into lunch containers before sitting down."
)


def _ing(*items) -> list[dict]:
    """Accept plain names or (name, qty, unit) tuples."""
    out = []
    for item in items:
        if isinstance(item, (list, tuple)):
            name = str(item[0]).strip()
            qty = str(item[1]).strip() if len(item) > 1 else ""
            unit = str(item[2]).strip() if len(item) > 2 else ""
        else:
            name = str(item).strip()
            qty, unit = "", ""
        if name:
            out.append({"name": name, "qty": qty, "unit": unit})
    return out


def _recipe(
    name: str,
    *,
    slot: str,
    ingredients: list,
    instructions: list[str],
    notes: str = "",
    servings: str = "2–3",
    prep_time: str = "10 min",
    cook_time: str = "15 min",
    source: str = "Life Manager",
) -> dict:
    return {
        "name": name,
        "source": source,
        "servings": servings,
        "prep_time": prep_time,
        "cook_time": cook_time,
        "tags": ["easy weekly", slot, "healthy"],
        "ingredients": _ing(*ingredients),
        "instructions": instructions,
        "notes": notes,
    }


RECIPES = [
    _recipe(
        "Protein pancakes + berries",
        slot="breakfast",
        servings="2–3",
        prep_time="8 min",
        cook_time="10 min",
        ingredients=[
            "eggs",
            "Greek yogurt",
            "oat flour or rolled oats (blended)",
            "protein powder (vanilla or unflavored)",
            "baking powder",
            "blueberries or mixed berries",
            "cinnamon",
            "maple syrup or honey (optional)",
            "cooking spray or butter",
        ],
        instructions=[
            "Blend 2 eggs, 1/2 cup Greek yogurt, 1/2 cup oats/oat flour, 1 scoop protein powder, 1/2 tsp baking powder, and a pinch of cinnamon until smooth.",
            "Heat a nonstick pan over medium-low; lightly grease.",
            "Pour small pancakes; cook until bubbles form, flip, cook 1–2 minutes more.",
            "Warm or scatter berries on top. Kid plate: extra berries + a little maple.",
            "Drizzle maple or honey only if you want sweetness.",
        ],
        notes="High-protein pancakes, no cottage cheese. Make a couple extra for the 5-year-old’s second breakfast / snack.",
    ),
    _recipe(
        "Turkey sausage scramble with veggies + micro greens",
        slot="breakfast",
        servings="2–3",
        prep_time="8 min",
        cook_time="12 min",
        ingredients=[
            "turkey sausage",
            "eggs",
            "bell pepper",
            "baby spinach",
            "zucchini or onion",
            "micro greens",
            "olive oil or butter",
            "salt",
            "black pepper",
            "hot sauce (optional)",
        ],
        instructions=[
            "Brown turkey sausage, breaking it up; drain extra fat if needed.",
            "Add chopped bell pepper and zucchini/onion; cook 3–4 minutes until softened.",
            "Stir in a big handful of spinach until just wilted.",
            "Pour in 5 beaten eggs (extra egg for the kid). Stir over medium-low until just set.",
            "Season with salt and pepper. Pile micro greens on top.",
        ],
        notes="Veggie-heavy scramble. Micro greens go on at the end.",
    ),
    _recipe(
        "Leftovers from dinner",
        slot="lunch",
        servings="1–2",
        prep_time="2 min",
        cook_time="5 min",
        ingredients=[
            "dinner leftovers",
            "salad greens or micro greens (optional)",
            "lemon or hot sauce (optional)",
        ],
        instructions=[
            "Pull last night’s dinner from the fridge.",
            "Reheat gently until hot (pasta and roasted veg are also fine cold).",
            "Add greens or a squeeze of lemon to freshen it up.",
        ],
        notes="Default adult lunch. Cook dinner with leftovers in mind.",
    ),
    _recipe(
        "Kid plate: leftover pasta or PB&J",
        slot="lunch",
        servings="1",
        prep_time="5 min",
        cook_time="2 min",
        ingredients=[
            "leftover pasta or sandwich bread",
            "peanut butter",
            "jelly",
            "fruit (apple, banana, or grapes)",
            "string cheese or cheddar",
        ],
        instructions=[
            "If there is leftover pasta, warm a kid portion with a little butter.",
            "Otherwise: peanut butter + jelly on bread.",
            "Add fruit and a cheese stick on the side.",
        ],
        notes="5-year-old backup so lunch is not only leftover salmon or salad.",
    ),
    _recipe(
        "Roasted veggie pasta with chicken",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="20 min",
        cook_time="35 min",
        ingredients=[
            ("chicken breasts or tenders", "2", "lb"),
            ("regular pasta (penne or rotini)", "2", "lb"),
            ("mushrooms (2 containers you have)", "2", "containers"),
            "roasted veg you already have (zucchini, broccoli, peppers, tomatoes)",
            "olive oil",
            "butter",
            "garlic",
            "Italian seasoning",
            "lemon",
            "parmesan (optional)",
            "salt",
            "black pepper",
        ],
        instructions=[
            "Heat oven to 425°F. Toss chicken with oil, salt, pepper, and Italian seasoning. On a second pan, toss whatever veg you have (zucchini, broccoli, peppers, tomatoes) with oil and salt. Roast both 18–22 minutes until chicken is 165°F.",
            "Dice both mushroom containers very small (almost a mince). Put them in a wide pot with a knob of butter and a little oil over medium. Cook 18–25 minutes, stirring now and then, until all the water cooks off and they shrink, brown, and taste savory — not spongy. Add minced garlic for the last minute.",
            "Boil the full 2 lb pasta. Scoop out a cup of pasta water; drain. Hold back a kid portion of plain noodles + butter.",
            "Toss the rest of the pasta in the mushroom pot with the roasted veg, a splash of pasta water, lemon, and optional parmesan. Slice the chicken over the top.",
            "Pack lunch leftovers before plating.",
        ],
        notes=FAMILY_DINNER_NOTE + " The two mushroom containers get diced small and cooked long so they melt into the pasta. Use veg already in the fridge.",
    ),
    _recipe(
        "Turkey burgers with sweet potatoes and salad",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="15 min",
        cook_time="30 min",
        ingredients=[
            ("ground turkey", "2", "lb"),
            ("burger buns", "8", ""),
            ("sweet potatoes", "3", "lb"),
            ("salad greens", "1", "big box"),
            ("cucumber", "1", ""),
            ("cherry tomatoes", "1", "pint"),
            "olive oil",
            "garlic powder",
            "smoked paprika",
            "salt",
            "black pepper",
            "ketchup or mustard (optional)",
        ],
        instructions=[
            "Heat oven to 425°F. Cut sweet potatoes into wedges; toss with oil, salt, paprika, and garlic powder. Roast 15 minutes.",
            "Mix turkey with salt, pepper, and garlic powder. Shape 6–7 burgers (make one smaller for the kid).",
            "Set burgers on the other side of the sheet pan (or a second pan). Roast 12–15 minutes more, until burgers are 165°F and potatoes are tender.",
            "Toss greens, cucumber, and tomatoes with oil, lemon or vinegar, salt, and pepper.",
            "Serve burgers on buns with salad and wedges. Pack extra burgers + potatoes for lunch.",
        ],
        notes=FAMILY_DINNER_NOTE + " Oven burgers — no skillet. Kid usually wants ketchup and a bun.",
    ),
    _recipe(
        "BBQ chicken thighs with corn and broccoli",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="10 min",
        cook_time="35 min",
        ingredients=[
            ("chicken thighs", "3", "lb"),
            ("corn on the cob (or frozen ears)", "8", ""),
            ("broccoli", "2", "lb"),
            ("BBQ sauce", "1", "bottle"),
            "olive oil",
            "garlic powder",
            "salt",
            "black pepper",
        ],
        instructions=[
            "Heat oven to 425°F. Pat chicken dry; season with salt, pepper, and garlic powder. Brush with BBQ sauce. Roast 20 minutes.",
            "Toss broccoli with oil and salt. Add broccoli and corn to the pan (or a second pan). Brush chicken with more sauce.",
            "Roast 12–15 minutes more until chicken is 165°F, broccoli is browned, and corn is tender.",
            "Brush with a last swipe of sauce. Pack lunch portions of chicken + veg.",
        ],
        notes=FAMILY_DINNER_NOTE + " Kid-friendly sauce, lots of corn.",
    ),
    _recipe(
        "Sheet-pan sausage and peppers",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="12 min",
        cook_time="30 min",
        ingredients=[
            ("Italian sausage (links)", "2", "lb"),
            ("bell peppers", "5", ""),
            ("red onion", "2", ""),
            ("zucchini", "2", ""),
            ("sandwich rolls or baguette", "1", "pack / loaf"),
            "olive oil",
            "garlic",
            "Italian seasoning",
            "salt",
            "black pepper",
            "lemon",
        ],
        instructions=[
            "Heat oven to 425°F. Slice peppers and onion into strips; chunk the zucchini.",
            "Toss vegetables with oil, minced garlic, Italian seasoning, salt, and pepper. Spread on a sheet pan.",
            "Nestle sausage links on top. Roast 25–30 minutes, turning sausages once, until browned and the veg is soft and sweet.",
            "Slice sausages. Pile into rolls or serve with bread. Lemon over the peppers.",
            "Pack leftover sausage + peppers for lunch (or a kid roll).",
        ],
        notes=FAMILY_DINNER_NOTE + " Sheet-pan, not a skillet.",
    ),
    _recipe(
        "Sheet-pan lemon salmon with green beans and rice",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="12 min",
        cook_time="25 min",
        ingredients=[
            ("salmon fillets", "2.5", "lb"),
            ("green beans", "1.5", "lb"),
            ("long-grain rice", "2", "cups"),
            "lemon",
            "olive oil",
            "garlic",
            "salt",
            "black pepper",
            "dried dill or parsley (optional)",
        ],
        instructions=[
            "Start the rice (about 2 cups dry).",
            "Heat oven to 425°F. Toss green beans with oil, salt, and minced garlic. Spread on a sheet pan; roast 8 minutes.",
            "Pat salmon dry. Season with salt, pepper, lemon zest, and dill. Nestle on the pan; drizzle oil and lemon juice.",
            "Roast 10–14 minutes until salmon flakes.",
            "Serve with rice and extra lemon. Pack lunch leftovers (salmon is good cold over the leftover beans + rice).",
        ],
        notes=FAMILY_DINNER_NOTE + " Simple lemon salmon — lighter night.",
    ),
]

# Grocery rows: (name, category, qty, unit)
GROCERY = [
    # Produce — dinners + snacks
    ("micro greens", "Produce", "1", "clamshell"),
    ("blueberries or mixed berries", "Produce", "2", "pints"),
    ("baby spinach", "Produce", "5", "oz"),
    ("salad greens", "Produce", "1", "big box"),
    ("broccoli", "Produce", "2", "lb"),
    ("green beans", "Produce", "1.5", "lb"),
    ("sweet potatoes", "Produce", "3", "lb"),
    ("zucchini", "Produce", "2", ""),
    ("bell peppers", "Produce", "7", ""),
    ("red onion", "Produce", "2", ""),
    ("cherry tomatoes", "Produce", "1", "pint"),
    ("corn on the cob", "Produce", "8", "ears"),
    ("mushrooms (2 containers — already have)", "Produce", "2", "containers"),
    ("apples", "Produce", "10", ""),
    ("bananas", "Produce", "1", "bunch (~8)"),
    ("grapes", "Produce", "2", "lb"),
    ("oranges", "Produce", "8", ""),
    ("watermelon (small)", "Produce", "1", ""),
    ("baby carrots", "Produce", "2", "lb"),
    ("cucumber", "Produce", "4", ""),
    ("celery", "Produce", "1", "bunch"),
    ("lemon", "Produce", "5", ""),
    ("garlic", "Produce", "2", "bulbs"),
    # Meat
    ("turkey sausage", "Meat & Seafood", "1", "pack"),
    ("ground turkey", "Meat & Seafood", "2", "lb"),
    ("chicken breasts or tenders", "Meat & Seafood", "2", "lb"),
    ("chicken thighs", "Meat & Seafood", "3", "lb"),
    ("Italian sausage (links)", "Meat & Seafood", "2", "lb"),
    ("salmon fillets", "Meat & Seafood", "2.5", "lb"),
    ("turkey sticks or meat sticks", "Meat & Seafood", "1", "pack"),
    # Dairy
    ("eggs", "Dairy", "24", "ct"),
    ("Greek yogurt", "Dairy", "32", "oz"),
    ("yogurt tubes", "Dairy", "1", "box (8–16)"),
    ("string cheese or cheese sticks", "Dairy", "2", "packs"),
    ("cheddar block", "Dairy", "1", "8 oz"),
    ("parmesan (optional)", "Dairy", "1", "small"),
    ("milk", "Dairy", "1", "gallon"),
    ("hummus", "Dairy", "2", "tubs"),
    ("ranch or yogurt dip", "Dairy", "1", "bottle"),
    ("unsalted butter", "Dairy", "1", "stick"),
    ("pudding cups", "Dairy", "1", "pack (6–8)"),
    ("ice cream cups", "Frozen", "1", "box (6–8)"),
    # Bakery
    ("sandwich bread", "Bakery", "2", "loaves"),
    ("burger buns", "Bakery", "1", "pack (8)"),
    ("sandwich rolls or baguette", "Bakery", "1", "pack / loaf"),
    ("graham crackers", "Bakery", "1", "box"),
    ("mini muffins", "Bakery", "1", "pack"),
    # Snacks
    ("goldfish crackers", "Snacks", "1", "big box"),
    ("pretzel sticks", "Snacks", "1", "bag"),
    ("popcorn (kernels or microwave)", "Snacks", "1", "box"),
    ("wheat crackers", "Snacks", "1", "box"),
    ("peanut butter sandwich crackers", "Snacks", "1", "box"),
    ("animal crackers", "Snacks", "1", "box"),
    ("granola bars", "Snacks", "1", "box"),
    ("applesauce pouches", "Snacks", "1", "box (12)"),
    ("fruit snacks", "Snacks", "1", "box"),
    ("chocolate chip cookies", "Snacks", "1", "pack"),
    ("chips", "Snacks", "1", "bag"),
    ("veggie straws or cheese puffs", "Snacks", "1", "bag"),
    ("rice krispie treats", "Snacks", "1", "box"),
    ("peanut butter", "Pantry", "1", "jar"),
    ("jelly", "Pantry", "1", "jar"),
    # Pantry
    ("regular pasta (penne or rotini)", "Pantry", "2", "lb"),
    ("long-grain rice", "Pantry", "1", "bag"),
    ("oat flour or rolled oats", "Pantry", "1", "bag"),
    ("protein powder", "Pantry", "", "on hand?"),
    ("BBQ sauce", "Pantry", "1", "bottle"),
    ("olive oil", "Pantry", "", "on hand?"),
    ("garlic powder", "Pantry", "", "on hand?"),
    ("smoked paprika", "Pantry", "", "on hand?"),
    ("Italian seasoning", "Pantry", "", "on hand?"),
    ("baking powder", "Pantry", "", "on hand?"),
    ("cinnamon", "Pantry", "", "on hand?"),
    ("maple syrup or honey (optional)", "Pantry", "", "on hand?"),
    ("dried dill or parsley (optional)", "Pantry", "", "on hand?"),
    ("ketchup or mustard (optional)", "Pantry", "", "on hand?"),
    ("hot sauce (optional)", "Pantry", "", "on hand?"),
    ("salt", "Pantry", "", "on hand?"),
    ("black pepper", "Pantry", "", "on hand?"),
]

GROCERY_ALIASES = {
    "cottage cheese": "Greek yogurt",
    "bell peppers": "bell peppers",
    "Italian sausage": "Italian sausage (links)",
    "bread (sandwich loaf)": "sandwich bread",
    "mushrooms": "mushrooms (2 containers — already have)",
}


MENU = {
    "breakfast": [
        "Protein pancakes + berries",
        "Turkey sausage scramble with veggies + micro greens",
    ],
    "lunch": [
        "Leftovers from dinner",
        "Kid plate: leftover pasta or PB&J",
    ],
    "dinner": [
        "Roasted veggie pasta with chicken",
        "Turkey burgers with sweet potatoes and salad",
        "BBQ chicken thighs with corn and broccoli",
        "Sheet-pan sausage and peppers",
        "Sheet-pan lemon salmon with green beans and rice",
    ],
    "snack": [
        "Apples (10)",
        "Bananas",
        "Grapes (2 lb)",
        "Oranges (8)",
        "Watermelon",
        "Baby carrots + hummus",
        "Cucumber + ranch",
        "Celery + peanut butter",
        "Bell peppers + hummus",
        "Yogurt tubes",
        "Greek yogurt + berries",
        "String cheese (2 packs)",
        "Cheddar + wheat crackers",
        "Hard-boiled eggs",
        "Peanut butter toast",
        "PB&J halves",
        "Granola bars",
        "Graham crackers",
        "Applesauce pouches (12)",
        "Apple slices + peanut butter",
        "Frozen grapes",
        "Mini muffins",
        "Goldfish (big box)",
        "Pretzel sticks",
        "Popcorn",
        "Peanut butter sandwich crackers",
        "Animal crackers",
        "Turkey stick + cheese",
        "Chips",
        "Veggie straws or cheese puffs",
        "Pudding cups",
        "Fruit snacks",
        "Chocolate chip cookies",
        "Rice krispie treats",
        "Ice cream cups",
    ],
}


def seed_easy_weekly_menu() -> dict:
    """Ensure recipes exist; if SEED_ID is new, set this week's menu + grocery."""
    existing = {
        (r.get("name") or "").strip().lower(): r
        for r in recipes_store.list_recipes()
    }
    created = 0
    updated = 0
    by_name: dict[str, dict] = {}
    apply_seed = recipes_store.get_active_seed() != SEED_ID
    for recipe in RECIPES:
        key = recipe["name"].strip().lower()
        if key in existing:
            if apply_seed:
                saved = recipes_store.update_recipe(existing[key]["id"], recipe)
                if saved:
                    by_name[recipe["name"]] = saved
                    existing[key] = saved
                    updated += 1
                    continue
            by_name[recipe["name"]] = existing[key]
            continue
        saved = recipes_store.create_recipe(recipe)
        by_name[recipe["name"]] = saved
        existing[key] = saved
        created += 1

    applied = False
    if apply_seed:
        slots = {}
        for slot, names in MENU.items():
            entries = []
            for name in names:
                rec = by_name.get(name) or existing.get(name.strip().lower())
                entries.append({
                    "name": name,
                    "recipe_id": (rec or {}).get("id"),
                })
            slots[slot] = entries

        recipes_store.set_week_menu(WEEK_KEY, slots)
        grocery_result = recipes_store.merge_grocery_items(
            [
                {
                    "name": name,
                    "category": cat,
                    "qty": qty,
                    "unit": unit,
                    "checked": "already have" in name.lower(),
                }
                for name, cat, qty, unit in GROCERY
            ],
            aliases=GROCERY_ALIASES,
            drop_missing=True,
        )
        recipes_store.set_active_seed(SEED_ID)
        applied = True
        print(
            f"[recipes] Applied easy weekly menu seed {SEED_ID} for {WEEK_KEY} "
            f"(grocery +{grocery_result.get('added', 0)}, "
            f"updated {grocery_result.get('updated', 0)}, "
            f"removed {grocery_result.get('removed', 0)}, "
            f"unchanged {grocery_result.get('skipped', 0)})."
        )
    else:
        print(f"[recipes] Easy weekly seed {SEED_ID} already active.")

    if created:
        print(f"[recipes] Created {created} easy weekly recipe(s).")
    if updated:
        print(f"[recipes] Updated {updated} easy weekly recipe(s).")
    return {
        "created_recipes": created,
        "updated_recipes": updated,
        "applied_menu": applied,
        "seed_id": SEED_ID,
        "week_key": WEEK_KEY,
    }
