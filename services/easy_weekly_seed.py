"""Easy weekly meal plan seed — simple breakfasts/lunches/dinners + grocery.

Bump SEED_ID when regenerating a new week so the menu and grocery list refresh
once on deploy/startup without overwriting later edits every restart.

Household meal preferences (keep this format on the Recipes tab):
- Menu slots: Breakfast / Lunch / Dinner / Snacks (a pool, not per-day boxes)
- Lunch is leftovers from dinner
- Each dinner = dinner + next-day lunch for 2 adults + 1 kid ≈ 5–6 servings
- Easy, high-protein, leftover-friendly; pack lunch containers before sitting down
- No cottage cheese; extra vegetables; no skillet dinners
- Grocery list has amounts; pantry staples already checked stay checked
"""

from __future__ import annotations

from services import recipes_store

# Week of Aug 17, 2026 (ISO 2026-W34)
WEEK_KEY = "2026-W34"
SEED_ID = "easy-weekly-2026-w34-v3"

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
        "Protein pancakes + berries",
        slot="breakfast",
        servings="2",
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
            "Warm or scatter berries on top.",
            "Drizzle a little maple or honey only if you want sweetness.",
        ],
        notes="High-protein pancakes with no cottage cheese. Frozen berries work thawed or warmed in a pan.",
    ),
    _recipe(
        "Turkey sausage scramble with veggies + micro greens",
        slot="breakfast",
        servings="2",
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
            "Brown turkey sausage in a skillet, breaking it up; drain extra fat if needed.",
            "Add chopped bell pepper and zucchini/onion; cook 3–4 minutes until softened.",
            "Stir in a big handful of spinach until just wilted.",
            "Pour in 4 beaten eggs. Stir over medium-low until just set.",
            "Season with salt and pepper. Pile a generous handful of micro greens on top (they wilt from the heat).",
            "Optional: a few drops of hot sauce.",
        ],
        notes="Savory, veggie-heavy scramble. Micro greens go on at the end so they stay fresh and crunchy.",
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
            "Reheat gently until hot (or eat cold if it tastes better that way — pasta and roasted veg often do).",
            "Add a handful of greens or micro greens, or a squeeze of lemon/hot sauce, to freshen it up.",
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
            ("green beans", "1", "lb"),
            ("asparagus", "1", "lb"),
            ("broccoli", "1", "lb"),
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
            "Push potatoes aside. Add green beans, asparagus, and broccoli tossed with oil and salt. Nestle salmon on the pan; brush with honey-mustard.",
            "Roast 12–15 minutes until salmon flakes and veggies are tender-crisp.",
            "Finish with lemon. Pack lunch leftovers before plating dinner.",
        ],
        notes=FAMILY_DINNER_NOTE + " Load the pan with extra veg. Leftover salmon is good cold over greens.",
    ),
    _recipe(
        "Garlic steak bites with roasted veggies",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="15 min",
        cook_time="25 min",
        ingredients=[
            ("steak (sirloin, strip, or flank)", "2–2.5", "lb"),
            ("broccoli", "1.5", "lb"),
            ("bell peppers", "3", ""),
            ("mushrooms", "1", "lb"),
            ("zucchini", "2", ""),
            "olive oil",
            "garlic",
            "garlic powder",
            "smoked paprika",
            "salt",
            "black pepper",
            "lemon",
            "parsley (optional)",
        ],
        instructions=[
            "Heat oven to 450°F. Cut broccoli, peppers, mushrooms, and zucchini into bite-size pieces. Toss with olive oil, salt, pepper, garlic powder, and paprika. Roast 12 minutes.",
            "Pat steak dry; cut into 1-inch bites. Toss with oil, minced garlic, salt, and pepper.",
            "Spread steak bites on the hot pan around the veggies. Roast 8–10 minutes more, until steak is browned and cooked to your liking (don’t overcook).",
            "Rest 3 minutes. Squeeze lemon over everything; scatter parsley if you have it.",
            "Pack lunch leftovers before plating dinner.",
        ],
        notes=FAMILY_DINNER_NOTE + " All sheet-pan — no skillet. Extra peppers, broccoli, mushrooms, and zucchini on the plate.",
    ),
    _recipe(
        "Honey-garlic chicken with carrots, Brussels, and rice",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="15 min",
        cook_time="35 min",
        ingredients=[
            ("chicken thighs", "3", "lb"),
            ("carrots", "2", "lb"),
            ("Brussels sprouts", "1.5", "lb"),
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
            "Heat oven to 425°F. Cut carrots into sticks; trim and halve Brussels sprouts. Toss both with oil, salt, and pepper. Spread on a sheet pan.",
            "Pat chicken dry. Season with salt, pepper, and garlic powder. Nestle on the pan.",
            "Stir honey, soy sauce, and minced garlic. Spoon over the chicken.",
            "Roast 30–35 minutes until chicken is 165°F and veggies are tender. Start the rice when the chicken goes in.",
            "Spoon pan juices over everything. Pack lunch portions of chicken, carrots, Brussels, and rice.",
        ],
        notes=FAMILY_DINNER_NOTE + " Sticky-savory, extra veg, and it reheats well.",
    ),
    _recipe(
        "Chicken pesto protein pasta with veggies",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="15 min",
        cook_time="25 min",
        ingredients=[
            ("chicken breasts or tenders", "2", "lb"),
            ("chickpea or lentil pasta (Banza)", "2", "boxes (8–12 oz)"),
            ("broccoli", "1", "lb"),
            ("baby spinach", "5", "oz"),
            ("cherry tomatoes", "1", "pint"),
            ("zucchini", "2", ""),
            ("basil pesto", "1", "jar"),
            "olive oil",
            "garlic",
            "lemon",
            "parmesan (optional)",
            "salt",
            "black pepper",
        ],
        instructions=[
            "Heat oven to 425°F. Toss chicken with oil, salt, pepper, and minced garlic. On a second pan, toss broccoli, zucchini, and tomatoes with oil and salt. Roast both 18–22 minutes until chicken is 165°F and veggies are tender.",
            "Boil the protein pasta 1–2 minutes less than the box; reserve a splash of pasta water and drain.",
            "In the empty pot, toss hot pasta with pesto and a splash of pasta water until coated.",
            "Slice the chicken. Fold in roasted veggies and a few big handfuls of spinach (it wilts from the heat). Add lemon juice and optional parmesan.",
            "Pack lunch leftovers — this pasta is good cold or reheated with a splash of water.",
        ],
        notes=FAMILY_DINNER_NOTE + " Chickpea/lentil pasta for extra protein. Lots of broccoli, zucchini, tomatoes, and spinach.",
    ),
    _recipe(
        "Sheet-pan sausage with peppers and broccoli",
        slot="dinner",
        servings=FAMILY_DINNER_SERVINGS,
        prep_time="12 min",
        cook_time="30 min",
        ingredients=[
            ("Italian sausage (links)", "2", "lb"),
            ("bell peppers", "4", ""),
            ("red onion", "2", ""),
            ("broccoli", "1.5", "lb"),
            ("zucchini", "2", ""),
            "olive oil",
            "garlic",
            "Italian seasoning",
            "salt",
            "black pepper",
            "lemon",
            "parsley (optional)",
        ],
        instructions=[
            "Heat oven to 425°F. Slice peppers and onion into strips; cut broccoli and zucchini into chunks.",
            "Toss all the vegetables with olive oil, minced garlic, Italian seasoning, salt, and pepper. Spread on a large sheet pan.",
            "Nestle sausage links on top of the veg. Roast 25–30 minutes, turning the sausages once, until browned and cooked through and the vegetables are caramelized.",
            "Slice sausages. Squeeze lemon over the pan; add parsley if you have it.",
            "Pack lunch leftovers before plating dinner.",
        ],
        notes=FAMILY_DINNER_NOTE + " Sheet-pan, not a skillet — peppers, onion, broccoli, and zucchini do most of the work.",
    ),
]

