"""Easy weekly meal plan seed — simple breakfasts/lunches/dinners + grocery.

Bump SEED_ID when regenerating a new week so the menu and grocery list refresh
once on deploy/startup without overwriting later edits every restart.
"""

from __future__ import annotations

from services import recipes_store

# Week of Aug 3, 2026 (ISO 2026-W32)
WEEK_KEY = "2026-W32"
SEED_ID = "easy-weekly-2026-w32-v1"


def _ing(*names: str) -> list[dict]:
    return [{"name": n, "qty": "", "unit": ""} for n in names]


def _recipe(
    name: str,
    *,
    slot: str,
    ingredients: list[str],
    instructions: list[str],
    notes: str = "",
    servings: str = "2–3",
    prep_time: str = "10 min",
    cook_time: str = "15 min",
) -> dict:
    return {
        "name": name,
        "source": "Life Manager",
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
        servings="3+",
        prep_time="15 min",
        cook_time="30 min",
        ingredients=[
            "steak (sirloin, flank, or strip)",
            "baby potatoes or Yukon gold potatoes",
            "broccoli or green beans",
            "bell pepper",
            "red onion",
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
        ],
        notes="Sheet-pan heavy lifting + a quick steak sear. Slice extra steak for lunch leftovers.",
    ),
    _recipe(
        "Edamame with Korean turkey lettuce wraps",
        slot="dinner",
        servings="3+",
        prep_time="12 min",
        cook_time="15 min",
        ingredients=[
            "ground turkey",
            "butter lettuce or romaine leaves",
            "frozen edamame",
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
            "Serve with the edamame.",
        ],
        notes="Light, spicy, high-protein. Leftover filling is excellent over greens for lunch.",
    ),
    _recipe(
        "Couscous halloumi and chicken salad",
        slot="dinner",
        servings="3+",
        prep_time="15 min",
        cook_time="20 min",
        ingredients=[
            "couscous",
            "cooked chicken or chicken breast",
            "halloumi cheese",
            "cucumber",
            "cherry tomatoes",
            "red onion",
            "fresh parsley or mint",
            "lemon",
            "olive oil",
            "salt",
            "black pepper",
            "garlic",
        ],
        instructions=[
            "Cook couscous per package (usually pour boiling water, cover 5 minutes, fluff).",
            "Season chicken with salt, pepper, garlic, and olive oil; grill or pan-sear until cooked. Slice.",
            "Pan-sear halloumi slices 1–2 minutes per side until golden.",
            "Chop cucumber, tomatoes, onion, and herbs. Toss with couscous, lemon juice, olive oil, salt, and pepper.",
            "Top with chicken and halloumi. Serve warm or room temp.",
        ],
        notes="Bright Mediterranean plate. Holds well for leftovers — pack the halloumi separate if reheating.",
    ),
    _recipe(
        "Mushroom gravy, steak and shishito peppers",
        slot="dinner",
        servings="3+",
        prep_time="15 min",
        cook_time="25 min",
        ingredients=[
            "steak (sirloin or ribeye)",
            "shishito peppers",
            "mushrooms (cremini or baby bella)",
            "beef broth or bone broth",
            "onion",
            "garlic",
            "butter or olive oil",
            "flour or cornstarch (optional thickener)",
            "thyme (fresh or dried)",
            "salt",
            "black pepper",
            "lemon",
        ],
        instructions=[
            "Pat steak dry; season with salt and pepper. Sear in a hot skillet with a little oil/butter to preferred doneness. Rest under foil.",
            "In the same pan, blister shishitos over medium-high heat with a pinch of salt until soft and charred in spots (5–7 min). Squeeze lemon; set aside.",
            "Lower heat. Sauté sliced mushrooms and onion in butter until browned. Add garlic and thyme.",
            "Pour in broth; simmer 3–5 minutes. Thicken with a small slurry of cornstarch + water if you want gravy-like sauce. Season to taste.",
            "Slice steak; spoon mushroom gravy over top. Serve with shishitos.",
        ],
        notes="Steakhouse vibes without the heaviness. Shishitos are mild — about 1 in 10 is spicy.",
    ),
    _recipe(
        "Grilled Lemon-Herb Chicken with kale salad",
        slot="dinner",
        servings="3+",
        prep_time="15 min",
        cook_time="20 min",
        ingredients=[
            "chicken thighs or breasts",
            "kale",
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
            "Serve chicken over or beside the kale salad.",
        ],
        notes="Massaging the kale is the secret — it turns bitter leaves into a tender salad. Extra chicken = easy leftovers.",
    ),
]

