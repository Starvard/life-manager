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

# Week of Sep 21, 2026 (ISO 2026-W39)
WEEK_KEY = "2026-W39"
SEED_ID = "easy-weekly-2026-w39-v2"

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
  {
    "name": "Protein pancakes + berries",
    "source": "Life Manager",
    "servings": "3",
    "prep_time": "5 min",
    "cook_time": "12 min",
    "tags": [
      "easy weekly",
      "breakfast",
      "budget friendly"
    ],
    "ingredients": [
      {
        "name": "protein pancake mix",
        "qty": "180",
        "unit": "g"
      },
      {
        "name": "Greek yogurt",
        "qty": "170",
        "unit": "g"
      },
      {
        "name": "blueberries or mixed berries",
        "qty": "150",
        "unit": "g"
      },
      {
        "name": "olive oil",
        "qty": "1",
        "unit": "tsp"
      }
    ],
    "instructions": [
      "Prepare 180 g protein pancake mix with water according to the package. Lightly oil a nonstick pan; cook small pancakes over medium-low until bubbles set, then flip and finish.",
      "Serve with 170 g Greek yogurt and 150 g berries. Make extra pancakes and freeze for toaster reheating."
    ],
    "notes": "Repeat 4 mornings. Adults take larger portions, Rosemary a smaller plate. Use a just-add-water protein pancake mix."
  },
  {
    "name": "Veggie scrambled eggs + turkey bacon toast",
    "source": "Life Manager",
    "servings": "3",
    "prep_time": "5 min",
    "cook_time": "15 min",
    "tags": [
      "easy weekly",
      "breakfast",
      "budget friendly"
    ],
    "ingredients": [
      {
        "name": "eggs",
        "qty": "6",
        "unit": "ct"
      },
      {
        "name": "bell peppers",
        "qty": "1",
        "unit": "ct"
      },
      {
        "name": "baby spinach",
        "qty": "60",
        "unit": "g"
      },
      {
        "name": "micro greens",
        "qty": "15",
        "unit": "g"
      },
      {
        "name": "turkey bacon",
        "qty": "6",
        "unit": "slices"
      },
      {
        "name": "sandwich bread",
        "qty": "3",
        "unit": "slices"
      },
      {
        "name": "olive oil",
        "qty": "1",
        "unit": "tsp"
      },
      {
        "name": "salt",
        "qty": "0.25",
        "unit": "tsp"
      },
      {
        "name": "black pepper",
        "qty": "0.125",
        "unit": "tsp"
      }
    ],
    "instructions": [
      "Cook 6 slices turkey bacon according to the package. Finely dice 1 bell pepper; soften in 1 tsp olive oil for 4–5 minutes. Add 60 g spinach and cook until wilted.",
      "Beat 6 eggs with 1/4 tsp salt and 1/8 tsp pepper. Add to vegetables and gently stir over medium-low until set.",
      "Serve with 3 slices toast and 15 g micro greens. Adults take larger portions, Rosemary a smaller plate."
    ],
    "notes": "Repeat 3 mornings. Chop the peppers in advance. A fresh savory breakfast with vegetables and micro greens."
  },
  {
    "name": "Leftovers + easy backup meals",
    "source": "Life Manager",
    "servings": "3",
    "prep_time": "5 min",
    "cook_time": "10 min",
    "tags": [
      "easy weekly",
      "lunch",
      "budget friendly"
    ],
    "ingredients": [],
    "instructions": [
      "Reserve lunch portions when serving each dinner.",
      "For the first lunch or the two nights without a planned dinner: egg-and-cheese toast with fruit and vegetables, or black bean and cheese quesadillas with salsa and carrots.",
      "For quesadillas, mash 1 drained can black beans; divide between 4 tortillas with 100 g cheese. Fold and bake at 400°F for 10–12 minutes, turning once. Repeat if needed. Keep extra bread and pasta for Rosemary."
    ],
    "notes": "Grocery includes 12 extra eggs, 2 extra cans beans, tortillas, cheese and extra pasta for these flexible meals."
  },
  {
    "name": "Honey-mustard chicken, potatoes + carrots",
    "source": "Life Manager",
    "servings": "5–6",
    "prep_time": "12 min",
    "cook_time": "45–50 min",
    "tags": [
      "easy weekly",
      "dinner",
      "budget friendly"
    ],
    "ingredients": [
      {
        "name": "chicken thighs",
        "qty": "3",
        "unit": "lb"
      },
      {
        "name": "potatoes",
        "qty": "2",
        "unit": "lb"
      },
      {
        "name": "carrots",
        "qty": "1.5",
        "unit": "lb"
      },
      {
        "name": "Dijon mustard",
        "qty": "45",
        "unit": "g"
      },
      {
        "name": "honey",
        "qty": "30",
        "unit": "g"
      },
      {
        "name": "olive oil",
        "qty": "2",
        "unit": "tbsp"
      },
      {
        "name": "garlic powder",
        "qty": "1",
        "unit": "tsp"
      },
      {
        "name": "salt",
        "qty": "0.75",
        "unit": "tsp"
      },
      {
        "name": "black pepper",
        "qty": "0.25",
        "unit": "tsp"
      }
    ],
    "instructions": [
      "Heat oven to 425°F. Cut potatoes into 3/4-inch pieces and carrots into thin sticks. Toss with 1 tbsp oil, half the salt and pepper; spread across two rimmed pans. Roast 15 minutes.",
      "Mix mustard, honey, remaining oil, garlic powder and remaining salt. Coat boneless chicken thighs and nestle on the pans, keeping everything in a single layer.",
      "Roast another 25–35 minutes until chicken reaches at least 165°F and vegetables are tender. Swap racks halfway."
    ],
    "notes": "Mild, sweet-savory flavor. Use two pans so vegetables roast well. Cook for dinner + next-day lunch for 2 adults + 1 kid; pack lunch portions before sitting down."
  },
  {
    "name": "Oven turkey meatballs, spaghetti + broccoli",
    "source": "Life Manager",
    "servings": "5–6",
    "prep_time": "15 min",
    "cook_time": "25 min",
    "tags": [
      "easy weekly",
      "dinner",
      "budget friendly"
    ],
    "ingredients": [
      {
        "name": "ground turkey",
        "qty": "2",
        "unit": "lb"
      },
      {
        "name": "eggs",
        "qty": "1",
        "unit": "ct"
      },
      {
        "name": "rolled oats",
        "qty": "50",
        "unit": "g"
      },
      {
        "name": "milk",
        "qty": "60",
        "unit": "ml"
      },
      {
        "name": "garlic powder",
        "qty": "1",
        "unit": "tsp"
      },
      {
        "name": "dried oregano",
        "qty": "2",
        "unit": "tsp"
      },
      {
        "name": "salt",
        "qty": "0.5",
        "unit": "tsp"
      },
      {
        "name": "black pepper",
        "qty": "0.25",
        "unit": "tsp"
      },
      {
        "name": "whole-wheat pasta",
        "qty": "1",
        "unit": "lb"
      },
      {
        "name": "marinara sauce",
        "qty": "24",
        "unit": "oz"
      },
      {
        "name": "broccoli",
        "qty": "2",
        "unit": "lb"
      },
      {
        "name": "olive oil",
        "qty": "1",
        "unit": "tbsp"
      }
    ],
    "instructions": [
      "Heat oven to 425°F. Mix oats and milk; soak 5 minutes. Mix with turkey, egg, garlic powder, oregano, salt and pepper. Form 18 meatballs on a lined pan.",
      "Toss broccoli with oil on a second pan. Roast both for 18–25 minutes, until meatballs reach 165°F and broccoli is tender.",
      "Meanwhile cook pasta according to package. Drain, reserving some water; warm marinara in the pasta pot and add meatballs. Serve with pasta and broccoli."
    ],
    "notes": "Leave a little pasta plain for Rosemary; reheat leftovers with a splash of water. Cook for dinner + next-day lunch for 2 adults + 1 kid; pack lunch portions before sitting down."
  },
  {
    "name": "Sheet-pan chicken fajitas + black beans",
    "source": "Life Manager",
    "servings": "5–6",
    "prep_time": "12 min",
    "cook_time": "30 min",
    "tags": [
      "easy weekly",
      "dinner",
      "budget friendly"
    ],
    "ingredients": [
      {
        "name": "chicken thighs",
        "qty": "3",
        "unit": "lb"
      },
      {
        "name": "bell peppers",
        "qty": "3",
        "unit": "ct"
      },
      {
        "name": "yellow onions",
        "qty": "1",
        "unit": "ct"
      },
      {
        "name": "black beans",
        "qty": "1",
        "unit": "15 oz can"
      },
      {
        "name": "whole-wheat tortillas",
        "qty": "12",
        "unit": "small"
      },
      {
        "name": "Greek yogurt",
        "qty": "170",
        "unit": "g"
      },
      {
        "name": "salsa",
        "qty": "150",
        "unit": "g"
      },
      {
        "name": "olive oil",
        "qty": "2",
        "unit": "tbsp"
      },
      {
        "name": "ground cumin",
        "qty": "2",
        "unit": "tsp"
      },
      {
        "name": "smoked paprika",
        "qty": "2",
        "unit": "tsp"
      },
      {
        "name": "garlic powder",
        "qty": "1",
        "unit": "tsp"
      },
      {
        "name": "salt",
        "qty": "0.75",
        "unit": "tsp"
      }
    ],
    "instructions": [
      "Heat oven to 425°F. Slice boneless chicken thighs into strips; slice peppers and onion. Toss with oil, cumin, paprika, garlic powder and salt. Divide over two lined pans.",
      "Roast 22–30 minutes, stirring once, until chicken reaches 165°F. Warm drained black beans in the microwave or a small pot.",
      "Serve in warm tortillas with beans, yogurt and salsa. Keep the filling separate for lunch."
    ],
    "notes": "Mild seasoning; serve Rosemary the components separately if preferred. Cook for dinner + next-day lunch for 2 adults + 1 kid; pack lunch portions before sitting down."
  },
  {
    "name": "Mild chickpea, sweet potato + spinach curry",
    "source": "Life Manager",
    "servings": "5–6",
    "prep_time": "10 min",
    "cook_time": "30 min",
    "tags": [
      "easy weekly",
      "dinner",
      "budget friendly"
    ],
    "ingredients": [
      {
        "name": "chickpeas",
        "qty": "3",
        "unit": "15 oz cans"
      },
      {
        "name": "sweet potatoes",
        "qty": "1.5",
        "unit": "lb"
      },
      {
        "name": "baby spinach",
        "qty": "150",
        "unit": "g"
      },
      {
        "name": "yellow onions",
        "qty": "1",
        "unit": "ct"
      },
      {
        "name": "light coconut milk",
        "qty": "1",
        "unit": "13.5 oz can"
      },
      {
        "name": "diced tomatoes",
        "qty": "1",
        "unit": "14.5 oz can"
      },
      {
        "name": "long-grain rice",
        "qty": "1.5",
        "unit": "cups dry"
      },
      {
        "name": "mild curry powder",
        "qty": "2",
        "unit": "tsp"
      },
      {
        "name": "olive oil",
        "qty": "1",
        "unit": "tbsp"
      },
      {
        "name": "salt",
        "qty": "0.5",
        "unit": "tsp"
      }
    ],
    "instructions": [
      "Start rice according to package. Dice onion and peel/cut sweet potatoes into 1/2-inch cubes.",
      "In a large pot, soften onion in oil for 5 minutes. Stir in curry powder for 30 seconds; add sweet potatoes, drained chickpeas, coconut milk, tomatoes, 240 ml water and salt.",
      "Cover and simmer 20–25 minutes, stirring occasionally, until potatoes are tender; add water if needed. Stir in spinach until wilted and serve over rice."
    ],
    "notes": "One inexpensive meat-free dinner. Start with 1 tsp curry powder for a very mild version; add more at the table. Cook for dinner + next-day lunch for 2 adults + 1 kid; pack lunch portions before sitting down."
  },
  {
    "name": "Sheet-pan chicken sausage, sweet potatoes + green beans",
    "source": "Life Manager",
    "servings": "5–6",
    "prep_time": "10 min",
    "cook_time": "40 min",
    "tags": [
      "easy weekly",
      "dinner",
      "budget friendly"
    ],
    "ingredients": [
      {
        "name": "fully cooked chicken sausage",
        "qty": "1.5",
        "unit": "lb"
      },
      {
        "name": "sweet potatoes",
        "qty": "2.5",
        "unit": "lb"
      },
      {
        "name": "green beans",
        "qty": "2",
        "unit": "lb"
      },
      {
        "name": "olive oil",
        "qty": "2",
        "unit": "tbsp"
      },
      {
        "name": "smoked paprika",
        "qty": "1",
        "unit": "tsp"
      },
      {
        "name": "garlic powder",
        "qty": "1",
        "unit": "tsp"
      },
      {
        "name": "salt",
        "qty": "0.5",
        "unit": "tsp"
      },
      {
        "name": "Greek yogurt",
        "qty": "170",
        "unit": "g"
      },
      {
        "name": "Dijon mustard",
        "qty": "15",
        "unit": "g"
      }
    ],
    "instructions": [
      "Heat oven to 425°F. Cut sweet potatoes into 3/4-inch cubes. Toss with oil, paprika, garlic powder and salt across two sheet pans. Roast 15 minutes.",
      "Add green beans and sliced fully cooked chicken sausage. Toss and roast another 20–25 minutes, until potatoes are tender and sausage is heated according to package directions.",
      "Mix yogurt and mustard for a quick dip. Cut Rosemary's sausage lengthwise into small pieces."
    ],
    "notes": "Frozen green beans work: add straight from frozen, spread well and allow a few extra minutes. Cook for dinner + next-day lunch for 2 adults + 1 kid; pack lunch portions before sitting down."
  }
]

