"""Idempotent May 25, 2026 weekly recipe seed."""

from services import recipes_store


def _recipe(slot, name, ingredients, instructions, notes):
    return {
        "name": name,
        "source": "Life Manager",
        "servings": "3+",
        "prep_time": "5 min" if slot == "snack" else "5-12 min",
        "cook_time": "0-5 min" if slot == "snack" else ("15-35 min" if slot == "dinner" else "5-10 min"),
        "tags": ["weekly menu", "may 25", slot],
        "ingredients": [{"name": item, "qty": "", "unit": ""} for item in ingredients],
        "instructions": instructions,
        "notes": notes,
    }


RECIPES = [
    _recipe("breakfast", "High-Protein Scrambled Eggs with Side Salad", ["eggs", "cheese", "salad greens", "fruit", "yogurt or cottage cheese"], ["Whisk 2-3 eggs with salt and a splash of milk or water.", "Cook in butter over medium-low heat, stirring slowly until softly set.", "Fold in cheese at the end.", "Serve with side salad plus fruit, yogurt, or cottage cheese."], "Default high-protein breakfast for Monday and Tuesday."),
    _recipe("breakfast", "Turkey Egg Scramble with Side Salad", ["leftover turkey taco filling", "eggs", "cheese", "salad greens", "salsa"], ["Warm leftover turkey filling in a skillet.", "Pour in beaten eggs and lower the heat.", "Stir gently until just set.", "Top with cheese and salsa.", "Serve with a simple side salad."], "Use the morning after taco melts."),
    _recipe("breakfast", "Chicken Egg Bites with Side Salad", ["eggs", "cottage cheese or ricotta", "cooked chicken", "shredded cheese", "chopped greens", "salad greens"], ["Heat oven to 350°F and grease a muffin tin.", "Whisk 8 eggs with 1/2 cup cottage cheese or ricotta, salt, pepper, and garlic powder.", "Stir in chopped chicken, cheese, and greens.", "Divide into muffin cups.", "Bake 18-24 minutes until set.", "Serve with side salad or refrigerate for fast breakfasts."], "Make after Wednesday dinner."),
    _recipe("breakfast", "Scrambled Eggs with Leftover Chicken and Greens", ["leftover cooked chicken", "eggs", "greens", "cheese", "hot sauce or salsa"], ["Warm chopped chicken in butter or oil.", "Add greens and cook until wilted.", "Pour in beaten eggs and stir until softly set.", "Finish with cheese and hot sauce or salsa."], "Friday breakfast."),
    _recipe("breakfast", "Egg Toast Fruit Plate", ["eggs", "toast or roll", "fruit", "yogurt or cottage cheese"], ["Cook eggs any style.", "Toast bread or warm a roll.", "Add fruit on the side.", "Add yogurt or cottage cheese if more protein is needed."], "Simple Sunday breakfast."),

    _recipe("lunch", "Easy Leftover Fridge Lunch Plate", ["available leftovers", "salad greens", "fruit", "yogurt or cottage cheese"], ["Pull the easiest existing leftovers from the fridge.", "Warm anything that should be hot.", "Add greens, fruit, yogurt, or cottage cheese for protein and freshness."], "Monday lunch before the new dinner flow starts."),
    _recipe("lunch", "Leftover Meatballs Lunch Plate", ["leftover meatballs", "leftover pasta salad", "leftover vegetables", "salad greens"], ["Reheat meatballs gently with a splash of sauce or water.", "Plate leftover pasta salad and vegetables.", "Add greens if you want it lighter and fresher."], "Tuesday lunch from Monday dinner."),
    _recipe("lunch", "Leftover Turkey Taco Lunch", ["leftover turkey black bean filling", "lettuce or greens", "salsa", "cheese"], ["Warm turkey black bean filling until hot.", "Serve over greens as taco salad or in a tortilla as a melt.", "Top with salsa and cheese."], "Wednesday lunch from Tuesday dinner."),
    _recipe("lunch", "Leftover Lemon Garlic Chicken Lunch", ["leftover lemon garlic chicken", "leftover carrots or potatoes", "salad greens", "lemon juice"], ["Slice chicken so it reheats evenly.", "Warm chicken and vegetables until just hot.", "Add greens on the side or underneath.", "Finish with lemon."], "Thursday lunch from Wednesday dinner."),
    _recipe("lunch", "Leftover Peanut Chicken Cauliflower Rice Lunch", ["leftover peanut chicken cauliflower rice", "carrots or cucumber", "lime or lemon"], ["Reheat in short bursts so the sauce does not dry out.", "Add a splash of water if the sauce is too thick.", "Serve with carrots or cucumber and finish with citrus."], "Friday lunch from Thursday dinner."),
    _recipe("lunch", "Leftover Steak and Broccoli Lunch", ["leftover steak", "leftover broccoli", "potatoes, rice, or salad greens"], ["Slice steak thin before reheating.", "Warm steak gently and stop before it overcooks.", "Reheat broccoli separately or eat it cold with lemon.", "Add potatoes, rice, or greens if needed."], "Saturday lunch from Friday dinner."),
    _recipe("lunch", "Leftover Chickpea Banza Pasta Bake Lunch", ["leftover chickpea tomato Banza pasta bake", "salad greens or fruit"], ["Reheat pasta bake covered so it stays moist.", "Add a spoonful of sauce or water first if it looks dry.", "Serve with greens or fruit."], "Sunday lunch from Saturday dinner."),

    _recipe("snack", "Cheese Cracker Fruit Nap Snack", ["cheese", "crackers", "fruit"], ["Cut cheese into snack pieces.", "Add crackers and fruit.", "Keep the portion small enough that dinner still works."], "Monday nap snack."),
    _recipe("snack", "Apple Peanut Butter Nap Snack", ["apple", "peanut butter"], ["Slice the apple.", "Serve peanut butter on the side for dipping.", "Add milk or yogurt if more protein is needed."], "Tuesday nap snack."),
    _recipe("snack", "Blueberry Yogurt Nap Snack", ["yogurt", "blueberries", "chia seeds or nuts"], ["Spoon yogurt into a bowl.", "Add blueberries.", "Sprinkle with chia or nuts if you want it more filling."], "Wednesday nap snack."),
    _recipe("snack", "Egg Fruit Nap Snack", ["egg", "fruit", "salt or everything seasoning"], ["Peel and season the egg.", "Add fruit on the side.", "Use two eggs if this needs to be a more serious snack."], "Thursday nap snack."),
    _recipe("snack", "Cheese Crackers Pickles Nap Snack", ["cheese", "crackers", "pickles"], ["Put cheese, crackers, and pickles on a small plate.", "Add fruit if the snack needs more.", "Keep it no-cook."], "Friday nap snack."),
    _recipe("snack", "Hummus Carrots or Edamame Nap Snack", ["hummus", "carrots", "edamame"], ["Put hummus in a small bowl with carrots.", "If using edamame, microwave or steam it until hot.", "Serve whichever option is easiest."], "Saturday nap snack."),
    _recipe("snack", "Peanut Butter Crackers Fruit Nap Snack", ["crackers", "peanut butter", "fruit"], ["Spread peanut butter on crackers or use it as a dip.", "Add fruit on the side.", "Use this as the easy Sunday snack."], "Sunday nap snack."),

    _recipe("dinner", "Beef Ricotta Meatballs with Leftover Veggies and Pasta Salad", ["ground beef", "ricotta", "egg", "crushed crackers or breadcrumbs", "Italian seasoning", "garlic powder", "leftover vegetables", "leftover pasta salad"], ["Heat oven to 400°F and line a sheet pan with foil or parchment.", "Mix beef, ricotta, egg, crushed crackers, Italian seasoning, garlic powder, salt, and pepper just until combined.", "Roll into small meatballs so they cook quickly.", "Bake 15-18 minutes, until browned and cooked through.", "Warm leftover vegetables while the meatballs cook.", "Serve with leftover vegetables and leftover pasta salad. Add tomato sauce only if you want it."], "Monday dinner. No extra pasta needed because pasta salad is already the side."),
    _recipe("dinner", "Ground Turkey Black Bean Taco Melts", ["ground turkey", "black beans", "salsa", "taco seasoning", "tortillas, bread, or rolls", "cheese", "lettuce or salad greens"], ["Brown ground turkey in a skillet, breaking it up as it cooks.", "Season with taco seasoning and add a splash of water if the pan looks dry.", "Stir in drained black beans and salsa, then simmer 3-5 minutes.", "Put filling on tortillas, bread, or rolls and top with cheese.", "Toast until cheese melts and the outside is crisp.", "Serve with lettuce or a quick side salad."], "Tuesday dinner. Make enough filling for Wednesday lunch and breakfast."),
    _recipe("dinner", "Lemon Garlic Chicken with Carrots and Potatoes", ["chicken", "carrots", "potatoes", "broccoli or green vegetable", "lemon juice", "garlic", "butter or olive oil"], ["Heat oven to 425°F.", "Cut potatoes and carrots small. Toss with oil, salt, pepper, and half the garlic.", "Roast vegetables for 15 minutes.", "Season chicken with salt, pepper, lemon juice, remaining garlic, and oil or butter.", "Add chicken to the pan and roast until cooked through and vegetables are tender.", "Cook broccoli on the side and save extra chicken for egg bites."], "Wednesday dinner. Cook extra chicken on purpose."),
    _recipe("dinner", "Peanut Chicken Cauliflower Rice Bowl", ["leftover cooked chicken", "cauliflower rice", "carrots", "peanut butter", "soy sauce or fish sauce", "lemon or lime juice", "hot water"], ["Whisk peanut butter, soy or fish sauce, citrus, and hot water into a pourable sauce.", "Cook cauliflower rice in a large skillet until hot and some moisture cooks off.", "Add carrots and cook 2-3 minutes.", "Stir in chicken and warm through.", "Toss with peanut sauce and adjust with citrus, hot sauce, or soy sauce."], "Thursday dinner. This is the only bowl dinner this week."),
    _recipe("dinner", "Steak and Broccoli", ["steak", "broccoli", "butter or olive oil", "garlic", "lemon juice", "potatoes or rice"], ["Thaw steak Thursday night and pat it dry.", "Season steak with salt and pepper.", "Cook broccoli first until bright green and tender-crisp.", "Sear steak in a hot skillet with a little oil to preferred doneness.", "Rest steak 5-10 minutes before slicing.", "Finish broccoli with butter or oil, garlic, lemon, salt, and pepper."], "Friday dinner. This replaces the steak sandwiches."),
    _recipe("dinner", "Chickpea Tomato Banza Pasta Bake", ["Banza pasta", "tomato sauce or marinara", "chickpeas", "ricotta", "shredded cheese", "leftover chicken or turkey"], ["Heat oven to 375°F.", "Boil Banza pasta 1-2 minutes less than box directions.", "Mix drained pasta with sauce, drained chickpeas, ricotta, and optional leftover meat.", "Spread in a baking dish and top with cheese.", "Bake 20-25 minutes until bubbling.", "Rest 5 minutes before serving."], "Saturday pantry cleanup dinner."),
    _recipe("dinner", "Snacky Leftover Dinner", ["leftover pasta bake, meatballs, chicken, turkey, or steak", "watermelon or fruit", "cheese and crackers", "eggs, pickles, yogurt, or cottage cheese"], ["Pull out leftovers that need to be used first.", "Warm anything that sounds better hot.", "Put cold sides like fruit, cheese, crackers, pickles, yogurt, or cottage cheese on the table.", "Let everyone build a plate."], "Sunday fridge reset."),
]


def seed_may25_recipes() -> int:
    existing = {
        (recipe.get("name") or "").strip().lower()
        for recipe in recipes_store.list_recipes()
    }
    created = 0
    for recipe in RECIPES:
        key = recipe["name"].strip().lower()
        if key in existing:
            continue
        recipes_store.create_recipe(recipe)
        existing.add(key)
        created += 1
    if created:
        print(f"[recipes] Seeded {created} May 25 recipes.")
    else:
        print("[recipes] May 25 recipes already present.")
    return created