# Grocery rows: (name, category, qty, unit)
# Amounts sized for dinner + next-day lunch (2 adults + 1 kid) across the week.
# A new seed replaces last week’s list; checked pantry staples that still appear stay checked.
GROCERY = [
    # Produce
    ("micro greens", "Produce", "2", "clamshells"),
    ("blueberries or mixed berries", "Produce", "2", "pints"),
    ("baby spinach", "Produce", "10", "oz"),
    ("broccoli", "Produce", "5", "lb"),
    ("asparagus", "Produce", "1", "lb"),
    ("green beans", "Produce", "1", "lb"),
    ("Brussels sprouts", "Produce", "1.5", "lb"),
    ("carrots", "Produce", "3", "lb"),
    ("zucchini", "Produce", "6", ""),
    ("bell peppers", "Produce", "8", ""),
    ("mushrooms", "Produce", "1", "lb"),
    ("cherry tomatoes", "Produce", "1", "pint"),
    ("red onion", "Produce", "2", ""),
    ("baby potatoes or Yukon gold potatoes", "Produce", "2.5", "lb"),
    ("bananas", "Produce", "1", "bunch (~8)"),
    ("apples", "Produce", "6", ""),
    ("oranges", "Produce", "6", ""),
    ("cucumber", "Produce", "2", ""),
    ("lemon", "Produce", "5", ""),
    ("garlic", "Produce", "2", "bulbs"),
    ("parsley (optional)", "Produce", "1", "bunch"),
    ("green onions (optional)", "Produce", "1", "bunch"),
    # Meat
    ("turkey sausage", "Meat & Seafood", "1", "pack"),
    ("salmon fillets", "Meat & Seafood", "2.5", "lb"),
    ("steak (sirloin, strip, or flank)", "Meat & Seafood", "2–2.5", "lb"),
    ("chicken thighs", "Meat & Seafood", "3", "lb"),
    ("chicken breasts or tenders", "Meat & Seafood", "2", "lb"),
    ("Italian sausage (links)", "Meat & Seafood", "2", "lb"),
    # Dairy
    ("eggs", "Dairy", "18", "ct"),
    ("Greek yogurt", "Dairy", "32", "oz"),
    ("parmesan (optional)", "Dairy", "1", "small"),
    ("string cheese or cheese sticks", "Dairy", "1", "pack"),
    ("milk", "Dairy", "1", "half-gal"),
    ("hummus", "Dairy", "1", "tub"),
    ("ranch or yogurt dip", "Dairy", "1", "bottle"),
    ("unsalted butter", "Dairy", "1", "stick"),
    # Bakery / snacks
    ("bread (sandwich loaf)", "Bakery", "1", "loaf"),
    ("trail mix", "Snacks", "1", "bag"),
    ("popcorn (kernels or microwave)", "Snacks", "1", "box"),
    ("peanut butter", "Pantry", "1", "jar"),
    # Pantry
    ("oat flour or rolled oats", "Pantry", "1", "bag"),
    ("protein powder", "Pantry", "", "on hand?"),
    ("chickpea or lentil pasta (Banza)", "Pantry", "2", "boxes"),
    ("basil pesto", "Pantry", "1", "jar"),
    ("long-grain rice", "Pantry", "1", "bag"),
    ("honey", "Pantry", "", "on hand?"),
    ("maple syrup or honey (optional)", "Pantry", "", "on hand?"),
    ("Dijon mustard", "Pantry", "", "on hand?"),
    ("soy sauce or coconut aminos", "Pantry", "", "on hand?"),
    ("olive oil", "Pantry", "", "on hand?"),
    ("garlic powder", "Pantry", "", "on hand?"),
    ("smoked paprika", "Pantry", "", "on hand?"),
    ("Italian seasoning", "Pantry", "", "on hand?"),
    ("baking powder", "Pantry", "", "on hand?"),
    ("cinnamon", "Pantry", "", "on hand?"),
    ("dried dill or parsley (optional)", "Pantry", "", "on hand?"),
    ("hot sauce (optional)", "Pantry", "", "on hand?"),
    ("salt", "Pantry", "", "on hand?"),
    ("black pepper", "Pantry", "", "on hand?"),
]

# Old seed names → canonical names (avoid duplicates after renames)
GROCERY_ALIASES = {
    "cottage cheese": "Greek yogurt",
    "cottage cheese or Greek yogurt": "Greek yogurt",
    "sour cream or Greek yogurt": "Greek yogurt",
    "bell pepper": "bell peppers",
    "chicken thighs or breasts": "chicken thighs",
    "Italian sausage": "Italian sausage (links)",
    "steak (sirloin/flank)": "steak (sirloin, strip, or flank)",
}


MENU = {
    "breakfast": [
        "Protein pancakes + berries",
        "Turkey sausage scramble with veggies + micro greens",
    ],
    "lunch": [
        "Leftovers from dinner",
    ],
    "dinner": [
        "Sheet-pan honey-mustard salmon",
        "Garlic steak bites with roasted veggies",
        "Honey-garlic chicken with carrots, Brussels, and rice",
        "Chicken pesto protein pasta with veggies",
        "Sheet-pan sausage with peppers and broccoli",
    ],
    "snack": [
        "Bell peppers + hummus",
        "Carrots + hummus",
        "Cucumber + ranch",
        "Oranges",
        "Greek yogurt + berries",
        "Cheese + apple slices",
        "Trail mix",
        "Popcorn",
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