GROCERY = [
  [
    "bananas",
    "Produce",
    "12",
    "ct"
  ],
  [
    "apples",
    "Produce",
    "8",
    "ct"
  ],
  [
    "clementines",
    "Produce",
    "1",
    "3 lb bag"
  ],
  [
    "bell peppers",
    "Produce",
    "6",
    "ct"
  ],
  [
    "baby spinach",
    "Produce",
    "1",
    "12 oz bag"
  ],
  [
    "micro greens",
    "Produce",
    "1",
    "2 oz pack"
  ],
  [
    "potatoes",
    "Produce",
    "1",
    "3 lb bag"
  ],
  [
    "sweet potatoes",
    "Produce",
    "4",
    "lb"
  ],
  [
    "carrots",
    "Produce",
    "1",
    "3 lb bag"
  ],
  [
    "cucumber",
    "Produce",
    "2",
    "ct"
  ],
  [
    "yellow onions",
    "Produce",
    "2",
    "ct"
  ],
  [
    "broccoli",
    "Frozen",
    "2",
    "lb"
  ],
  [
    "green beans",
    "Frozen",
    "2",
    "lb"
  ],
  [
    "blueberries or mixed berries",
    "Frozen",
    "2",
    "lb"
  ],
  [
    "chicken thighs",
    "Meat & Seafood",
    "6",
    "lb boneless skinless"
  ],
  [
    "ground turkey",
    "Meat & Seafood",
    "2",
    "lb lean"
  ],
  [
    "fully cooked chicken sausage",
    "Meat & Seafood",
    "1.5",
    "lb"
  ],
  [
    "turkey bacon",
    "Meat & Seafood",
    "2",
    "packs totaling at least 18 slices"
  ],
  [
    "eggs",
    "Dairy",
    "36",
    "ct"
  ],
  [
    "milk",
    "Dairy",
    "1",
    "gallon"
  ],
  [
    "Greek yogurt",
    "Dairy",
    "3",
    "32 oz tubs plain"
  ],
  [
    "shredded cheese",
    "Dairy",
    "1",
    "16 oz bag"
  ],
  [
    "string cheese or cheese sticks",
    "Dairy",
    "2",
    "12 ct packs"
  ],
  [
    "yogurt tubes",
    "Dairy",
    "3",
    "8 ct boxes"
  ],
  [
    "hummus",
    "Dairy",
    "2",
    "10 oz tubs"
  ],
  [
    "sandwich bread",
    "Bakery",
    "2",
    "loaves"
  ],
  [
    "whole-wheat tortillas",
    "Bakery",
    "2",
    "10 ct packs, small"
  ],
  [
    "rolled oats",
    "Pantry",
    "1",
    "18 oz container"
  ],
  [
    "peanut butter",
    "Pantry",
    "1",
    "16 oz jar"
  ],
  [
    "long-grain rice",
    "Pantry",
    "1",
    "1 lb bag"
  ],
  [
    "whole-wheat pasta",
    "Pantry",
    "2",
    "1 lb boxes (one dinner; one backup)"
  ],
  [
    "marinara sauce",
    "Pantry",
    "1",
    "24 oz jar"
  ],
  [
    "black beans",
    "Pantry",
    "3",
    "15 oz cans"
  ],
  [
    "chickpeas",
    "Pantry",
    "3",
    "15 oz cans"
  ],
  [
    "light coconut milk",
    "Pantry",
    "1",
    "13.5 oz can"
  ],
  [
    "diced tomatoes",
    "Pantry",
    "1",
    "14.5 oz can"
  ],
  [
    "salsa",
    "Pantry",
    "1",
    "16 oz jar"
  ],
  [
    "Dijon mustard",
    "Pantry",
    "1",
    "small jar"
  ],
  [
    "honey",
    "Pantry",
    "1",
    "small bottle"
  ],
  [
    "olive oil",
    "Pantry",
    "1",
    "bottle"
  ],
  [
    "garlic powder",
    "Pantry",
    "1",
    "jar"
  ],
  [
    "ground cumin",
    "Pantry",
    "1",
    "jar"
  ],
  [
    "smoked paprika",
    "Pantry",
    "1",
    "jar"
  ],
  [
    "dried oregano",
    "Pantry",
    "1",
    "jar"
  ],
  [
    "mild curry powder",
    "Pantry",
    "1",
    "jar"
  ],
  [
    "cinnamon",
    "Pantry",
    "1",
    "jar"
  ],
  [
    "salt",
    "Pantry",
    "1",
    "container"
  ],
  [
    "black pepper",
    "Pantry",
    "1",
    "jar"
  ],
  [
    "goldfish crackers",
    "Snacks",
    "1",
    "large box"
  ],
  [
    "wheat crackers",
    "Snacks",
    "1",
    "box"
  ],
  [
    "granola bars",
    "Snacks",
    "1",
    "12 ct box"
  ],
  [
    "applesauce pouches",
    "Snacks",
    "1",
    "18 ct box unsweetened"
  ],
  [
    "fruit snacks",
    "Snacks",
    "1",
    "small box"
  ],
  [
    "chocolate chip cookies",
    "Snacks",
    "1",
    "small pack"
  ],
  [
    "protein pancake mix",
    "Pantry",
    "2",
    "20 oz boxes, just-add-water"
  ],
  [
    "mini whole-wheat bagels",
    "Bakery",
    "1",
    "12 ct bag"
  ],
  [
    "cream cheese",
    "Dairy",
    "1",
    "8 oz tub"
  ],
  [
    "deli turkey",
    "Meat & Seafood",
    "1",
    "8 oz pack"
  ],
  [
    "pretzels",
    "Snacks",
    "1",
    "16 oz bag"
  ],
  [
    "graham crackers",
    "Snacks",
    "1",
    "14 oz box"
  ],
  [
    "mini banana muffins",
    "Bakery",
    "1",
    "12 ct pack"
  ],
  [
    "raisins",
    "Snacks",
    "1",
    "6 ct pack of small boxes"
  ],
  [
    "shelled edamame",
    "Frozen",
    "1",
    "12 oz bag"
  ],
  [
    "whole-grain cereal",
    "Pantry",
    "1",
    "12 oz box"
  ],
  [
    "avocados",
    "Produce",
    "3",
    "ct"
  ],
  [
    "frozen mango",
    "Frozen",
    "1",
    "16 oz bag"
  ]
]

