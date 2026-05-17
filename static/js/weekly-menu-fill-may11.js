(function () {
  // Approved menu: week of May 18, 2026. Kept in this filename because base.html already loads it.
  const WEEK_KEY = '2026-W21';
  const WEEK_START = '2026-05-18';
  const SLOTS = ['breakfast', 'lunch', 'snack', 'dinner'];

  const RECIPES = {
    breakfast: [
      ['Greek Yogurt Blueberry Bowl', ['plain Greek yogurt', 'blueberries', 'chia seeds', 'toasted walnuts', 'cinnamon']],
      ['Garden Egg Scramble', ['eggs', 'greens', 'cherry tomatoes', 'avocado']],
      ['Tomato and Greens Egg Bites', ['eggs', 'greens', 'cherry tomatoes', 'cheddar or feta']],
      ['Cottage Cheese Berry Bowl', ['cottage cheese', 'blueberries', 'chia seeds', 'walnuts']],
      ['Protein Pancakes with Greek Yogurt and Berries', ['protein pancake mix', 'Greek yogurt', 'blueberries', 'walnuts']],
      ['Veggie Omelet with Avocado', ['eggs', 'greens', 'cherry tomatoes', 'avocado']]
    ],
    lunch: [
      ['Leftover Beef Chuck Bowls', ['leftover beef chuck', 'greens', 'avocado', 'lime crema']],
      ['Shrimp-Chicken Vegetable Bowls', ['leftover shrimp and chicken', 'greens', 'cauliflower rice']],
      ['Turkey Taco Salad', ['leftover turkey taco meat', 'greens', 'avocado', 'salsa']],
      ['Burger Lettuce Cups', ['leftover burger patties', 'lettuce', 'cucumber', 'pickles']],
      ['Fajita Chicken Salad', ['leftover fajita chicken', 'greens', 'cucumber', 'avocado']],
      ['Sesame Beef Broccoli Bowls with Cucumber Salad', ['leftover sesame beef and broccoli', 'cucumber', 'cauliflower rice']],
      ['Turkey Meatball Salad Bowls', ['leftover turkey meatballs', 'greens', 'cucumber tomato salad']]
    ],
    dinner: [
      ['Lemon Garlic Shrimp and Chicken Bowls', ['shrimp', 'chicken breast', 'broccoli', 'zucchini', 'cauliflower rice', 'garlic', 'lemon']],
      ['Turkey Taco Lettuce Bowls', ['lean ground turkey', 'lettuce', 'cherry tomatoes', 'avocado', 'Greek yogurt', 'lime', 'black beans']],
      ['Bunless Burger Salad', ['lean ground beef', 'greens', 'pickles', 'cherry tomatoes', 'avocado', 'Greek yogurt']],
      ['Chicken Fajita Cauliflower Bowls', ['chicken breast', 'bell peppers', 'onion', 'cauliflower rice', 'avocado', 'salsa', 'black beans']],
      ['Sesame Beef and Broccoli Bowls', ['beef strips', 'broccoli', 'cauliflower rice', 'soy sauce or coconut aminos', 'sesame oil', 'fresh ginger', 'green onions']],
      ['Greek Turkey Meatball Bowls', ['lean ground turkey', 'Greek yogurt', 'cucumber', 'cherry tomatoes', 'cauliflower rice', 'feta', 'lemon']],
      ['Lemon Roasted Salmon or Chicken', ['salmon or chicken', 'broccoli', 'zucchini', 'lemon', 'olive oil']]
    ],
    snack: [
      ['Hard-Boiled Eggs', ['eggs']],
      ['Cottage Cheese with Cucumber', ['cottage cheese', 'cucumber']],
      ['Greek Yogurt with Berries and Chia', ['Greek yogurt', 'blueberries', 'chia seeds']],
      ['Apple with Cheddar', ['apples', 'cheddar']],
      ['Turkey and Cheese Roll-Ups', ['turkey lunch meat', 'cheese', 'cucumber']],
      ['Celery with Peanut Butter', ['celery', 'peanut butter']],
      ['Edamame with Lime', ['edamame', 'lime']],
      ['Hummus Cucumber Bites', ['cucumber', 'hummus']],
      ['Caprese Cucumber Bites', ['cucumber', 'cherry tomatoes', 'mozzarella pearls']],
      ['Deviled Egg Cups with Greek Yogurt', ['hard-boiled eggs', 'Greek yogurt', 'mustard']],
      ['Smoked Turkey Pickle Roll-Ups', ['turkey lunch meat', 'pickles']],
      ['Ricotta Cocoa Bowl with Walnuts', ['ricotta', 'cocoa powder', 'walnuts']],
      ['Roasted Chickpea Crunch', ['chickpeas', 'olive oil']],
      ['Mini Tuna Cucumber Boats', ['tuna packets or cans', 'cucumber', 'Greek yogurt']]
    ]
  };

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
      ['Leftover Beef Chuck Bowls', 'Monday — leftovers from last week'],
      ['Shrimp-Chicken Vegetable Bowls', 'Tuesday — leftovers from Monday dinner'],
      ['Turkey Taco Salad', 'Wednesday — leftovers from Tuesday dinner'],
      ['Burger Lettuce Cups', 'Thursday — leftovers from Wednesday dinner'],
      ['Fajita Chicken Salad', 'Friday — leftovers from Thursday dinner'],
      ['Sesame Beef Broccoli Bowls with Cucumber Salad', 'Saturday — leftovers from Friday dinner'],
      ['Turkey Meatball Salad Bowls', 'Sunday — leftovers from Saturday dinner']
    ],
    dinner: [
      ['Lemon Garlic Shrimp and Chicken Bowls', 'Monday — make enough for Tuesday lunch'],
      ['Turkey Taco Lettuce Bowls', 'Tuesday — make enough for Wednesday lunch'],
      ['Bunless Burger Salad', 'Wednesday — make enough for Thursday lunch'],
      ['Chicken Fajita Cauliflower Bowls', 'Thursday — make enough for Friday lunch'],
      ['Sesame Beef and Broccoli Bowls', 'Friday — make enough for Saturday lunch'],
      ['Greek Turkey Meatball Bowls', 'Saturday — make enough for Sunday lunch'],
      ['Lemon Roasted Salmon or Chicken', 'Sunday']
    ],
    snack: RECIPES.snack.map((r) => [r[0], 'Snack pool'])
  };

  const GROCERY = [
    ['Eggs', '2', 'dozen', 'Dairy'], ['Plain Greek yogurt', '2', 'large tubs', 'Dairy'], ['Cottage cheese', '1', 'large tub', 'Dairy'],
    ['Lean ground turkey', '4', 'lb', 'Meat & Seafood'], ['Lean ground beef', '2', 'lb', 'Meat & Seafood'], ['Beef strips, sirloin, or flank steak', '2', 'lb', 'Meat & Seafood'], ['Chicken breast', '4-5', 'lb', 'Meat & Seafood'], ['Shrimp', '1.5-2', 'lb', 'Meat & Seafood'], ['Salmon or extra chicken', '1.5-2', 'lb', 'Meat & Seafood'], ['Turkey lunch meat', '1', 'pack', 'Meat & Seafood'],
    ['Cheddar', '1', 'pack', 'Dairy'], ['Mozzarella pearls', '1', 'container', 'Dairy'], ['Ricotta', '1', 'container', 'Dairy'], ['Feta', '1', 'container', 'Dairy'], ['Tuna packets or cans', '3', '', 'Pantry'],
    ['Salad greens or chopped salad kits', '5-6', 'bags', 'Produce'], ['Lettuce for cups', '2', 'heads', 'Produce'], ['Cucumbers', '6-7', '', 'Produce'], ['Cherry tomatoes', '2', 'large packs', 'Produce'], ['Broccoli', '4', 'heads or 3 large bags', 'Produce'], ['Zucchini', '6', '', 'Produce'], ['Bell peppers', '6', '', 'Produce'], ['Onions', '3', '', 'Produce'], ['Avocados', '6', '', 'Produce'], ['Blueberries', '2', 'pints', 'Produce'], ['Apples', '6', '', 'Produce'], ['Lemons', '4', '', 'Produce'], ['Limes', '4', '', 'Produce'], ['Celery', '1', 'bunch', 'Produce'], ['Green onions', '1', 'bunch', 'Produce'], ['Fresh ginger', '1', 'piece', 'Produce'], ['Garlic', '1', 'bulb', 'Produce'],
    ['Cauliflower rice', '5-6', 'bags', 'Frozen'], ['Black beans', '2', 'cans', 'Pantry'], ['Salsa or pico', '2', 'containers', 'Pantry'], ['Chia seeds', '1', 'bag', 'Pantry'], ['Walnuts or almonds', '1', 'bag', 'Pantry'], ['Peanut butter', '1', 'jar', 'Pantry'], ['Hummus', '1', 'container', 'Other'], ['Edamame', '1', 'bag', 'Frozen'], ['Pickles', '1', 'jar', 'Pantry'], ['Chickpeas', '1', 'can', 'Pantry'], ['Low-sodium soy sauce or coconut aminos', '1', 'bottle', 'Pantry'], ['Sesame oil', '1', 'bottle', 'Pantry'], ['Olive oil', '1', 'bottle', 'Pantry'], ['Cocoa powder', '1', 'container', 'Pantry'], ['Everything seasoning', '1', 'container', 'Pantry']
  ];

  function onRecipesPage() { return location.pathname.startsWith('/recipes'); }
  function state() { if (!window.Alpine) return null; const root = document.querySelector('[x-data="recipesPage()"]'); if (!root) return null; try { return window.Alpine.$data(root); } catch (_) { return null; } }
  function currentRecipes() { const el = document.getElementById('recipes-bootstrap'); try { return JSON.parse(el.textContent || '{}').recipes || []; } catch (_) { return []; } }
  function allRows() { return [].concat(RECIPES.breakfast, RECIPES.lunch, RECIPES.dinner, RECIPES.snack); }

  async function ensureRecipes() {
    const s = state();
    const recipes = currentRecipes().concat((s && s.recipes) || []);
    const byName = new Map(recipes.filter((r) => r.name).map((r) => [r.name.trim().toLowerCase(), r]));
    const created = [];
    for (const row of allRows()) {
      const name = row[0];
      const key = name.toLowerCase();
      if (byName.has(key)) continue;
      const payload = { name, source: 'Life Manager', servings: '3+', tags: ['weekly menu', 'may 18'], ingredients: row[1].map((x) => ({ name: x, qty: '', unit: '' })), instructions: ['Prepare and serve as listed on the approved weekly menu.'], notes: 'Approved menu for week of May 18.' };
      try {
        const res = await fetch('/api/recipes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const data = await res.json();
        if (data && data.ok && data.recipe) { byName.set(key, data.recipe); created.push(data.recipe); }
      } catch (_) {}
    }
    if (s && created.length) s.recipes = (s.recipes || []).concat(created);
    return byName;
  }

  async function getMenu() {
    try { const res = await fetch('/api/recipes/menu?week=' + encodeURIComponent(WEEK_KEY)); const data = await res.json(); if (data && data.ok && data.menu) return data.menu; } catch (_) {}
    return { breakfast: [], lunch: [], snack: [], dinner: [] };
  }

  function has(entries, name) { const key = String(name || '').trim().toLowerCase(); return (entries || []).some((e) => String(e.name || '').trim().toLowerCase() === key); }

  async function fillMenu(byName) {
    let menu = await getMenu();
    for (const slot of SLOTS) {
      for (const row of MENU[slot]) {
        const name = row[0], notes = row[1], rec = byName.get(name.toLowerCase());
        if (has(menu[slot] || [], name)) continue;
        try {
          const res = await fetch('/api/recipes/menu/' + slot, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ week_key: WEEK_KEY, recipe_id: rec ? rec.id : null, name, notes }) });
          const data = await res.json();
          if (data && data.ok && data.menu) menu = data.menu;
        } catch (_) {}
      }
    }
  }

  async function fillGrocery() {
    let existing = [];
    try { const res = await fetch('/api/recipes/grocery'); const data = await res.json(); existing = data.items || []; } catch (_) {}
    const names = new Set(existing.map((it) => String(it.name || '').trim().toLowerCase()));
    const s = state(), created = [];
    for (const item of GROCERY) {
      const key = item[0].toLowerCase();
      if (names.has(key)) continue;
      try {
        const res = await fetch('/api/recipes/grocery', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: item[0], qty: item[1], unit: item[2], category: item[3] }) });
        const data = await res.json();
        if (data && data.ok && data.item) { names.add(key); created.push(data.item); }
      } catch (_) {}
    }
    if (s && created.length) s.grocery = (s.grocery || []).concat(created);
  }

  async function loadWeekInUi() {
    const s = state();
    if (!s) return;
    const params = new URLSearchParams(location.search);
    if (params.get('menu_week_start') !== WEEK_START && s.currentWeek !== WEEK_KEY) return;
    const menu = await getMenu();
    s.menuSlots = SLOTS;
    s.menuTargets = Object.assign({}, s.menuTargets || {}, { snack: { min: 4, max: 10 } });
    s.addMenuRecipe = { breakfast: '', lunch: '', snack: '', dinner: '' };
    s.addMenuText = { breakfast: '', lunch: '', snack: '', dinner: '' };
    s.menu = { week_key: WEEK_KEY, breakfast: menu.breakfast || [], lunch: menu.lunch || [], snack: menu.snack || [], dinner: menu.dinner || [] };
    s.currentWeek = WEEK_KEY;
  }

  async function run() {
    if (!onRecipesPage()) return;
    const s = state();
    if (s) { s.menuSlots = SLOTS; s.addMenuRecipe = Object.assign({ snack: '' }, s.addMenuRecipe || {}); s.addMenuText = Object.assign({ snack: '' }, s.addMenuText || {}); if (s.menu) s.menu.snack = s.menu.snack || []; }
    const byName = await ensureRecipes();
    await fillMenu(byName);
    await fillGrocery();
    await loadWeekInUi();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(run, 700));
  else setTimeout(run, 700);
})();
