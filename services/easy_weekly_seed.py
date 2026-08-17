"""Easy weekly meal plan seed — simple breakfasts/lunches/dinners + grocery.

Bump SEED_ID when regenerating a new week so the menu and grocery list refresh
once on deploy/startup without overwriting later edits every restart.

Household meal preferences (keep this format on the Recipes tab):
- Menu slots: Breakfast / Lunch / Dinner / Snacks (a pool, not per-day boxes)
- Lunch is leftovers from dinner
- Each dinner = dinner + next-day lunch for 2 adults + 1 kid ≈ 5–6 servings
- Easy, high-protein, leftover-friendly; pack lunch containers before sitting down
- Grocery list has amounts; pantry staples already checked stay checked
"""

from __future__ import annotations

from services import recipes_store

# Week of Aug 17, 2026 (ISO 2026-W34)
WEEK_KEY = "2026-W34"
SEED_ID = "easy-weekly-2026-w34-v1"

# Each dinner should cover dinner + next-day lunch for 2 adults + 1 kid.
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
        "Cottage cheese berry bowls",
        slot="breakfast",
        servings="2",
        prep_time="5 min",
        cook_time="0 min",
        ingredients=[
            "cottage cheese",
            "blueberries or mixed berries",
            "granola",
            "honey (optional)",
            "cinnamon",
        ],
        instructions=[
            "Spoon cottage cheese into two bowls.",
            "Top with a generous handful of berries and a sprinkle of granola.",
            "Dust with cinnamon. Drizzle a little honey only if you want sweetness.",
        ],
        notes="No-cook, high-protein breakfast. Frozen berries work thawed or warmed 30 seconds.",
    ),
    _recipe(
        "Turkey sausage scramble + fruit",
        slot="breakfast",
        servings="2",
        prep_time="5 min",
        cook_time="12 min",
        ingredients=[
            "turkey sausage",
            "eggs",
            "bell pepper or spinach",
            "olive oil or butter",
            "salt",
            "black pepper",
            "fruit (banana, orange, or berries)",
            "salsa (optional)",
        ],
        instructions=[
            "Brown turkey sausage in a skillet, breaking it up; drain extra fat if needed.",
            "Add chopped pepper or a handful of spinach; cook 1–2 minutes.",
            "Pour in 4 beaten eggs. Stir over medium-low until just set.",
            "Season with salt and pepper. Optional salsa on top.",
            "Serve with a piece of fruit on the side.",
        ],
        notes="Savory, filling, and fast. Use pre-cooked turkey sausage links sliced up if that’s easier.",
    ),
    _recipe(
        "Leftovers from dinner",
        slot="lunch",
        servings="1–2",
        prep_time="2 min",
        cook_time="5 min",
        ingredients=[
            "dinner leftovers",
            "salad greens (optional)",
            "lemon or hot sauce (optional)",
        ],
        instructions=[
            "Pull last night’s dinner from the fridge.",
            "Reheat gently until hot (or eat cold if it tastes better that way — bowls and salads often do).",
            "Add a handful of greens or a squeeze of lemon/hot sauce to freshen it up.",
        ],
        notes="Default lunch every day this week. Cook dinner with lunch leftovers in mind.",
    ),
    _recipe(
        "Sheet-pan honey-mustard salmon",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="15 min",
        cook_time="25 min",
        ingredients=[
            ("salmon fillets", "2.5", "lb"),
            ("baby potatoes or Yukon gold potatoes", "2.5", "lb"),
            ("green beans", "1.5", "lb"),
            ("Dijon mustard", "3", "Tbsp"),
            ("honey", "2", "Tbsp"),
            "olive oil",
            "garlic",
            "lemon",
            "salt",
            "black pepper",
            "dried dill or parsley (optional)",
        ],
        instructions=[
            "Heat oven to 425°F. Halve potatoes; toss with olive oil, salt, pepper, and minced garlic. Roast 12 minutes.",
            "Stir Dijon, honey, a squeeze of lemon, and a pinch of salt. Pat salmon dry.",
            "Push potatoes aside. Add green beans tossed with oil and salt. Nestle salmon on the pan; brush with honey-mustard.",
            "Roast 12–15 minutes until salmon flakes and potatoes are tender.",
            "Finish with lemon. Pack lunch leftovers before plating dinner.",
        ],
        notes=FAMILY_DINNER_NOTE + " Kid-friendly sweet-tangy glaze. Leftover salmon is good cold over greens.",
    ),
    _recipe(
        "Turkey taco bowls",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="15 min",
        cook_time="25 min",
        ingredients=[
            ("ground turkey", "2", "lb"),
            ("long-grain rice", "2", "cups"),
            ("black beans (cans)", "2", "cans"),
            ("salsa", "1", "jar"),
            "taco seasoning",
            ("shredded Mexican cheese", "2", "cups"),
            ("romaine or iceberg", "1", "head"),
            ("avocado", "2", ""),
            "lime",
            "cilantro (optional)",
            "sour cream or Greek yogurt (optional)",
            "olive oil",
            "salt",
        ],
        instructions=[
            "Cook rice according to the package (about 2 cups dry).",
            "Brown turkey in a large skillet. Stir in taco seasoning and a splash of water; simmer 2 minutes.",
            "Rinse and warm the black beans. Chop lettuce; slice avocado; warm salsa.",
            "Build bowls: rice, turkey, beans, salsa, cheese, lettuce, avocado. Lime + cilantro on top.",
            "Pack leftover bowls (keep lettuce separate if you want it crisp tomorrow).",
        ],
        notes=FAMILY_DINNER_NOTE + " Everyone builds their own bowl — easy for a kid plate.",
    ),
    _recipe(
        "Honey-garlic chicken thighs with carrots and rice",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="15 min",
        cook_time="35 min",
        ingredients=[
            ("chicken thighs", "3", "lb"),
            ("carrots", "2", "lb"),
            ("long-grain rice", "2", "cups"),
            ("honey", "3", "Tbsp"),
            ("soy sauce or coconut aminos", "1/4", "cup"),
            "garlic",
            "olive oil",
            "garlic powder",
            "salt",
            "black pepper",
            "green onions (optional)",
        ],
        instructions=[
            "Heat oven to 425°F. Cut carrots into sticks; toss with oil, salt, and pepper. Spread on a sheet pan.",
            "Pat chicken dry. Season with salt, pepper, and garlic powder. Nestle on the pan.",
            "Stir honey, soy sauce, and minced garlic. Spoon over the chicken.",
            "Roast 30–35 minutes until chicken is 165°F and carrots are tender. Start the rice when the chicken goes in.",
            "Spoon pan juices over everything. Pack lunch portions of chicken, carrots, and rice.",
        ],
        notes=FAMILY_DINNER_NOTE + " Sticky-savory and reheats well.",
    ),
    _recipe(
        "Pork tenderloin with apples and Brussels sprouts",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="15 min",
        cook_time="30 min",
        ingredients=[
            ("pork tenderloin", "2–2.5", "lb"),
            ("Brussels sprouts", "1.5", "lb"),
            ("apples", "3", ""),
            "olive oil",
            "Dijon mustard",
            "garlic powder",
            "dried thyme or Italian seasoning",
            "salt",
            "black pepper",
            "apple cider vinegar or lemon",
        ],
        instructions=[
            "Heat oven to 425°F. Trim and halve Brussels sprouts; core and wedge the apples.",
            "Toss sprouts and apples with olive oil, salt, pepper, and thyme. Spread on a sheet pan.",
            "Pat pork dry. Rub with Dijon, garlic powder, salt, and pepper. Set in the center of the pan.",
            "Roast 22–28 minutes until pork is 145°F. Rest 5 minutes, then slice.",
            "Splash vinegar or lemon over the sprouts. Pack sliced pork + sides for lunch.",
        ],
        notes=FAMILY_DINNER_NOTE + " Sweet apples make the sprouts easier for a kid plate.",
    ),
    _recipe(
        "Sausage, white bean, and kale skillet",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="12 min",
        cook_time="25 min",
        ingredients=[
            ("Italian sausage", "2", "lb"),
            ("cannellini or white beans (cans)", "2", "cans"),
            ("kale", "2", "bunches"),
            ("yellow onion", "1", ""),
            "garlic",
            ("chicken broth", "1", "cup"),
            "olive oil",
            "Italian seasoning",
            "crushed red pepper (optional)",
            "parmesan (optional)",
            ("baguette or garlic bread", "1", "loaf"),
            "salt",
            "black pepper",
        ],
        instructions=[
            "Brown sausage in a large skillet, breaking it up; scoop out extra fat if the pan is greasy.",
            "Add chopped onion; cook 3 minutes. Add minced garlic and Italian seasoning; cook 30 seconds.",
            "Stir in rinsed beans and broth. Simmer 5 minutes.",
            "Strip kale from stems, chop, and wilt it into the skillet 3–5 minutes. Season with salt, pepper, and chili flake.",
            "Warm the bread. Serve bowls with optional parmesan. Pack leftover skillet for lunch.",
        ],
        notes=FAMILY_DINNER_NOTE + " One-pan, hearty, and even better the next day.",
    ),
]