GROCERY_ALIASES = {"bread (sandwich loaf)":"sandwich bread","corn tortillas":"whole-wheat tortillas","red onion":"yellow onions"}

MENU = {
  "breakfast": [
    "Protein pancakes + berries",
    "Veggie scrambled eggs + turkey bacon toast"
  ],
  "lunch": [
    "Leftovers + easy backup meals"
  ],
  "dinner": [
    "Honey-mustard chicken, potatoes + carrots",
    "Oven turkey meatballs, spaghetti + broccoli",
    "Sheet-pan chicken fajitas + black beans",
    "Mild chickpea, sweet potato + spinach curry",
    "Sheet-pan chicken sausage, sweet potatoes + green beans"
  ],
  "snack": [
    "Yogurt tube + banana",
    "String cheese + apple slices",
    "Greek yogurt + thawed berries",
    "Peanut butter banana toast",
    "Apple slices + peanut butter",
    "Hummus + cucumber strips",
    "Hummus + carrot sticks",
    "Hard-boiled egg + wheat crackers",
    "Cheese + crackers",
    "Clementine + cheese stick",
    "Applesauce pouch + peanut butter toast",
    "Granola bar + milk",
    "Goldfish + string cheese",
    "Small bean-and-cheese tortilla",
    "Cinnamon yogurt + banana",
    "Fruit snacks + cheese stick",
    "A couple chocolate chip cookies + milk",
    "Mini whole-wheat bagel + cream cheese",
    "Turkey-and-cheese roll-ups",
    "Pretzels + hummus",
    "Graham crackers + peanut butter",
    "Mini banana muffin + milk",
    "Raisins + wheat crackers",
    "Steamed shelled edamame",
    "Whole-grain cereal + milk",
    "Avocado toast",
    "Mango-banana yogurt smoothie",
    "Apple slices + cinnamon yogurt dip",
    "Mini bagel pizza",
    "Graham crackers + yogurt"
  ]
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
    previous_seed = recipes_store.get_active_seed()
    apply_seed = previous_seed != SEED_ID
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
        # A prior purchase does not imply this week's fresh food is still on hand.
        # Preserve checked pantry staples; restock meal-specific cans and sauces.
        restock_names = {
            name.lower() for name, category, _, _ in GROCERY
            if category != "Pantry" or name in {
                "marinara sauce", "black beans", "chickpeas",
                "light coconut milk", "diced tomatoes", "salsa",
            }
        }
        # Same-week revision: keep existing purchase checks except increased amounts.
        if previous_seed == "easy-weekly-2026-w39-v1":
            restock_names = {
                "blueberries or mixed berries", "milk", "string cheese or cheese sticks",
                "yogurt tubes", "hummus", "granola bars", "applesauce pouches",
            }
        refreshed = grocery_result["items"]
        for item in refreshed:
            if item["name"].lower() in restock_names:
                item["checked"] = False
        recipes_store.replace_grocery_items(refreshed)
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