# Curated grocery list for the week (simple, shoppable names).
GROCERY = [
    # Produce
    ("micro greens", "Produce"),
    ("peaches", "Produce"),
    ("baby potatoes or Yukon gold potatoes", "Produce"),
    ("broccoli or green beans", "Produce"),
    ("bell pepper", "Produce"),
    ("red onion", "Produce"),
    ("lemon", "Produce"),
    ("butter lettuce or romaine", "Produce"),
    ("garlic", "Produce"),
    ("fresh ginger", "Produce"),
    ("green onions", "Produce"),
    ("cucumber", "Produce"),
    ("cherry tomatoes", "Produce"),
    ("fresh parsley or mint", "Produce"),
    ("mushrooms (cremini)", "Produce"),
    ("shishito peppers", "Produce"),
    ("kale", "Produce"),
    ("onion", "Produce"),
    # Meat
    ("turkey bacon", "Meat & Seafood"),
    ("steak (sirloin/flank)", "Meat & Seafood"),
    ("ground turkey", "Meat & Seafood"),
    ("chicken thighs or breasts", "Meat & Seafood"),
    # Dairy
    ("eggs", "Dairy"),
    ("cottage cheese or Greek yogurt", "Dairy"),
    ("halloumi cheese", "Dairy"),
    ("butter", "Dairy"),
    ("parmesan (optional)", "Dairy"),
    # Frozen / Pantry
    ("frozen edamame", "Frozen"),
    ("oat flour or rolled oats", "Pantry"),
    ("protein powder", "Pantry"),
    ("couscous", "Pantry"),
    ("olive oil", "Pantry"),
    ("soy sauce or coconut aminos", "Pantry"),
    ("sesame oil", "Pantry"),
    ("rice vinegar", "Pantry"),
    ("gochujang or sriracha", "Pantry"),
    ("beef broth", "Pantry"),
    ("Dijon mustard", "Pantry"),
    ("baking powder", "Pantry"),
    ("garlic powder", "Pantry"),
    ("smoked paprika", "Pantry"),
    ("dried oregano or Italian seasoning", "Pantry"),
    ("thyme", "Pantry"),
    ("sesame seeds (optional)", "Pantry"),
    ("maple syrup or honey (optional)", "Pantry"),
    ("hot sauce (optional)", "Pantry"),
    ("salt", "Pantry"),
    ("black pepper", "Pantry"),
]


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
        "Couscous halloumi and chicken salad",
        "Mushroom gravy, steak and shishito peppers",
        "Grilled Lemon-Herb Chicken with kale salad",
    ],
    "snack": [],
}


def seed_easy_weekly_menu() -> dict:
    """Ensure recipes exist; if SEED_ID is new, set this week's menu + grocery."""
    existing = {
        (r.get("name") or "").strip().lower(): r
        for r in recipes_store.list_recipes()
    }
    created = 0
    by_name: dict[str, dict] = {}
    for recipe in RECIPES:
        key = recipe["name"].strip().lower()
        if key in existing:
            by_name[recipe["name"]] = existing[key]
            continue
        saved = recipes_store.create_recipe(recipe)
        by_name[recipe["name"]] = saved
        existing[key] = saved
        created += 1

    applied = False
    if recipes_store.get_active_seed() != SEED_ID:
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
        recipes_store.replace_grocery_items([
            {"name": name, "category": cat, "qty": "", "unit": "", "checked": False}
            for name, cat in GROCERY
        ])
        recipes_store.set_active_seed(SEED_ID)
        applied = True
        print(f"[recipes] Applied easy weekly menu seed {SEED_ID} for {WEEK_KEY}.")
    else:
        print(f"[recipes] Easy weekly seed {SEED_ID} already active.")

    if created:
        print(f"[recipes] Created {created} easy weekly recipe(s).")
    return {"created_recipes": created, "applied_menu": applied, "seed_id": SEED_ID, "week_key": WEEK_KEY}
