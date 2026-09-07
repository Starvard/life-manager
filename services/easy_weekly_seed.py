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

# Week of Sep 7, 2026 (ISO 2026-W37)
WEEK_KEY = "2026-W37"
SEED_ID = "easy-weekly-2026-w37-v1"

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


RECIPES = [{'name': 'Protein pancakes + berries',
  'source': 'Life Manager',
  'servings': '3',
  'prep_time': '5 min',
  'cook_time': '12 min',
  'tags': ['easy weekly', 'breakfast', 'healthy'],
  'ingredients': [{'name': 'protein pancake mix', 'qty': '180', 'unit': 'g'},
                  {'name': 'Greek yogurt', 'qty': '170', 'unit': 'g'},
                  {'name': 'blueberries or mixed berries', 'qty': '150', 'unit': 'g'},
                  {'name': 'olive oil', 'qty': '1', 'unit': 'tsp'}],
  'instructions': ['Prepare 180 g protein pancake mix with the water amount on your package. Lightly oil a '
                   'nonstick pan with 1 tsp oil; cook small pancakes over medium-low until bubbles set, then '
                   'flip and finish.',
                   'Serve with 170 g Greek yogurt and 150 g berries.'],
  'notes': 'Repeat 3 mornings. Easy button: frozen protein waffles with the same toppings.'},
 {'name': 'Veggie eggs + turkey bacon',
  'source': 'Life Manager',
  'servings': '3',
  'prep_time': '5 min',
  'cook_time': '15 min',
  'tags': ['easy weekly', 'breakfast', 'healthy'],
  'ingredients': [{'name': 'eggs', 'qty': '6', 'unit': 'ct'},
                  {'name': 'bell peppers', 'qty': '1', 'unit': 'ct'},
                  {'name': 'baby spinach', 'qty': '60', 'unit': 'g'},
                  {'name': 'micro greens', 'qty': '15', 'unit': 'g'},
                  {'name': 'turkey bacon', 'qty': '6', 'unit': 'slices'},
                  {'name': 'olive oil', 'qty': '1', 'unit': 'tsp'},
                  {'name': 'salt', 'qty': '0.25', 'unit': 'tsp'},
                  {'name': 'black pepper', 'qty': '0.125', 'unit': 'tsp'}],
  'instructions': ['Cook 6 slices turkey bacon according to its package. Soften 1 diced pepper in 1 tsp '
                   'olive oil for 4–5 minutes; wilt 60 g spinach.',
                   'Add 6 beaten eggs, 1/4 tsp salt and 1/8 tsp pepper. Gently stir over medium-low until '
                   'set; top with 15 g micro greens and serve with bacon.'],
  'notes': 'Repeat 4 mornings; washed greens and pre-cut peppers save time.'},
 {'name': 'Leftovers from dinner',
  'source': 'Life Manager',
  'servings': '3',
  'prep_time': '2 min',
  'cook_time': '5 min',
  'tags': ['easy weekly', 'lunch', 'healthy'],
  'ingredients': [],
  'instructions': ['Pack dinner leftovers into lunch containers before serving dinner. Refrigerate within 2 '
                   'hours.',
                   'Reheat hot components to 165°F; keep crunchy vegetables and yogurt sauce cold.'],
  'notes': 'For an easy kid backup: peanut butter toast, fruit and a cheese stick.'},
 {'name': 'Yuzu-ginger chicken, broccoli + rice',
  'source': 'Life Manager',
  'servings': '5–6',
  'prep_time': '10 min',
  'cook_time': '35 min',
  'tags': ['easy weekly', 'dinner', 'healthy'],
  'ingredients': [{'name': 'chicken thighs', 'qty': '3', 'unit': 'lb'},
                  {'name': 'broccoli', 'qty': '2', 'unit': 'lb'},
                  {'name': 'long-grain rice', 'qty': '1.5', 'unit': 'cups dry'},
                  {'name': 'yuzu juice (unsweetened)', 'qty': '30', 'unit': 'g'},
                  {'name': 'reduced-sodium soy sauce', 'qty': '40', 'unit': 'g'},
                  {'name': 'honey', 'qty': '20', 'unit': 'g'},
                  {'name': 'ginger', 'qty': '15', 'unit': 'g'},
                  {'name': 'garlic', 'qty': '3', 'unit': 'cloves'},
                  {'name': 'olive oil', 'qty': '2', 'unit': 'tbsp'},
                  {'name': 'salt', 'qty': '0.25', 'unit': 'tsp'}],
  'instructions': ['Heat oven to 425°F. Start 1½ cups dry rice according to the package. Mix 30 g yuzu '
                   'juice, 40 g soy sauce, 20 g honey, 15 g grated ginger and 3 minced garlic cloves. '
                   'Reserve half in a clean serving bowl before touching raw chicken.',
                   'Toss 3 lb boneless chicken thighs with the remaining sauce and 1 tbsp oil. Spread on a '
                   'lined sheet pan. Toss 2 lb broccoli with 1 tbsp oil and 1/4 tsp salt on a second pan.',
                   'Roast chicken 25–35 minutes, until at least 165°F (thighs are more tender around 175°F). '
                   'Add broccoli for the final 18–22 minutes; swap rack positions if needed. Serve over rice '
                   'with reserved sauce.'],
  'notes': 'Needs testing. Use bottled unsweetened yuzu juice, not sweet yuzu tea concentrate. Easy swap: '
           'equal lemon and lime juice. Keep sauce light for the kid. Cook for dinner + next-day lunch for 2 '
           'adults + 1 kid; pack lunch portions before sitting down. Refrigerate within 2 hours; use within '
           '3–4 days, reheating to 165°F. Freeze raw meat for later-week meals and thaw in the fridge.'},
 {'name': 'Sheet-pan shawarma chicken + lemon yogurt',
  'source': 'Life Manager',
  'servings': '5–6',
  'prep_time': '15 min',
  'cook_time': '25 min',
  'tags': ['easy weekly', 'dinner', 'healthy'],
  'ingredients': [{'name': 'chicken breasts or tenders', 'qty': '2.5', 'unit': 'lb'},
                  {'name': 'bell peppers', 'qty': '3', 'unit': 'ct'},
                  {'name': 'red onion', 'qty': '1', 'unit': 'ct'},
                  {'name': 'whole-wheat pitas', 'qty': '6', 'unit': 'ct'},
                  {'name': 'cucumber', 'qty': '1', 'unit': 'ct'},
                  {'name': 'Greek yogurt', 'qty': '240', 'unit': 'g'},
                  {'name': 'lemon', 'qty': '1', 'unit': 'ct'},
                  {'name': 'garlic', 'qty': '3', 'unit': 'cloves'},
                  {'name': 'olive oil', 'qty': '2', 'unit': 'tbsp'},
                  {'name': 'ground cumin', 'qty': '2', 'unit': 'tsp'},
                  {'name': 'smoked paprika', 'qty': '2', 'unit': 'tsp'},
                  {'name': 'cinnamon', 'qty': '0.25', 'unit': 'tsp'},
                  {'name': 'salt', 'qty': '0.75', 'unit': 'tsp'},
                  {'name': 'black pepper', 'qty': '0.25', 'unit': 'tsp'}],
  'instructions': ['Heat oven to 425°F. Slice 2½ lb chicken breast into thick strips. Toss with 3 sliced '
                   'peppers, 1 sliced onion, 2 tbsp oil, 2 tsp cumin, 2 tsp smoked paprika, 1/4 tsp '
                   'cinnamon, 1/2 tsp salt and 1/4 tsp pepper. Spread across two pans.',
                   'Roast 20–25 minutes, turning once, until chicken reaches 165°F. Meanwhile mix 240 g '
                   'yogurt with juice of 1 lemon, 3 finely grated garlic cloves and 1/4 tsp salt.',
                   'Warm 6 pitas and serve with chicken, vegetables, 1 chopped cucumber and lemon yogurt. '
                   'Keep some chicken and cucumber separate for the kid.'],
  'notes': 'Needs testing. Prep ahead: mix the dry spices and yogurt sauce; refrigerate sauce. Extra sauce '
           'works with tacos or raw vegetables. Cook for dinner + next-day lunch for 2 adults + 1 kid; pack '
           'lunch portions before sitting down. Refrigerate within 2 hours; use within 3–4 days, reheating '
           'to 165°F. Freeze raw meat for later-week meals and thaw in the fridge.'},
 {'name': 'Smoky turkey + black bean tacos',
  'source': 'Life Manager',
  'servings': '5–6',
  'prep_time': '10 min',
  'cook_time': '25 min',
  'tags': ['easy weekly', 'dinner', 'healthy'],
  'ingredients': [{'name': 'ground turkey', 'qty': '2', 'unit': 'lb'},
                  {'name': 'black beans', 'qty': '1', 'unit': '15 oz can'},
                  {'name': 'bell peppers', 'qty': '2', 'unit': 'ct'},
                  {'name': 'red onion', 'qty': '1', 'unit': 'ct'},
                  {'name': 'corn tortillas', 'qty': '18', 'unit': 'small'},
                  {'name': 'shredded cabbage', 'qty': '12', 'unit': 'oz'},
                  {'name': 'Greek yogurt', 'qty': '170', 'unit': 'g'},
                  {'name': 'lime', 'qty': '2', 'unit': 'ct'},
                  {'name': 'olive oil', 'qty': '1', 'unit': 'tbsp'},
                  {'name': 'ground cumin', 'qty': '2', 'unit': 'tsp'},
                  {'name': 'smoked paprika', 'qty': '2', 'unit': 'tsp'},
                  {'name': 'garlic powder', 'qty': '1', 'unit': 'tsp'},
                  {'name': 'salt', 'qty': '0.75', 'unit': 'tsp'}],
  'instructions': ['Heat oven to 425°F. Toss 2 sliced peppers and 1 sliced onion with 1 tbsp oil on a large '
                   'rimmed sheet pan. Break 2 lb ground turkey into small loose chunks over the vegetables; '
                   'sprinkle with 2 tsp cumin, 2 tsp smoked paprika, 1 tsp garlic powder and 3/4 tsp salt.',
                   'Roast 12 minutes, break up turkey and stir. Add 1 drained 15 oz can black beans; roast '
                   'another 8–12 minutes until turkey reaches 165°F.',
                   'Mix 170 g yogurt with juice of 1 lime. Toss 12 oz shredded cabbage with juice of the '
                   'second lime. Warm 18 small tortillas; fill with turkey, beans, cabbage and yogurt.'],
  'notes': 'Needs testing. No skillet needed. Leftovers make a taco salad; keep tortillas and slaw separate. '
           'Cook for dinner + next-day lunch for 2 adults + 1 kid; pack lunch portions before sitting down. '
           'Refrigerate within 2 hours; use within 3–4 days, reheating to 165°F. Freeze raw meat for '
           'later-week meals and thaw in the fridge.'},
 {'name': 'Lemon-feta chickpea pasta + roasted vegetables',
  'source': 'Life Manager',
  'servings': '5–6',
  'prep_time': '10 min',
  'cook_time': '30 min',
  'tags': ['easy weekly', 'dinner', 'healthy'],
  'ingredients': [{'name': 'whole-wheat pasta', 'qty': '1', 'unit': 'lb'},
                  {'name': 'chickpeas', 'qty': '2', 'unit': '15 oz cans'},
                  {'name': 'zucchini', 'qty': '3', 'unit': 'ct'},
                  {'name': 'cherry tomatoes', 'qty': '2', 'unit': 'pints'},
                  {'name': 'baby spinach', 'qty': '5', 'unit': 'oz'},
                  {'name': 'feta', 'qty': '6', 'unit': 'oz'},
                  {'name': 'lemon', 'qty': '1', 'unit': 'ct'},
                  {'name': 'garlic', 'qty': '4', 'unit': 'cloves'},
                  {'name': 'olive oil', 'qty': '2', 'unit': 'tbsp'},
                  {'name': 'dried oregano', 'qty': '2', 'unit': 'tsp'},
                  {'name': 'salt', 'qty': '0.5', 'unit': 'tsp'},
                  {'name': 'black pepper', 'qty': '0.25', 'unit': 'tsp'}],
  'instructions': ['Heat oven to 425°F. Toss 3 chopped zucchini, 2 pints cherry tomatoes and 2 drained 15 oz '
                   'cans chickpeas with 2 tbsp oil, 4 minced garlic cloves, 2 tsp oregano, 1/2 tsp salt and '
                   '1/4 tsp pepper. Spread across two pans; roast 25–30 minutes until tomatoes burst and '
                   'zucchini browns.',
                   'Meanwhile cook 1 lb whole-wheat pasta according to the package. Reserve 1 cup pasta '
                   'water, then drain.',
                   'Return pasta to the pot with roasted vegetables, chickpeas, 5 oz spinach, 6 oz crumbled '
                   'feta and zest and juice of 1 lemon. Add pasta water a little at a time, tossing until '
                   'spinach wilts and sauce lightly coats the pasta.'],
  'notes': 'Needs testing. Hold back plain pasta for the kid if useful. Reheat with a splash of water. This '
           'is the meat-free dinner. Cook for dinner + next-day lunch for 2 adults + 1 kid; pack lunch '
           'portions before sitting down. Refrigerate within 2 hours; use within 3–4 days, reheating to '
           '165°F. Freeze raw meat for later-week meals and thaw in the fridge.'},
 {'name': 'Miso-yuzu salmon, green beans + rice',
  'source': 'Life Manager',
  'servings': '5–6',
  'prep_time': '10 min',
  'cook_time': '30 min',
  'tags': ['easy weekly', 'dinner', 'healthy'],
  'ingredients': [{'name': 'salmon fillets', 'qty': '2.5', 'unit': 'lb'},
                  {'name': 'green beans', 'qty': '2', 'unit': 'lb'},
                  {'name': 'long-grain rice', 'qty': '1.5', 'unit': 'cups dry'},
                  {'name': 'white miso', 'qty': '35', 'unit': 'g'},
                  {'name': 'yuzu juice (unsweetened)', 'qty': '25', 'unit': 'g'},
                  {'name': 'honey', 'qty': '15', 'unit': 'g'},
                  {'name': 'ginger', 'qty': '10', 'unit': 'g'},
                  {'name': 'olive oil', 'qty': '1', 'unit': 'tbsp'}],
  'instructions': ['Heat oven to 425°F and start 1½ cups dry rice according to its package. Toss 2 lb '
                   'trimmed green beans with 1 tbsp oil on a large sheet pan; roast 10 minutes.',
                   'Mix 35 g white miso, 25 g yuzu juice, 15 g honey and 10 g grated ginger. Put 2½ lb '
                   'salmon in portions on a separate lined pan and brush with the glaze.',
                   'Roast salmon 10–16 minutes depending on thickness, until the center reaches 145°F, while '
                   'beans finish roasting. Serve with rice; if glaze darkens early, loosely tent with foil.'],
  'notes': 'Needs testing. Cook early in the week or buy frozen. Yuzu juice is shared with chicken; '
           'substitute equal lemon and lime juice if unavailable. Miso supplies salt; taste before adding '
           'more. Cook for dinner + next-day lunch for 2 adults + 1 kid; pack lunch portions before sitting '
           'down. Refrigerate within 2 hours; use within 3–4 days, reheating to 165°F. Freeze raw meat for '
           'later-week meals and thaw in the fridge.'}]

