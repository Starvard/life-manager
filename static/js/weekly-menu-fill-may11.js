(function () {
  const WEEK_KEY = '2026-W20';
  const WEEK_START = '2026-05-11';

  const STARTERS = [
    { name: 'Turkey Burgers', tags: ['weekly menu', 'dinner'], ingredients: ['ground turkey', 'cheddar cheese', 'butter lettuce', 'tomato', 'Greek yogurt', 'chipotle in adobo', 'zucchini', 'red pepper'], instructions: ['Season and form turkey patties.', 'Cook until done.', 'Serve with lettuce, cheddar, tomato, chipotle yogurt sauce, zucchini, and peppers.'] },
    { name: 'Chicken Fried Rice', tags: ['weekly menu', 'dinner'], ingredients: ['chicken', 'eggs', 'cauliflower rice', 'cooked rice', 'broccoli', 'garlic', 'lime'], instructions: ['Cook chicken.', 'Scramble eggs.', 'Stir-fry with cauliflower rice, cooked rice, broccoli, garlic, and lime.'] },
    { name: 'Turkey Lettuce Cups', tags: ['weekly menu', 'lunch'], ingredients: ['ground turkey', 'butter lettuce', 'avocado', 'pico', 'pickled onion', 'lime'], instructions: ['Brown turkey.', 'Spoon into lettuce cups.', 'Top with avocado, pico, pickled onion, and lime.'] },
    { name: 'Shrimp Taco Salad', tags: ['weekly menu', 'lunch'], ingredients: ['shrimp', 'cabbage slaw', 'pico', 'avocado', 'Greek yogurt', 'lime'], instructions: ['Cook shrimp.', 'Serve over cabbage slaw with pico, avocado, and lime crema.'] },
    { name: 'Chuck Roast Bowls', tags: ['weekly menu', 'dinner'], ingredients: ['chuck roast', 'beef stock', 'salsa', 'cauliflower rice', 'pico', 'avocado', 'sour cream'], instructions: ['Cook chuck roast until shreddable.', 'Serve over greens or cauliflower rice with pico, avocado, and sour cream.'] },
    { name: 'Lemon Garlic Shrimp', tags: ['weekly menu', 'dinner'], ingredients: ['shrimp', 'zucchini', 'red pepper', 'broccoli', 'garlic', 'lemon', 'basil'], instructions: ['Sauté vegetables.', 'Add garlic and shrimp.', 'Finish with lemon and basil.'] },
    { name: 'Chicken Salad Lettuce Cups', tags: ['weekly menu', 'lunch'], ingredients: ['cooked chicken', 'Greek yogurt', 'celery', 'apple', 'butter lettuce', 'lemon'], instructions: ['Mix chicken salad.', 'Spoon into lettuce cups.'] },
    { name: 'Protein Waffles', tags: ['weekly menu', 'breakfast'], ingredients: ['waffle mix or protein waffle batter', 'Greek yogurt', 'berries', 'peanut butter'], instructions: ['Prepare waffles.', 'Serve with Greek yogurt, berries, and peanut butter.'] }
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

  function bootstrapRecipes() {
    const el = document.getElementById('recipes-bootstrap');
    if (!el) return [];
    try { return JSON.parse(el.textContent || '{}').recipes || []; } catch (_) { return []; }
  }

  function alpineState() {
    if (!window.Alpine) return null;
    const root = document.querySelector('[x-data="recipesPage()"]');
    if (!root) return null;
    try { return window.Alpine.$data(root); } catch (_) { return null; }
  }

  function recipePayload(r) {
    return {
      name: r.name,
      source: 'Life Manager',
      tags: r.tags || ['weekly menu'],
      ingredients: (r.ingredients || []).map((name) => ({ name, qty: '', unit: '' })),
      instructions: r.instructions || [],
      notes: 'Starter recipe from the May 11 weekly menu.'
    };
  }

  async function ensureRecipes() {
    const state = alpineState();
    const recipes = [...bootstrapRecipes(), ...((state && state.recipes) || [])];
    const byName = new Map(recipes.filter((r) => r && r.name).map((r) => [r.name.trim().toLowerCase(), r]));
    const created = [];
    for (const r of STARTERS) {
      const key = r.name.toLowerCase();
      if (byName.has(key)) continue;
      try {
        const res = await fetch('/api/recipes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(recipePayload(r)) });
        const data = await res.json();
        if (data && data.ok && data.recipe) {
          byName.set(key, data.recipe);
          created.push(data.recipe);
        }
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
    return { breakfast: [], lunch: [], dinner: [] };
  }

  async function fillMenu(byName) {
    let menu = await currentMenu();
    for (const slot of ['breakfast', 'lunch', 'dinner']) {
      const existing = new Set((menu[slot] || []).map((e) => String(e.name || '').trim().toLowerCase()));
      for (const [name, notes] of MENU[slot]) {
        if (existing.has(name.toLowerCase())) continue;
        const rec = byName.get(name.toLowerCase());
        try {
          const res = await fetch('/api/recipes/menu/' + slot, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ week_key: WEEK_KEY, recipe_id: rec ? rec.id : null, name, notes })
          });
          const data = await res.json();
          if (data && data.ok && data.menu) menu = data.menu;
          existing.add(name.toLowerCase());
        } catch (_) {}
      }
    }
  }

  async function maybeLoadWeekInUi() {
    const state = alpineState();
    const params = new URLSearchParams(location.search);
    if (!state || params.get('menu_week_start') !== WEEK_START) return;
    try {
      const menu = await currentMenu();
      state.menu = { week_key: WEEK_KEY, breakfast: menu.breakfast || [], lunch: menu.lunch || [], dinner: menu.dinner || [] };
      state.currentWeek = WEEK_KEY;
    } catch (_) {}
  }

  async function run() {
    if (!onRecipesPage()) return;
    const byName = await ensureRecipes();
    await fillMenu(byName);
    await maybeLoadWeekInUi();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(run, 600));
  else setTimeout(run, 600);
})();
