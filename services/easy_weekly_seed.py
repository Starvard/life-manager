"""Easy weekly meal plan seed — simple breakfasts/lunches/dinners + grocery.

Bump SEED_ID when regenerating a new week so the menu and grocery list refresh
once on deploy/startup without overwriting later edits every restart.
"""

from __future__ import annotations

from services import recipes_store

# Week of Aug 3, 2026 (ISO 2026-W32)
WEEK_KEY = "2026-W32"
SEED_ID = "easy-weekly-2026-w32-v6"

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
        "Eggs + turkey bacon + micro greens",
        slot="breakfast",
        servings="2",
        prep_time="5 min",
        cook_time="10 min",
        ingredients=[
            "eggs",
            "turkey bacon",
            "micro greens",
            "olive oil or butter",
            "salt",
            "black pepper",
            "hot sauce (optional)",
        ],
        instructions=[
            "Cook turkey bacon in a skillet over medium heat until crisp; set aside on a paper towel.",
            "In the same pan (or a lightly oiled nonstick), cook 2–3 eggs soft-scrambled or sunny-side up.",
            "Season eggs with salt and pepper.",
            "Plate eggs with bacon and a generous handful of micro greens on top or on the side.",
            "Optional: a few drops of hot sauce.",
        ],
        notes="High-protein, low-effort breakfast. Micro greens add crunch without a full salad.",
    ),
    _recipe(
        "Protein pancakes + peaches",
        slot="breakfast",
        servings="2",
        prep_time="8 min",
        cook_time="10 min",
        ingredients=[
            "eggs",
            "cottage cheese or Greek yogurt",
            "oat flour or rolled oats (blended)",
            "protein powder (vanilla or unflavored)",
            "baking powder",
            "peaches (fresh or frozen)",
            "cinnamon",
            "maple syrup or honey (optional)",
            "cooking spray or butter",
        ],
        instructions=[
            "Blend 2 eggs, 1/2 cup cottage cheese or Greek yogurt, 1/2 cup oats/oat flour, 1 scoop protein powder, 1/2 tsp baking powder, and a pinch of cinnamon until smooth.",
            "Heat a nonstick pan over medium-low; lightly grease.",
            "Pour small pancakes; cook until bubbles form, flip, cook 1–2 minutes more.",
            "Warm or slice peaches; serve on top of pancakes.",
            "Drizzle a little maple or honey only if you want sweetness.",
        ],
        notes="Fluffy, filling, and not dessert-level sweet. Frozen peaches work great thawed or warmed in a pan.",
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
            "Reheat gently until hot (or eat cold if it tastes better that way — salads and wraps often do).",
            "Add a handful of greens or a squeeze of lemon/hot sauce to freshen it up.",
        ],
        notes="Default lunch every day this week. Cook dinner with lunch leftovers in mind.",
    ),
    _recipe(
        "Roasted potatoes and veggies with Steak Strips",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="15 min",
        cook_time="30 min",
        ingredients=[
            ("steak (sirloin, flank, or strip)", "2–2.5", "lb"),
            ("baby potatoes or Yukon gold potatoes", "2.5", "lb"),
            ("broccoli or green beans", "1.5", "lb"),
            ("bell pepper", "2", ""),
            ("red onion", "1", ""),
            "olive oil",
            "garlic powder",
            "smoked paprika",
            "salt",
            "black pepper",
            "lemon",
        ],
        instructions=[
            "Heat oven to 425°F. Cut potatoes into 1-inch pieces; toss with olive oil, salt, pepper, garlic powder, and paprika. Roast 15 minutes.",
            "Toss broccoli, bell pepper, and onion with oil and salt; add to the pan and roast another 12–15 minutes until potatoes are crisp and veggies tender.",
            "Pat steak dry; season well with salt and pepper. Sear in a hot skillet 3–5 minutes per side (doneness to taste). Rest 5 minutes.",
            "Slice steak into strips against the grain; squeeze lemon over everything and serve.",
            "Pack lunch leftovers before plating dinner so tomorrow’s lunch is already done.",
        ],
        notes=FAMILY_DINNER_NOTE,
    ),
    _recipe(
        "Edamame with Korean turkey lettuce wraps",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="12 min",
        cook_time="15 min",
        ingredients=[
            ("ground turkey", "2", "lb"),
            ("butter lettuce or romaine leaves", "2", "heads"),
            ("frozen edamame", "1.5", "lb"),
            "garlic",
            "fresh ginger (or ginger paste)",
            "soy sauce or coconut aminos",
            "sesame oil",
            "rice vinegar or lime juice",
            "gochujang or sriracha",
            "green onions",
            "sesame seeds (optional)",
            "cucumber (optional)",
        ],
        instructions=[
            "Steam or microwave edamame; salt lightly and set aside as the side.",
            "Brown ground turkey in a skillet, breaking it up. Add minced garlic and ginger; cook 1 minute.",
            "Stir in soy sauce, a drizzle of sesame oil, rice vinegar/lime, and gochujang/sriracha to taste. Simmer 2–3 minutes until saucy.",
            "Spoon turkey into lettuce cups. Top with green onions, sesame seeds, and sliced cucumber if using.",
            "Serve with the edamame. Save leftover filling for lunch bowls or wraps.",
        ],
        notes=FAMILY_DINNER_NOTE + " Light, spicy, high-protein.",
    ),
    _recipe(
        "Grilled Halloumi Orzo Salad",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="15 min",
        cook_time="20 min",
        source="eMeals",
        ingredients=[
            ("orzo", "2", "cups"),
            ("olive oil vinaigrette", "8", "Tbsp"),
            ("halloumi cheese (8-oz blocks)", "2", "blocks"),
            ("red onion (small, cut into wedges)", "1", ""),
            ("red bell peppers (halved and seeded)", "3", ""),
            ("zucchini (cut into planks)", "4", ""),
            ("fresh basil (chopped)", "3/4", "cup"),
            ("balsamic glaze", "4", "Tbsp"),
        ],
        instructions=[
            "Preheat grill (or grill pan) to medium-high heat. Cook orzo according to package directions; drain, toss with 2–3 Tbsp vinaigrette.",
            "Brush cheese, bell peppers, and zucchini with remaining vinaigrette. Grill vegetables, covered, 8 minutes or until tender and slightly charred. Grill cheese, covered, 2 minutes per side or until grill marks appear.",
            "Cut bell pepper halves into 1-inch pieces. Divide orzo, vegetables, cheese, and basil among bowls; drizzle with balsamic glaze.",
            "Pack cold lunch portions before dinner — this salad holds well overnight.",
        ],
        notes=FAMILY_DINNER_NOTE + " Halloumi tip: cut into ¾-inch-thick slices before grilling.",
    ),
    _recipe(
        "Beef Fillet with Chanterelle Marsala Sauce",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="15 min",
        cook_time="30 min",
        source="Justin Courson",
        ingredients=[
            ("beef fillets (8-oz)", "5–6", ""),
            ("salt", "", ""),
            ("freshly ground black pepper", "", ""),
            ("neutral oil (corn or canola)", "2", "Tbsp"),
            ("unsalted butter", "6", "Tbsp"),
            ("garlic (minced)", "2", "tsp"),
            ("fresh chanterelle mushrooms", "1.5", "lb"),
            ("fresh thyme (chopped)", "2", "tsp"),
            ("dry marsala wine", "3/4", "cup"),
            ("heavy cream", "1 1/4", "cups"),
        ],
        instructions=[
            "Preheat the oven to 400°F.",
            "Season the beef fillets with salt and pepper to taste.",
            "Heat a large skillet over high heat until smoking. Add the oil and place the fillets in the skillet (work in batches if needed). Sear 2–3 minutes until browned and they release easily; flip and brown the other side a couple of minutes.",
            "Place the skillet with the meat in the oven and cook 6 minutes for medium-rare (or longer for desired doneness).",
            "Remove the skillet from the oven, add most of the butter, and baste the meat about 1½ minutes. Transfer meat to a platter and rest 10 minutes.",
            "In the same skillet, melt the remaining butter over medium heat. Add garlic and cook until it starts to sweat (1–2 minutes). Add chanterelles, salt, pepper, and thyme. Cook, stirring frequently, 6–7 minutes until mushrooms release their liquid.",
            "Add marsala and cook until reduced by half. Add heavy cream and reduce by about a quarter (~4 minutes) until the sauce takes on a lovely caramel color.",
            "Serve the fillets covered with the chanterelle marsala sauce. Slice leftover fillets for tomorrow’s lunch.",
        ],
        notes=FAMILY_DINNER_NOTE + " Cremini can stand in if chanterelles aren’t available.",
    ),
    _recipe(
        "Grilled Lemon-Herb Chicken with kale salad",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="15 min",
        cook_time="20 min",
        ingredients=[
            ("chicken thighs or breasts", "2.5–3", "lb"),
            ("kale", "2", "bunches"),
            "lemon",
            "olive oil",
            "garlic",
            "dried oregano or Italian seasoning",
            "Dijon mustard",
            "parmesan (optional)",
            "cherry tomatoes or cucumber",
            "salt",
            "black pepper",
        ],
        instructions=[
            "Marinate chicken 10+ minutes in olive oil, lemon juice/zest, garlic, oregano, salt, and pepper.",
            "Grill or pan-sear chicken until cooked through (165°F). Rest, then slice.",
            "Strip kale from stems; massage with olive oil, lemon, Dijon, salt, and pepper until softer and darker.",
            "Toss kale with tomatoes/cucumber and optional parmesan.",
            "Serve chicken over or beside the kale salad. Pack lunch containers with extra chicken + kale.",
        ],
        notes=FAMILY_DINNER_NOTE + " Massaging the kale is the secret — it turns bitter leaves tender.",
    ),
]

