"""Easy weekly meal plan seed — simple breakfasts/lunches/dinners + grocery.

Bump SEED_ID when regenerating a new week so the menu and grocery list refresh
once on deploy/startup without overwriting later edits every restart.
"""

from __future__ import annotations

from services import recipes_store

# Week of Aug 3, 2026 (ISO 2026-W32)
WEEK_KEY = "2026-W32"
SEED_ID = "easy-weekly-2026-w32-v2"


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
        "Grilled Halloumi Orzo Salad",
        slot="dinner",
        servings="6",
        prep_time="15 min",
        cook_time="20 min",
        source="eMeals",
        ingredients=[
            ("orzo", "1 1/2", "cups"),
            ("olive oil vinaigrette", "6", "Tbsp"),
            ("halloumi cheese (8-oz blocks)", "1 1/2", "blocks"),
            ("red onion (small, cut into wedges)", "1", ""),
            ("red bell peppers (halved and seeded)", "2", ""),
            ("zucchini (cut into planks)", "3", ""),
            ("fresh basil (chopped)", "1/2", "cup"),
            ("balsamic glaze", "3", "Tbsp"),
        ],
        instructions=[
            "Preheat grill (or grill pan) to medium-high heat. Cook orzo according to package directions; drain, toss with 2 Tbsp vinaigrette.",
            "Brush cheese, bell peppers, and zucchini with remaining 1/4 cup vinaigrette. Grill vegetables, covered, 8 minutes or until tender and slightly charred. Grill cheese, covered, 2 minutes per side or until grill marks appear.",
            "Cut bell pepper halves into 1-inch pieces. Divide orzo, vegetables, cheese, and basil among 6 serving bowls; drizzle with balsamic glaze.",
        ],
        notes="Halloumi tip: cut into ¾-inch-thick slices before grilling. Leftovers keep well cold for lunch.",
    ),
    _recipe(
        "Beef Fillet with Chanterelle Marsala Sauce",
        slot="dinner",
        servings="4",
        prep_time="15 min",
        cook_time="30 min",
        source="Justin Courson",
        ingredients=[
            ("beef fillets (8-oz)", "4", ""),
            ("salt", "", ""),
            ("freshly ground black pepper", "", ""),
            ("neutral oil (corn or canola)", "1–2", "Tbsp"),
            ("unsalted butter", "5", "Tbsp"),
            ("garlic (minced)", "1", "tsp"),
            ("fresh chanterelle mushrooms", "1", "lb"),
            ("fresh thyme (chopped)", "1", "tsp"),
            ("dry marsala wine", "1/2", "cup"),
            ("heavy cream", "1", "cup"),
        ],
        instructions=[
            "Preheat the oven to 400°F.",
            "Season the beef fillets with salt and pepper to taste.",
            "Heat a large skillet over high heat until smoking. Add the oil and place the fillets in the skillet. Sear 2–3 minutes until browned and they release easily; flip and brown the other side a couple of minutes.",
            "Place the skillet with the meat in the oven and cook 6 minutes for medium-rare (or longer for desired doneness).",
            "Remove the skillet from the oven, add 4 tablespoons of butter, and baste the meat about 1½ minutes. Transfer meat to a platter and rest 10 minutes.",
            "In the same skillet, melt the remaining 1 tablespoon butter over medium heat. Add garlic and cook until it starts to sweat (1–2 minutes). Add chanterelles, salt, pepper, and thyme. Cook, stirring frequently, 6–7 minutes until mushrooms release their liquid.",
            "Add marsala and cook until reduced by half. Add heavy cream and reduce by about a quarter (~4 minutes) until the sauce takes on a lovely caramel color.",
            "Serve the fillets covered with the chanterelle marsala sauce.",
        ],
        notes="From Justin Courson (Mississippi). Chanterelles pair beautifully with steak; cremini can stand in if chanterelles aren’t available.",
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
    ("red bell peppers", "Produce"),
    ("zucchini", "Produce"),
    ("lemon", "Produce"),
    ("butter lettuce or romaine", "Produce"),
    ("garlic", "Produce"),
    ("fresh ginger", "Produce"),
    ("green onions", "Produce"),
    ("fresh basil", "Produce"),
    ("fresh chanterelle mushrooms", "Produce"),
    ("kale", "Produce"),
    ("cherry tomatoes or cucumber", "Produce"),
    # Meat
    ("turkey bacon", "Meat & Seafood"),
    ("steak (sirloin/flank)", "Meat & Seafood"),
    ("beef fillets (8-oz)", "Meat & Seafood"),
    ("ground turkey", "Meat & Seafood"),
    ("chicken thighs or breasts", "Meat & Seafood"),
    # Dairy
    ("eggs", "Dairy"),
    ("cottage cheese or Greek yogurt", "Dairy"),
    ("halloumi cheese (8-oz blocks)", "Dairy"),
    ("unsalted butter", "Dairy"),
    ("heavy cream", "Dairy"),
    ("parmesan (optional)", "Dairy"),
    # Frozen / Pantry
    ("frozen edamame", "Frozen"),
    ("oat flour or rolled oats", "Pantry"),
    ("protein powder", "Pantry"),
    ("orzo", "Pantry"),
    ("olive oil vinaigrette", "Pantry"),
    ("balsamic glaze", "Pantry"),
    ("olive oil", "Pantry"),
    ("neutral oil (corn or canola)", "Pantry"),
    ("dry marsala wine", "Pantry"),
    ("soy sauce or coconut aminos", "Pantry"),
    ("sesame oil", "Pantry"),
    ("rice vinegar", "Pantry"),
    ("gochujang or sriracha", "Pantry"),
    ("Dijon mustard", "Pantry"),
    ("baking powder", "Pantry"),
    ("garlic powder", "Pantry"),
    ("smoked paprika", "Pantry"),
    ("dried oregano or Italian seasoning", "Pantry"),
    ("fresh thyme", "Pantry"),
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
        "Grilled Halloumi Orzo Salad",
        "Beef Fillet with Chanterelle Marsala Sauce",
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
    if updated:
        print(f"[recipes] Updated {updated} easy weekly recipe(s).")
    return {
        "created_recipes": created,
        "updated_recipes": updated,
        "applied_menu": applied,
        "seed_id": SEED_ID,
        "week_key": WEEK_KEY,
    }