# Grocery rows: (name, category, qty, unit)
# Amounts sized for dinner + next-day lunch (2 adults + 1 kid) across the week.
# A new seed replaces last week’s list; checked pantry staples that still appear stay checked.
GROCERY = [
    # Produce
    ("blueberries or mixed berries", "Produce", "2", "pints"),
    ("bananas", "Produce", "1", "bunch (~8)"),
    ("apples", "Produce", "8", ""),
    ("oranges", "Produce", "6", ""),
    ("baby potatoes or Yukon gold potatoes", "Produce", "2.5", "lb"),
    ("green beans", "Produce", "1.5", "lb"),
    ("carrots", "Produce", "2", "lb"),
    ("Brussels sprouts", "Produce", "1.5", "lb"),
    ("kale", "Produce", "2", "bunches"),
    ("bell peppers", "Produce", "4", ""),
    ("yellow onion", "Produce", "1", ""),
    ("romaine or iceberg", "Produce", "1", "head"),
    ("avocado", "Produce", "3", ""),
    ("cucumber", "Produce", "2", ""),
    ("lemon", "Produce", "3", ""),
    ("lime", "Produce", "3", ""),
    ("garlic", "Produce", "1", "bulb"),
    ("cilantro", "Produce", "1", "bunch"),
    ("green onions (optional)", "Produce", "1", "bunch"),
    # Meat
    ("salmon fillets", "Meat & Seafood", "2.5", "lb"),
    ("ground turkey", "Meat & Seafood", "2", "lb"),
    ("chicken thighs", "Meat & Seafood", "3", "lb"),
    ("pork tenderloin", "Meat & Seafood", "2–2.5", "lb"),
    ("Italian sausage", "Meat & Seafood", "2", "lb"),
    ("turkey sausage", "Meat & Seafood", "1", "pack"),
    # Dairy
    ("eggs", "Dairy", "18", "ct"),
    ("cottage cheese", "Dairy", "32", "oz"),
    ("shredded Mexican cheese", "Dairy", "16", "oz"),
    ("sour cream or Greek yogurt", "Dairy", "16", "oz"),
    ("parmesan (optional)", "Dairy", "1", "small"),
    ("string cheese or cheese sticks", "Dairy", "1", "pack"),
    ("milk", "Dairy", "1", "half-gal"),
    ("hummus", "Dairy", "1", "tub"),
    ("ranch or yogurt dip", "Dairy", "1", "bottle"),
    ("unsalted butter", "Dairy", "1", "stick"),
    # Bakery / snacks
    ("baguette or garlic bread", "Bakery", "1", "loaf"),
    ("bread (sandwich loaf)", "Bakery", "1", "loaf"),
    ("tortillas or wraps", "Bakery", "1", "pack"),
    ("granola", "Snacks", "1", "bag"),
    ("trail mix", "Snacks", "1", "bag"),
    ("popcorn (kernels or microwave)", "Snacks", "1", "box"),
    ("peanut butter", "Pantry", "1", "jar"),
    # Pantry
    ("long-grain rice", "Pantry", "1", "bag"),
    ("black beans (cans)", "Pantry", "2", "cans"),
    ("cannellini or white beans (cans)", "Pantry", "2", "cans"),
    ("salsa", "Pantry", "1", "jar"),
    ("taco seasoning", "Pantry", "1", "packet"),
    ("chicken broth", "Pantry", "1", "carton"),
    ("honey", "Pantry", "", "on hand?"),
    ("Dijon mustard", "Pantry", "", "on hand?"),
    ("soy sauce or coconut aminos", "Pantry", "", "on hand?"),
    ("olive oil", "Pantry", "", "on hand?"),
    ("garlic powder", "Pantry", "", "on hand?"),
    ("dried thyme or Italian seasoning", "Pantry", "", "on hand?"),
    ("Italian seasoning", "Pantry", "", "on hand?"),
    ("cinnamon", "Pantry", "", "on hand?"),
    ("crushed red pepper (optional)", "Pantry", "", "on hand?"),
    ("dried dill or parsley (optional)", "Pantry", "", "on hand?"),
    ("apple cider vinegar or lemon", "Pantry", "", "on hand?"),
    ("hot sauce (optional)", "Pantry", "", "on hand?"),
    ("salt", "Pantry", "", "on hand?"),
    ("black pepper", "Pantry", "", "on hand?"),
]