# Grocery rows: (name, category, qty, unit)
# Amounts sized for dinner + next-day lunch (2 adults + 1 kid) across the week.
# Seed syncs amounts onto existing rows and will not uncheck items you already have.
GROCERY = [
    # Produce
    ("micro greens", "Produce", "1", "clamshell"),
    ("peaches", "Produce", "6", ""),
    ("baby potatoes or Yukon gold potatoes", "Produce", "2.5", "lb"),
    ("broccoli or green beans", "Produce", "1.5", "lb"),
    ("bell pepper", "Produce", "2", ""),
    ("red onion", "Produce", "2", ""),
    ("red bell peppers", "Produce", "3", ""),
    ("zucchini", "Produce", "4", ""),
    ("lemon", "Produce", "4", ""),
    ("butter lettuce or romaine", "Produce", "2", "heads"),
    ("garlic", "Produce", "1", "bulb"),
    ("fresh ginger", "Produce", "1", "knob"),
    ("green onions", "Produce", "1", "bunch"),
    ("fresh basil", "Produce", "1", "bunch"),
    ("fresh chanterelle mushrooms", "Produce", "1.5", "lb"),
    ("kale", "Produce", "2", "bunches"),
    ("cherry tomatoes or cucumber", "Produce", "1", "pint / 2 cukes"),
    ("carrots", "Produce", "2", "lb"),
    ("bananas", "Produce", "1", "bunch (~8)"),
    ("apples", "Produce", "6", ""),
    ("grapes or berries", "Produce", "1", "lb"),
    ("celery", "Produce", "1", "bunch"),
    # Meat
    ("turkey bacon", "Meat & Seafood", "1", "pack"),
    ("steak (sirloin/flank)", "Meat & Seafood", "2–2.5", "lb"),
    ("beef fillets (8-oz)", "Meat & Seafood", "5–6", "fillets"),
    ("ground turkey", "Meat & Seafood", "2", "lb"),
    ("chicken thighs or breasts", "Meat & Seafood", "2.5–3", "lb"),
    # Dairy
    ("eggs", "Dairy", "18", "ct"),
    ("cottage cheese or Greek yogurt", "Dairy", "32", "oz"),
    ("halloumi cheese (8-oz blocks)", "Dairy", "2", "blocks"),
    ("unsalted butter", "Dairy", "1", "stick+"),
    ("heavy cream", "Dairy", "1.25", "cups"),
    ("parmesan (optional)", "Dairy", "1", "small"),
    ("string cheese or cheese sticks", "Dairy", "1", "pack"),
    ("milk", "Dairy", "1", "half-gal"),
    ("hummus", "Dairy", "1", "tub"),
    # Bakery / snacks
    ("bread (sandwich loaf)", "Bakery", "1", "loaf"),
    ("tortillas or wraps", "Bakery", "1", "pack"),
    ("crackers", "Snacks", "1", "box"),
    ("granola bars or granola", "Snacks", "1", "box"),
    ("peanut butter", "Pantry", "1", "jar"),
    # Frozen / Pantry
    ("frozen edamame", "Frozen", "1.5", "lb"),
    ("oat flour or rolled oats", "Pantry", "1", "bag"),
    ("protein powder", "Pantry", "", "on hand?"),
    ("orzo", "Pantry", "1", "box (16 oz)"),
    ("olive oil vinaigrette", "Pantry", "1", "bottle"),
    ("balsamic glaze", "Pantry", "1", "bottle"),
    ("olive oil", "Pantry", "", "on hand?"),
    ("neutral oil (corn or canola)", "Pantry", "", "on hand?"),
    ("dry marsala wine", "Pantry", "1", "small bottle"),
    ("soy sauce or coconut aminos", "Pantry", "", "on hand?"),
    ("sesame oil", "Pantry", "", "on hand?"),
    ("rice vinegar", "Pantry", "", "on hand?"),
    ("gochujang or sriracha", "Pantry", "", "on hand?"),
    ("Dijon mustard", "Pantry", "", "on hand?"),
    ("baking powder", "Pantry", "", "on hand?"),
    ("garlic powder", "Pantry", "", "on hand?"),
    ("smoked paprika", "Pantry", "", "on hand?"),
    ("dried oregano or Italian seasoning", "Pantry", "", "on hand?"),
    ("fresh thyme", "Produce", "1", "pack"),
    ("sesame seeds (optional)", "Pantry", "", "on hand?"),
    ("maple syrup or honey (optional)", "Pantry", "", "on hand?"),
    ("hot sauce (optional)", "Pantry", "", "on hand?"),
    ("salt", "Pantry", "", "on hand?"),
    ("black pepper", "Pantry", "", "on hand?"),
]

