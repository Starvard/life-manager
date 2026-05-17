(function () {
  // Approved weekly menu filler for May 18, 2026.
  // Filename kept for compatibility with the existing base.html include.
  const WEEK_KEY = '2026-W21';
  const WEEK_START = '2026-05-18';
  const SLOTS = ['breakfast', 'lunch', 'snack', 'dinner'];

  const STARTERS = [
    ['Greek Yogurt Blueberry Bowl', 'breakfast', ['plain Greek yogurt', 'blueberries', 'chia seeds', 'toasted walnuts', 'cinnamon'], 'Monday breakfast.', '3', '5 min', '0 min'],
    ['Garden Egg Scramble', 'breakfast', ['eggs', 'greens', 'cherry tomatoes', 'avocado', 'olive oil'], 'Tuesday breakfast.', '3', '5 min', '10 min'],
    ['Tomato and Greens Egg Bites', 'breakfast', ['eggs', 'cottage cheese or Greek yogurt', 'cherry tomatoes', 'greens', 'cheddar or feta'], 'Wednesday and Thursday breakfast.', '6', '10 min', '20 min'],
    ['Cottage Cheese Berry Bowl', 'breakfast', ['cottage cheese', 'blueberries', 'chia seeds', 'walnuts'], 'Friday breakfast.', '3', '5 min', '0 min'],
    ['Protein Pancakes with Greek Yogurt and Berries', 'breakfast', ['protein pancake mix or batter', 'plain Greek yogurt', 'blueberries', 'walnuts'], 'Saturday breakfast.', '3', '10 min', '15 min'],
    ['Veggie Omelet with Avocado', 'breakfast', ['eggs', 'greens', 'cherry tomatoes', 'avocado', 'cheese'], 'Sunday breakfast.', '3', '5 min', '10 min'],

    ['Leftover Beef Chuck Bowls', 'lunch', ['leftover beef chuck', 'greens', 'avocado', 'Greek yogurt', 'lime'], 'Monday lunch from last week\'s beef chuck bowls.', '3', '10 min', '0 min'],
    ['Shrimp-Chicken Vegetable Bowls', 'lunch', ['leftover shrimp and chicken', 'greens', 'cauliflower rice', 'lemon'], 'Tuesday lunch from Monday dinner.', '3', '5 min', '5 min'],
    ['Turkey Taco Salad', 'lunch', ['leftover turkey taco meat', 'greens', 'avocado', 'salsa', 'Greek yogurt lime crema'], 'Wednesday lunch from Tuesday dinner.', '3', '10 min', '0 min'],
    ['Burger Lettuce Cups', 'lunch', ['leftover burger patties', 'lettuce', 'cucumber', 'pickles', 'yogurt burger sauce'], 'Thursday lunch from Wednesday dinner.', '3', '10 min', '0 min'],
    ['Fajita Chicken Salad', 'lunch', ['leftover fajita chicken', 'greens', 'cucumber', 'avocado', 'salsa'], 'Friday lunch from Thursday dinner.', '3', '10 min', '0 min'],
    ['Sesame Beef Broccoli Bowls with Cucumber Salad', 'lunch', ['leftover sesame beef and broccoli', 'cucumber', 'lime', 'cauliflower rice'], 'Saturday lunch from Friday dinner.', '3', '10 min', '5 min'],
    ['Turkey Meatball Salad Bowls', 'lunch', ['leftover turkey meatballs', 'greens', 'cucumber tomato salad', 'yogurt herb sauce'], 'Sunday lunch from Saturday dinner.', '3', '10 min', '0 min'],

    ['Lemon Garlic Shrimp and Chicken Bowls', 'dinner', ['shrimp', 'chicken breast', 'broccoli', 'zucchini', 'cauliflower rice', 'garlic', 'lemon'], 'Monday dinner. Make enough for Tuesday lunch.', '6', '10 min', '20 min'],
    ['Turkey Taco Lettuce Bowls', 'dinner', ['lean ground turkey', 'lettuce', 'cherry tomatoes', 'avocado', 'Greek yogurt', 'lime', 'black beans', 'salsa or pico'], 'Tuesday dinner. Make enough for Wednesday lunch.', '6', '10 min', '15 min'],
    ['Bunless Burger Salad', 'dinner', ['lean ground beef', 'greens', 'pickles', 'cherry tomatoes', 'avocado', 'Greek yogurt'], 'Wednesday dinner. Make enough for Thursday lunch.', '6', '10 min', '15 min'],
    ['Chicken Fajita Cauliflower Bowls', 'dinner', ['chicken breast', 'bell peppers', 'onion', 'cauliflower rice', 'avocado', 'salsa', 'black beans'], 'Thursday dinner. Make enough for Friday lunch.', '6', '10 min', '20 min'],
    ['Sesame Beef and Broccoli Bowls', 'dinner', ['beef strips, sirloin, or flank steak', 'broccoli', 'cauliflower rice', 'low-sodium soy sauce or coconut aminos', 'sesame oil', 'fresh ginger', 'green onions'], 'Friday dinner. Make enough for Saturday lunch.', '6', '10 min', '20 min'],
    ['Greek Turkey Meatball Bowls', 'dinner', ['lean ground turkey', 'Greek yogurt', 'cucumber', 'cherry tomatoes', 'cauliflower rice', 'feta', 'lemon'], 'Saturday dinner. Make enough for Sunday lunch.', '6', '15 min', '20 min'],
    ['Lemon Roasted Salmon or Chicken', 'dinner', ['salmon or chicken', 'broccoli', 'zucchini', 'lemon', 'olive oil'], 'Sunday dinner.', '3', '10 min', '20 min'],

    ['Hard-Boiled Eggs', 'snack', ['eggs'], 'Snack pool.', '1-2', '5 min', '12 min'],
    ['Cottage Cheese with Cucumber', 'snack', ['cottage cheese', 'cucumber'], 'Snack pool.', '1-2', '5 min', '0 min'],
    ['Greek Yogurt with Berries and Chia', 'snack', ['Greek yogurt', 'blueberries', 'chia seeds'], 'Snack pool.', '1-2', '5 min', '0 min'],
    ['Apple with Cheddar', 'snack', ['apple', 'cheddar'], 'Snack pool.', '1-2', '5 min', '0 min'],
    ['Turkey and Cheese Roll-Ups', 'snack', ['turkey lunch meat', 'cheese', 'cucumber'], 'Snack pool.', '1-2', '5 min', '0 min'],
    ['Celery with Peanut Butter', 'snack', ['celery', 'peanut butter'], 'Snack pool.', '1-2', '5 min', '0 min'],
    ['Edamame with Lime', 'snack', ['edamame', 'lime'], 'Snack pool.', '1-2', '5 min', '5 min'],
    ['Hummus Cucumber Bites', 'snack', ['cucumber', 'hummus'], 'Snack pool.', '1-2', '5 min', '0 min'],
    ['Caprese Cucumber Bites', 'snack', ['cucumber', 'cherry tomatoes', 'mozzarella pearls'], 'Snack pool.', '1-2', '5 min', '0 min'],
    ['Deviled Egg Cups with Greek Yogurt', 'snack', ['hard-boiled eggs', 'Greek yogurt', 'mustard'], 'Snack pool.', '1-2', '10 min', '0 min'],
    ['Smoked Turkey Pickle Roll-Ups', 'snack', ['turkey lunch meat', 'pickles'], 'Snack pool.', '1-2', '5 min', '0 min'],
    ['Ricotta Cocoa Bowl with Walnuts', 'snack', ['ricotta', 'cocoa powder', 'walnuts'], 'Snack pool.', '1-2', '5 min', '0 min'],
    ['Roasted Chickpea Crunch', 'snack', ['chickpeas', 'olive oil'], 'Snack pool.', '1-2', '5 min', '20 min'],
    ['Mini Tuna Cucumber Boats', 'snack', ['tuna packets or cans', 'cucumber', 'Greek yogurt'], 'Snack pool.', '1-2', '10 min', '0 min']
  ];

  const MENU = {
    breakfast: [
      ['Greek Yogurt Blueberry Bowl', 'Monday, May 18'],
      ['Garden Egg Scramble', 'Tuesday, May 19'],
      ['Tomato and Greens Egg Bites', 'Wednesday and Thursday'],
      ['Cottage Cheese Berry Bowl', 'Friday, May 22'],
      ['Protein Pancakes with Greek Yogurt and Berries', 'Saturday, May 23'],
      ['Veggie Omelet with Avocado', 'Sunday, May 24']
    ],
    lunch: [
      ['Leftover Beef Chuck Bowls', 'Monday, May 18 — leftovers from last week'],
      ['Shrimp-Chicken Vegetable Bowls', 'Tuesday, May 19 — leftovers from Monday dinner'],
      ['Turkey Taco Salad', 'Wednesday, May 20 — leftovers from Tuesday dinner'],
      ['Burger Lettuce Cups', 'Thursday, May 21 — leftovers from Wednesday dinner'],
      ['Fajita Chicken Salad', 'Friday, May 22 — leftovers from Thursday dinner'],
      ['Sesame Beef Broccoli Bowls with Cucumber Salad', 'Saturday, May 23 — leftovers from Friday dinner'],
      ['Turkey Meatball Salad Bowls', 'Sunday, May 24 — leftovers from Saturday dinner']
    ],
    snack: [
      ['Hard-Boiled Eggs', 'Snack pool'],
      ['Cottage Cheese with Cucumber', 'Snack pool'],
      ['Greek Yogurt with Berries and Chia', 'Snack pool'],
      ['Apple with Cheddar', 'Snack pool'],
      ['Turkey and Cheese Roll-Ups', 'Snack pool'],
      ['Celery with Peanut Butter', 'Snack pool'],
      ['Edamame with Lime', 'Snack pool'],
      ['Hummus Cucumber Bites', 'Snack pool'],
      ['Caprese Cucumber Bites', 'Snack pool'],
      ['Deviled Egg Cups with Greek Yogurt', 'Snack pool'],
      ['Smoked Turkey Pickle Roll-Ups', 'Snack pool'],
      ['Ricotta Cocoa Bowl with Walnuts', 'Snack pool'],
      ['Roasted Chickpea Crunch', 'Snack pool'],
      ['Mini Tuna Cucumber Boats', 'Snack pool']
    ],
    dinner: [
      ['Lemon Garlic Shrimp and Chicken Bowls', 'Monday, May 18 — make enough for Tuesday lunch'],
      ['Turkey Taco Lettuce Bowls', 'Tuesday, May 19 — make enough for Wednesday lunch'],
      ['Bunless Burger Salad', 'Wednesday, May 20 — make enough for Thursday lunch'],
      ['Chicken Fajita Cauliflower Bowls', 'Thursday, May 21 — make enough for Friday lunch'],
      ['Sesame Beef and Broccoli Bowls', 'Friday, May 22 — make enough for Saturday lunch'],
      ['Greek Turkey Meatball Bowls', 'Saturday, May 23 — make enough for Sunday lunch'],
      ['Lemon Roasted Salmon or Chicken', 'Sunday, May 24']
    ]
  };

  const GROCERY = [
    ['Eggs', '2', 'dozen', 'Dairy'], ['Plain Greek yogurt', '2', 'large tubs', 'Dairy'], ['Cottage cheese', '1', 'large tub', 'Dairy'],
    ['Lean ground turkey', '4', 'lb', 'Meat & Seafood'], ['Lean ground beef', '2', 'lb', 'Meat & Seafood'], ['Beef strips, sirloin, or flank steak', '2', 'lb', 'Meat & Seafood'], ['Chicken breast', '4-5', 'lb', 'Meat & Seafood'], ['Shrimp', '1.5-2', 'lb', 'Meat & Seafood'], ['Salmon or extra chicken', '1.5-2', 'lb', 'Meat & Seafood'], ['Turkey lunch meat', '1', 'pack', 'Meat & Seafood'],
    ['Cheddar', '1', 'block or pack', 'Dairy'], ['Mozzarella pearls', '1', 'container', 'Dairy'], ['Ricotta', '1', 'container', 'Dairy'], ['Feta', '1', 'container', 'Dairy'], ['Tuna packets or cans', '3', '', 'Pantry'],
    ['Salad greens or chopped salad kits', '5-6', 'bags', 'Produce'], ['Lettuce for cups', '2', 'heads', 'Produce'], ['Cucumbers', '6-7', '', 'Produce'], ['Cherry tomatoes', '2', 'large packs', 'Produce'], ['Broccoli', '4', 'heads or 3 large bags', 'Produce'], ['Zucchini', '6', '', 'Produce'], ['Bell peppers', '6', '', 'Produce'], ['Onions', '3', '', 'Produce'], ['Avocados', '6', '', 'Produce'], ['Blueberries', '2', 'pints', 'Produce'], ['Apples', '6', '', 'Produce'], ['Lemons', '4', '', 'Produce'], ['Limes', '4', '', 'Produce'], ['Celery', '1', 'bunch', 'Produce'], ['Green onions', '1', 'bunch', 'Produce'], ['Fresh ginger', '1', 'piece', 'Produce'], ['Garlic', '1', 'bulb', 'Produce'],
    ['Cauliflower rice', '5-6', 'bags', 'Frozen'], ['Black beans', '2', 'cans', 'Pantry'], ['Salsa or pico', '2', 'containers', 'Pantry'], ['Chia seeds', '1', 'bag', 'Pantry'], ['Walnuts or almonds', '1', 'bag', 'Pantry'], ['Peanut butter', '1', 'jar', 'Pantry'], ['Hummus', '1', 'container', 'Deli'], ['Edamame', '1', 'bag', 'Frozen'], ['Pickles', '1', 'jar', 'Pantry'], ['Chickpeas', '1', 'can', 'Pantry'], ['Low-sodium soy sauce or coconut aminos', '1', 'bottle', 'Pantry'], ['Sesame oil', '1', 'bottle', 'Pantry'], ['Olive oil', '1', 'bottle', 'Pantry'], ['Cocoa powder', '1', 'container', 'Pantry'], ['Everything seasoning', '1', 'container', 'Pantry']
  ];

  function onRecipesPage() { return location.pathname.startsWith('/recipes'); }
  function bootstrapRecipes() { const el = document.getElementById('recipes-bootstrap'); if (!el) return []; try { return JSON.parse(el.textContent || '{}').recipes || []; } catch (_) { return []; } }
  function alpineState() { if (!window.Alpine) return null; const root = document.querySelector('[x-data="recipesPage()"]'); if (!root) return null; try { return window.Alpine.$data(root); } catch (_) { return null; } }

  function recipeId(name) { return 'may18-' + String(name || '').toLowerCase().replace(/&/g, 'and').replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '').slice(0, 54); }

  function recipePayload(row) {
    return {
      id: recipeId(row[0]),
      name: row[0], source: 'Life Manager', servings: row[4] || '', prep_time: row[5] || '', cook_time: row[6] || '',
      tags: ['weekly menu', 'may 18', row[1], 'diabetes prevention'],
      ingredients: row[2].map((name) => ({ name, qty: '', unit: '' })),
      instructions: ['Prepare and serve as listed on the approved weekly menu.'],
      notes: row[3] || ''
    };
  }

  async function ensureRecipes() {
    const state = alpineState();
    const recipes = [...bootstrapRecipes(), ...((state && state.recipes) || [])];
    const byName = new Map(recipes.filter((r) => r && r.name).map((r) => [r.name.trim().toLowerCase(), r]));
    const created = [];
    for (const row of STARTERS) {
      const key = row[0].toLowerCase();
      if (byName.has(key)) continue;
      try {
        const res = await fetch('/api/recipes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(recipePayload(row)) });
        const data = await res.json();
        if (data && data.ok && data.recipe) { byName.set(key, data.recipe); created.push(data.recipe); }
      } catch (_) {}
    }
    if (state && created.length) state.recipes = (state.recipes || []).concat(created);
    return byName;
  }

  async function currentMenu() {
    try {
      const res = await fetch('/api/recipes/menu?week=' + encodeURIComponent(WEEK_KEY));
      const data = await res.json();
      if (data && data.ok && data.menu) return data.menu;
    } catch (_) {}
    return { breakfast: [], lunch: [], snack: [], dinner: [] };
  }

  function hasEntry(entries, name) {
    const key = String(name || '').trim().toLowerCase();
    return (entries || []).some((e) => String(e.name || '').trim().toLowerCase() === key);
  }

  async function fillMenu(byName) {
    let menu = await currentMenu();
    for (const slot of SLOTS) {
      for (const [name, notes] of MENU[slot]) {
        const rec = byName.get(name.toLowerCase());
        if (hasEntry(menu[slot] || [], name)) continue;
        try {
          const res = await fetch('/api/recipes/menu/' + slot, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ week_key: WEEK_KEY, recipe_id: rec ? rec.id : null, name, notes }) });
          const data = await res.json();
          if (data && data.ok && data.menu) menu = data.menu;
        } catch (_) {}
      }
    }
  }

  async function ensureGrocery() {
    let existing = [];
    try {
      const res = await fetch('/api/recipes/grocery');
      const data = await res.json();
      existing = data.items || [];
    } catch (_) {}
    const names = new Set(existing.map((it) => String(it.name || '').trim().toLowerCase()));
    const state = alpineState();
    const created = [];
    for (const [name, qty, unit, category] of GROCERY) {
      const key = String(name || '').trim().toLowerCase();
      if (!key || names.has(key)) continue;
      try {
        const res = await fetch('/api/recipes/grocery', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, qty, unit, category }) });
        const data = await res.json();
        if (data && data.ok && data.item) { names.add(key); created.push(data.item); }
      } catch (_) {}
    }
    if (state && created.length) state.grocery = (state.grocery || []).concat(created);
  }

  async function maybeLoadWeekInUi() {
    const state = alpineState();
    if (!state) return;
    const params = new URLSearchParams(location.search);
    if (params.get('menu_week_start') !== WEEK_START && state.currentWeek !== WEEK_KEY) return;
    const menu = await currentMenu();
    state.menuSlots = SLOTS;
    state.menuTargets = Object.assign({}, state.menuTargets || {}, { snack: { min: 4, max: 10 } });
    state.addMenuRecipe = { breakfast: '', lunch: '', snack: '', dinner: '' };
    state.addMenuText = { breakfast: '', lunch: '', snack: '', dinner: '' };
    state.menu = { week_key: WEEK_KEY, breakfast: menu.breakfast || [], lunch: menu.lunch || [], snack: menu.snack || [], dinner: menu.dinner || [] };
    state.currentWeek = WEEK_KEY;
  }

  async function run() {
    if (!onRecipesPage()) return;
    const state = alpineState();
    if (state) {
      state.menuSlots = SLOTS;
      state.menuTargets = Object.assign({}, state.menuTargets || {}, { snack: { min: 4, max: 10 } });
      state.addMenuRecipe = Object.assign({ breakfast: '', lunch: '', snack: '', dinner: '' }, state.addMenuRecipe || {});
      state.addMenuText = Object.assign({ breakfast: '', lunch: '', snack: '', dinner: '' }, state.addMenuText || {});
      if (state.menu) state.menu.snack = state.menu.snack || [];
    }
    const byName = await ensureRecipes();
    await fillMenu(byName);
    await ensureGrocery();
    await maybeLoadWeekInUi();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(run, 700));
  else setTimeout(run, 700);
})();
