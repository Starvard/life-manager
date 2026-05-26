(function () {
  // May 25 one-recipe smoke test: actually creates the meatball recipe and adds Monday dinner.
  const WEEK_KEY = '2026-W22';
  const WEEK_START = '2026-05-25';
  const RECIPE = {
    name: 'Beef Ricotta Meatballs with Leftover Veggies and Pasta Salad',
    source: 'Life Manager',
    servings: '3-4',
    prep_time: '12 min',
    cook_time: '15-18 min',
    tags: ['weekly menu', 'may 25', 'dinner'],
    ingredients: [
      { name: 'ground beef', qty: '1', unit: 'lb or whatever is left' },
      { name: 'ricotta', qty: '1/3', unit: 'cup' },
      { name: 'egg', qty: '1', unit: '' },
      { name: 'crushed crackers or breadcrumbs', qty: '1/3', unit: 'cup' },
      { name: 'Italian seasoning', qty: '1', unit: 'tsp' },
      { name: 'garlic powder', qty: '1/2', unit: 'tsp' },
      { name: 'leftover vegetables', qty: '1', unit: 'side' },
      { name: 'leftover pasta salad', qty: '1', unit: 'side' }
    ],
    instructions: [
      'Heat oven to 400°F and line a sheet pan with foil or parchment.',
      'Mix ground beef, ricotta, egg, crushed crackers, Italian seasoning, garlic powder, salt, and pepper just until combined.',
      'Roll into small meatballs so they cook quickly.',
      'Bake 15-18 minutes, until browned and cooked through.',
      'Warm the leftover vegetables while the meatballs cook.',
      'Serve the meatballs with leftover vegetables and leftover pasta salad. Add tomato sauce only if you want it.'
    ],
    notes: 'Monday dinner. No extra pasta needed because pasta salad is already the side.'
  };

  function onRecipesPage() { return location.pathname.startsWith('/recipes'); }
  function state() {
    if (!window.Alpine) return null;
    const root = document.querySelector('[x-data="recipesPage()"]');
    if (!root) return null;
    try { return window.Alpine.$data(root); } catch (_) { return null; }
  }
  function bootstrapRecipes() {
    const el = document.getElementById('recipes-bootstrap');
    try { return JSON.parse(el.textContent || '{}').recipes || []; } catch (_) { return []; }
  }
  async function getMenu() {
    try {
      const res = await fetch('/api/recipes/menu?week=' + encodeURIComponent(WEEK_KEY));
      const data = await res.json();
      if (data && data.ok && data.menu) return data.menu;
    } catch (_) {}
    return { breakfast: [], lunch: [], snack: [], dinner: [] };
  }
  function hasName(entries, name) {
    const key = String(name || '').trim().toLowerCase();
    return (entries || []).some((entry) => String(entry.name || '').trim().toLowerCase() === key);
  }
  async function ensureRecipe() {
    const s = state();
    const recipes = bootstrapRecipes().concat((s && s.recipes) || []);
    const existing = recipes.find((recipe) => String(recipe.name || '').trim().toLowerCase() === RECIPE.name.toLowerCase());
    if (existing) return existing;
    try {
      const res = await fetch('/api/recipes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(RECIPE)
      });
      const data = await res.json();
      if (data && data.ok && data.recipe) {
        if (s) s.recipes = (s.recipes || []).concat([data.recipe]);
        return data.recipe;
      }
    } catch (_) {}
    return null;
  }
  async function ensureDinnerCard(recipe) {
    let menu = await getMenu();
    if (hasName(menu.dinner || [], RECIPE.name)) return;
    try {
      await fetch('/api/recipes/menu/dinner', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          week_key: WEEK_KEY,
          recipe_id: recipe ? recipe.id : null,
          name: RECIPE.name,
          notes: 'Monday — no extra pasta needed'
        })
      });
    } catch (_) {}
  }
  async function loadWeekInUi() {
    const s = state();
    if (!s) return;
    const params = new URLSearchParams(location.search);
    if (params.get('menu_week_start') !== WEEK_START && s.currentWeek !== WEEK_KEY) return;
    const menu = await getMenu();
    s.menuSlots = ['breakfast', 'lunch', 'snack', 'dinner'];
    s.addMenuRecipe = { breakfast: '', lunch: '', snack: '', dinner: '' };
    s.addMenuText = { breakfast: '', lunch: '', snack: '', dinner: '' };
    s.menu = { week_key: WEEK_KEY, breakfast: menu.breakfast || [], lunch: menu.lunch || [], snack: menu.snack || [], dinner: menu.dinner || [] };
    s.currentWeek = WEEK_KEY;
  }
  async function run() {
    if (!onRecipesPage()) return;
    const recipe = await ensureRecipe();
    await ensureDinnerCard(recipe);
    await loadWeekInUi();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(run, 900));
  else setTimeout(run, 900);
})();