GROCERY = [('blueberries or mixed berries', 'Produce', '2', 'lb'),
 ('bell peppers', 'Produce', '9', 'ct'),
 ('baby spinach', 'Produce', '16', 'oz'),
 ('micro greens', 'Produce', '1', '3 oz clamshell'),
 ('broccoli', 'Produce', '2', 'lb'),
 ('green beans', 'Produce', '2', 'lb'),
 ('red onion', 'Produce', '2', 'ct'),
 ('cucumber', 'Produce', '2', 'ct'),
 ('zucchini', 'Produce', '3', 'ct'),
 ('cherry tomatoes', 'Produce', '2', 'pints'),
 ('shredded cabbage', 'Produce', '1', '12 oz bag'),
 ('lemon', 'Produce', '2', 'ct'),
 ('lime', 'Produce', '2', 'ct'),
 ('ginger', 'Produce', '1', '3 oz piece'),
 ('garlic', 'Produce', '1', 'bulb'),
 ('apples', 'Produce', '6', 'ct'),
 ('bananas', 'Produce', '7', 'ct'),
 ('baby carrots', 'Produce', '1', 'lb'),
 ('chicken thighs', 'Meat & Seafood', '3', 'lb boneless skinless'),
 ('chicken breasts or tenders', 'Meat & Seafood', '2.5', 'lb'),
 ('ground turkey', 'Meat & Seafood', '2', 'lb lean'),
 ('salmon fillets', 'Meat & Seafood', '2.5', 'lb'),
 ('turkey bacon', 'Meat & Seafood', '2', '12 oz packs'),
 ('eggs', 'Dairy', '30', 'ct'),
 ('Greek yogurt', 'Dairy', '2', '32 oz tubs plain'),
 ('feta', 'Dairy', '1', '6 oz pack'),
 ('string cheese or cheese sticks', 'Dairy', '1', '12 ct pack'),
 ('yogurt tubes', 'Dairy', '1', '8 ct box'),
 ('hummus', 'Dairy', '1', '10 oz tub'),
 ('whole-wheat pitas', 'Bakery', '6', 'ct'),
 ('corn tortillas', 'Bakery', '18', 'small'),
 ('sandwich bread', 'Bakery', '1', 'loaf'),
 ('protein pancake mix', 'Pantry', '1', '20 oz box'),
 ('long-grain rice', 'Pantry', '1', '1 lb bag'),
 ('whole-wheat pasta', 'Pantry', '1', 'lb'),
 ('black beans', 'Pantry', '1', '15 oz can'),
 ('chickpeas', 'Pantry', '2', '15 oz cans'),
 ('yuzu juice (unsweetened)', 'Pantry', '1', 'small bottle, at least 60 ml'),
 ('white miso', 'Pantry', '1', 'small tub'),
 ('reduced-sodium soy sauce', 'Pantry', '1', 'bottle'),
 ('honey', 'Pantry', '1', 'bottle'),
 ('olive oil', 'Pantry', '1', 'bottle'),
 ('ground cumin', 'Pantry', '1', 'jar'),
 ('smoked paprika', 'Pantry', '1', 'jar'),
 ('garlic powder', 'Pantry', '1', 'jar'),
 ('cinnamon', 'Pantry', '1', 'jar'),
 ('dried oregano', 'Pantry', '1', 'jar'),
 ('salt', 'Pantry', '1', 'container'),
 ('black pepper', 'Pantry', '1', 'jar'),
 ('peanut butter', 'Pantry', '1', 'jar'),
 ('goldfish crackers', 'Snacks', '1', 'box'),
 ('wheat crackers', 'Snacks', '1', 'box'),
 ('granola bars', 'Snacks', '1', 'box'),
 ('applesauce pouches', 'Snacks', '1', '6 ct box'),
 ('fruit snacks', 'Snacks', '1', 'box'),
 ('chocolate chip cookies', 'Snacks', '1', 'small pack')]

GROCERY_ALIASES = {'soy sauce': 'reduced-sodium soy sauce', 'yuzu juice': 'yuzu juice (unsweetened)', 'bread (sandwich loaf)': 'sandwich bread'}

MENU = {'breakfast': ['Protein pancakes + berries', 'Veggie eggs + turkey bacon'],
 'lunch': ['Leftovers from dinner'],
 'dinner': ['Yuzu-ginger chicken, broccoli + rice',
            'Sheet-pan shawarma chicken + lemon yogurt',
            'Smoky turkey + black bean tacos',
            'Lemon-feta chickpea pasta + roasted vegetables',
            'Miso-yuzu salmon, green beans + rice'],
 'snack': ['Greek yogurt + berries',
           'Apple + peanut butter',
           'Banana',
           'Carrots or cucumber + hummus',
           'Hard-boiled egg + crackers',
           'String cheese',
           'Yogurt tubes',
           'Peanut butter toast',
           'Granola bar',
           'Applesauce pouch',
           'Goldfish',
           'Fruit snacks',
           'A couple chocolate chip cookies']}


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
