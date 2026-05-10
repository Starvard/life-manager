(function () {
  const WEEK_KEY = '2026-W20';
  const WEEK_START = '2026-05-11';
  const SLOTS = ['breakfast', 'lunch', 'snack', 'dinner'];

  const STARTERS = [
    ['Turkey Burgers', 'dinner', ['ground turkey', 'cheddar cheese', 'butter lettuce', 'tomato', 'Greek yogurt', 'chipotle in adobo', 'zucchini', 'red pepper']],
    ['Chicken Fried Rice', 'dinner', ['chicken', 'eggs', 'cauliflower rice', 'cooked rice', 'broccoli', 'garlic', 'lime']],
    ['Turkey Lettuce Cups', 'lunch', ['ground turkey', 'butter lettuce', 'avocado', 'pico', 'pickled onion', 'lime']],
    ['Shrimp Taco Salad', 'lunch', ['shrimp', 'cabbage slaw', 'pico', 'avocado', 'Greek yogurt', 'lime']],
    ['Chuck Roast Bowls', 'dinner', ['chuck roast', 'beef stock', 'salsa', 'cauliflower rice', 'pico', 'avocado', 'sour cream']],
    ['Lemon Garlic Shrimp', 'dinner', ['shrimp', 'zucchini', 'red pepper', 'broccoli', 'garlic', 'lemon', 'basil']],
    ['Chicken Salad Lettuce Cups', 'lunch', ['cooked chicken', 'Greek yogurt', 'celery', 'apple', 'butter lettuce', 'lemon']],
    ['Protein Waffles', 'breakfast', ['waffle mix or protein waffle batter', 'Greek yogurt', 'berries', 'peanut butter']],
    ['Cottage Cheese', 'snack', ['cottage cheese', 'cucumber', 'lemon']],
    ['Apple & Brie', 'snack', ['apples', 'brie', 'whole-grain crackers']],
    ['Hard-Boiled Eggs', 'snack', ['eggs']],
    ['Celery & Peanut Butter', 'snack', ['celery', 'peanut butter', 'cinnamon']],
    ['Cheese & Cucumber Box', 'snack', ['snacking cheese', 'cucumber', 'pickles', 'whole-grain crackers']],
    ['Greek Yogurt Cup', 'snack', ['Greek yogurt', 'berries', 'chia seeds']],
    ['Apple Cheddar Bites', 'snack', ['apples', 'cheddar cheese', 'almonds or whole-grain crackers']],
    ['Turkey Roll-Ups', 'snack', ['deli turkey', 'cheese', 'pickles', 'cucumber']],
    ['Cottage Cheese Cup', 'snack', ['cottage cheese', 'tomatoes', 'cucumber', 'everything seasoning']],
    ['Peanut Butter Yogurt Dip', 'snack', ['Greek yogurt', 'peanut butter', 'apples']],
    ['Edamame', 'snack', ['edamame', 'lime']],
    ['Frozen Yogurt Berry Bark', 'snack', ['Greek yogurt', 'berries', 'chia seeds', 'toasted nuts']],
    ['Cucumber Brie Bites', 'snack', ['cucumber', 'brie', 'lemon']],
    ['Cheese & Crackers', 'snack', ['snacking cheese', 'whole-grain crackers', 'pickles', 'cucumber']]
  ];

  const MENU = {
    breakfast: [
      ['Egg Bites', 'Berries, greens, cheddar'],
      ['Greek Yogurt Bowl', 'Berries, chia, toasted nuts'],
      ['Protein Waffles', 'Greek yogurt, berries, peanut butter'],
      ['Eat Out — Hilton Head Breakfast', 'Wednesday, Thursday, Friday'],
      ['Brunch Plate', 'Eggs, berries, avocado, microgreens']
    ],
    lunch: [
      ['Turkey Lettuce Cups', 'Avocado, pico, pickled onion, lime'],
      ['Turkey Burger Salad', 'Greens, avocado, cucumber, tomato'],
      ['Eat Out — Hilton Head Lunch', 'Wednesday, Thursday, Friday'],
      ['Shrimp Taco Salad', 'Cabbage, pico, avocado, chipotle lime crema'],
      ['Chicken Salad Lettuce Cups', 'Celery, Greek yogurt, herbs, apple']
    ],
    snack: [
      ['Cottage Cheese', 'Cucumber, cracked pepper, lemon'],
      ['Apple & Brie', 'Whole-grain crackers'],
      ['Hard-Boiled Eggs', 'Kosher salt, cracked pepper'],
      ['Celery & Peanut Butter', 'Cinnamon'],
      ['Cheese & Cucumber Box', 'Pickles, crackers'],
      ['Greek Yogurt Cup', 'Berries, chia'],
      ['Apple Cheddar Bites', 'Almonds or crackers'],
      ['Turkey Roll-Ups', 'Cheese, pickle, cucumber'],
      ['Cottage Cheese Cup', 'Tomato, cucumber, everything seasoning'],
      ['Peanut Butter Yogurt Dip', 'Apple slices'],
      ['Edamame', 'Lime, sea salt'],
      ['Frozen Yogurt Berry Bark', 'Chia, toasted nuts'],
      ['Cucumber Brie Bites', 'Lemon, cracked pepper'],
      ['Cheese & Crackers', 'Pickles, cucumber']
    ],
    dinner: [
      ['Turkey Burgers', 'Butter lettuce, cheddar, tomato, chipotle yogurt sauce · zucchini & peppers'],
      ['Chicken Fried Rice', 'Chicken, egg, cauliflower rice, garlic, broccoli, lime'],
      ['Eat Out — Hilton Head Dinner', 'Wednesday, Thursday, Friday'],
      ['Eat Out or Easy Home Plate', 'Chicken, greens, avocado, cucumber'],
      ['Chuck Roast Bowls', 'Greens, cauliflower rice, pico, avocado, sour cream'],
      ['Lemon Garlic Shrimp', 'Zucchini, red pepper, basil, broccoli']
    ]
  };

  function onRecipesPage() { return location.pathname.startsWith('/recipes'); }
  function bootstrapRecipes() { const el = document.getElementById('recipes-bootstrap'); if (!el) return []; try { return JSON.parse(el.textContent || '{}').recipes || []; } catch (_) { return []; } }
  function alpineState() { if (!window.Alpine) return null; const root = document.querySelector('[x-data="recipesPage()"]'); if (!root) return null; try { return window.Alpine.$data(root); } catch (_) { return null; } }

  function recipePayload(row) {
    return {
      name: row[0], source: 'Life Manager', tags: ['weekly menu', row[1]],
      ingredients: row[2].map((name) => ({ name, qty: '', unit: '' })),
      instructions: ['Prepare and serve as listed on the weekly menu.'],
      notes: 'Starter recipe from the May 11 weekly menu.'
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

  function hasLinkedEntry(entries, name) {
    const key = String(name || '').trim().toLowerCase();
    return (entries || []).some((e) => String(e.name || '').trim().toLowerCase() === key && e.recipe_id);
  }

  function hasAnyEntry(entries, name) {
    const key = String(name || '').trim().toLowerCase();
    return (entries || []).some((e) => String(e.name || '').trim().toLowerCase() === key);
  }

  function dedupeForUi(entries) {
    const linkedNames = new Set((entries || []).filter((e) => e.recipe_id).map((e) => String(e.name || '').trim().toLowerCase()));
    const seen = new Set();
    return (entries || []).filter((e) => {
      const key = String(e.name || '').trim().toLowerCase();
      const sig = key + '::' + (e.recipe_id || 'text');
      if (!key) return false;
      if (!e.recipe_id && linkedNames.has(key)) return false;
      if (seen.has(sig)) return false;
      seen.add(sig);
      return true;
    });
  }

  async function fillMenu(byName) {
    let menu = await currentMenu();
    for (const slot of SLOTS) {
      for (const [name, notes] of MENU[slot]) {
        const rec = byName.get(name.toLowerCase());
        const entries = menu[slot] || [];
        if (rec ? hasLinkedEntry(entries, name) : hasAnyEntry(entries, name)) continue;
        try {
          const res = await fetch('/api/recipes/menu/' + slot, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ week_key: WEEK_KEY, recipe_id: rec ? rec.id : null, name, notes }) });
          const data = await res.json();
          if (data && data.ok && data.menu) menu = data.menu;
        } catch (_) {}
      }
    }
  }

  async function maybeLoadWeekInUi() {
    const state = alpineState();
    const params = new URLSearchParams(location.search);
    if (!state || params.get('menu_week_start') !== WEEK_START) return;
    const menu = await currentMenu();
    state.menuSlots = SLOTS;
    state.menuTargets = Object.assign({}, state.menuTargets || {}, { snack: { min: 4, max: 10 } });
    state.addMenuRecipe = Object.assign({ snack: '' }, state.addMenuRecipe || {});
    state.addMenuText = Object.assign({ snack: '' }, state.addMenuText || {});
    state.menu = { week_key: WEEK_KEY, breakfast: dedupeForUi(menu.breakfast || []), lunch: dedupeForUi(menu.lunch || []), snack: dedupeForUi(menu.snack || []), dinner: dedupeForUi(menu.dinner || []) };
    state.currentWeek = WEEK_KEY;
  }

  async function run() {
    if (!onRecipesPage()) return;
    const state = alpineState();
    if (state) {
      state.menuSlots = SLOTS;
      state.menuTargets = Object.assign({}, state.menuTargets || {}, { snack: { min: 4, max: 10 } });
      state.addMenuRecipe = Object.assign({ snack: '' }, state.addMenuRecipe || {});
      state.addMenuText = Object.assign({ snack: '' }, state.addMenuText || {});
      if (state.menu) state.menu.snack = state.menu.snack || [];
    }
    const byName = await ensureRecipes();
    await fillMenu(byName);
    await maybeLoadWeekInUi();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(run, 600));
  else setTimeout(run, 600);
})();