# Old seed names → canonical names (avoid duplicates after renames)
GROCERY_ALIASES = {
    "steak (sirloin/flank) 2–2.5 lb": "steak (sirloin/flank)",
    "beef fillets (8-oz) × 5–6": "beef fillets (8-oz)",
    "ground turkey 2 lb": "ground turkey",
    "chicken thighs or breasts 2.5–3 lb": "chicken thighs or breasts",
    "halloumi cheese (8-oz blocks) × 2": "halloumi cheese (8-oz blocks)",
}


MENU = {
    "breakfast": [
        "Eggs + turkey bacon + micro greens",
        "Protein pancakes + peaches",
    ],
    "lunch": [
        "Leftovers from dinner",
    ],
    "dinner": [
        "Roasted potatoes and veggies with Steak Strips",
        "Edamame with Korean turkey lettuce wraps",
        "Grilled Halloumi Orzo Salad",
        "Beef Fillet with Chanterelle Marsala Sauce",
        "Grilled Lemon-Herb Chicken with kale salad",
    ],
    "snack": [
        "Carrots + hummus",
        "Bananas",
        "Apples",
        "Bread / toast + peanut butter",
        "Cheese + crackers",
        "Yogurt",
        "Granola bars",
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
        # Sync amounts onto existing rows; never uncheck items already marked have.
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