# Old seed names → canonical names (avoid duplicates after renames)
GROCERY_ALIASES = {
    "cottage cheese or Greek yogurt": "cottage cheese",
    "bell pepper": "bell peppers",
    "chicken thighs or breasts": "chicken thighs",
}


MENU = {
    "breakfast": [
        "Cottage cheese berry bowls",
        "Turkey sausage scramble + fruit",
    ],
    "lunch": [
        "Leftovers from dinner",
    ],
    "dinner": [
        "Sheet-pan honey-mustard salmon",
        "Turkey taco bowls",
        "Honey-garlic chicken thighs with carrots and rice",
        "Pork tenderloin with apples and Brussels sprouts",
        "Sausage, white bean, and kale skillet",
    ],
    "snack": [
        "Bell peppers + hummus",
        "Oranges",
        "Cottage cheese cups",
        "Popcorn",
        "Cheese + apple slices",
        "Trail mix",
        "Cucumber + ranch",
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
        # Replace last week’s list; never uncheck pantry staples that still appear.
        grocery_result = recipes_store.merge_grocery_items(
            [
                {
                    "name": name,
                    "category": cat,
                    "qty": qty,
                    "unit": unit,
                    "checked": False,
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
            f"removed dupes {grocery_result.get('removed', 0)}, "
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
