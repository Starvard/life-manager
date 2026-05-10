(function () {
  const STARTER_RECIPES = [
    {
      name: 'Turkey Burgers', servings: '4', prep_time: '10 min', cook_time: '12 min', source: 'Life Manager',
      tags: ['weekly menu', 'diabetes friendly', 'dinner'],
      ingredients: [
        { name: 'ground turkey', qty: '1', unit: 'lb' },
        { name: 'cheddar cheese', qty: '4', unit: 'slices' },
        { name: 'butter lettuce', qty: '1', unit: 'head' },
        { name: 'tomato', qty: '1', unit: '' },
        { name: 'Greek yogurt', qty: '1/3', unit: 'cup' },
        { name: 'chipotle in adobo', qty: '1', unit: 'tsp' },
        { name: 'zucchini', qty: '2', unit: '' },
        { name: 'red pepper', qty: '1', unit: '' }
      ],
      instructions: ['Season ground turkey with kosher salt, pepper, garlic, and a little lime zest if desired.', 'Form into patties and sear or grill until cooked through.', 'Mix Greek yogurt with minced chipotle, lime, and a pinch of salt.', 'Serve with butter lettuce, cheddar, tomato, chipotle yogurt sauce, zucchini, and peppers.'],
      notes: 'Menu line: Butter lettuce, cheddar, tomato, chipotle yogurt sauce · zucchini & peppers.'
    },
    {
      name: 'Chicken Fried Rice', servings: '4', prep_time: '10 min', cook_time: '15 min', source: 'Life Manager',
      tags: ['weekly menu', 'diabetes friendly', 'dinner'],
      ingredients: [
        { name: 'chicken', qty: '1', unit: 'lb' }, { name: 'eggs', qty: '2', unit: '' }, { name: 'cauliflower rice', qty: '4', unit: 'cups' }, { name: 'cooked rice', qty: '1', unit: 'cup' }, { name: 'broccoli', qty: '2', unit: 'cups' }, { name: 'garlic', qty: '3', unit: 'cloves' }, { name: 'lime', qty: '1', unit: '' }
      ],
      instructions: ['Cook diced chicken in a hot pan until browned and cooked through.', 'Scramble eggs in the pan, then add garlic, cauliflower rice, cooked rice, and broccoli.', 'Stir-fry until hot and slightly browned.', 'Finish with lime and seasoning to taste.'],
      notes: 'Keep it mostly cauliflower rice with enough real rice to feel right.'
    },
    {
      name: 'Turkey Lettuce Cups', servings: '2-3', prep_time: '10 min', cook_time: '10 min', source: 'Life Manager',
      tags: ['weekly menu', 'lunch'],
      ingredients: [
        { name: 'ground turkey', qty: '1', unit: 'lb' }, { name: 'butter lettuce', qty: '1', unit: 'head' }, { name: 'avocado', qty: '1', unit: '' }, { name: 'pico', qty: '1/2', unit: 'cup' }, { name: 'pickled onion', qty: '1/4', unit: 'cup' }, { name: 'lime', qty: '1', unit: '' }
      ],
      instructions: ['Brown the turkey with salt, pepper, garlic, and a little lime.', 'Spoon into butter lettuce cups.', 'Top with avocado, pico, pickled onion, and lime.'],
      notes: 'Fresh Monday lunch; not leftovers.'
    },
    {
      name: 'Shrimp Taco Salad', servings: '2-3', prep_time: '10 min', cook_time: '6 min', source: 'Life Manager',
      tags: ['weekly menu', 'lunch'],
      ingredients: [
        { name: 'shrimp', qty: '1', unit: 'lb' }, { name: 'cabbage slaw', qty: '4', unit: 'cups' }, { name: 'pico', qty: '1/2', unit: 'cup' }, { name: 'avocado', qty: '1', unit: '' }, { name: 'Greek yogurt', qty: '1/3', unit: 'cup' }, { name: 'lime', qty: '1', unit: '' }, { name: 'chipotle in adobo', qty: '1', unit: 'tsp' }
      ],
      instructions: ['Season shrimp with salt, garlic, lime, and a little chipotle if desired.', 'Sear quickly until just cooked.', 'Serve over cabbage with pico, avocado, and chipotle lime yogurt sauce.'],
      notes: 'Menu line: Cabbage, pico, avocado, chipotle lime crema.'
    },
    {
      name: 'Chuck Roast Bowls', servings: '4-6', prep_time: '10 min', cook_time: '3-8 hr', source: 'Life Manager',
      tags: ['weekly menu', 'dinner'],
      ingredients: [
        { name: 'chuck roast', qty: '2.5', unit: 'lb' }, { name: 'beef stock', qty: '1', unit: 'cup' }, { name: 'salsa', qty: '1', unit: 'cup' }, { name: 'cauliflower rice', qty: '4', unit: 'cups' }, { name: 'pico', qty: '1/2', unit: 'cup' }, { name: 'avocado', qty: '1', unit: '' }, { name: 'sour cream', qty: '1/2', unit: 'cup' }
      ],
      instructions: ['Salt the chuck roast well and sear if time allows.', 'Cook with beef stock and salsa until shreddable.', 'Serve over greens or cauliflower rice with pico, avocado, and sour cream.'],
      notes: 'Easy Saturday dinner after Hilton Head.'
    },
    {
      name: 'Lemon Garlic Shrimp', servings: '3-4', prep_time: '10 min', cook_time: '10 min', source: 'Life Manager',
      tags: ['weekly menu', 'dinner'],
      ingredients: [
        { name: 'shrimp', qty: '1', unit: 'lb' }, { name: 'zucchini', qty: '2', unit: '' }, { name: 'red pepper', qty: '1', unit: '' }, { name: 'broccoli', qty: '2', unit: 'cups' }, { name: 'garlic', qty: '3', unit: 'cloves' }, { name: 'lemon', qty: '1', unit: '' }, { name: 'basil', qty: '1', unit: 'handful' }
      ],
      instructions: ['Sauté zucchini, red pepper, and broccoli until tender-crisp.', 'Add garlic and shrimp; cook until shrimp are just pink.', 'Finish with lemon, basil, butter or olive oil, salt, and pepper.'],
      notes: 'Menu line: Zucchini, red pepper, basil, broccoli.'
    },
    {
      name: 'Chicken Salad Lettuce Cups', servings: '3-4', prep_time: '15 min', cook_time: '0 min', source: 'Life Manager',
      tags: ['weekly menu', 'lunch'],
      ingredients: [
        { name: 'cooked chicken', qty: '2', unit: 'cups' }, { name: 'Greek yogurt', qty: '1/2', unit: 'cup' }, { name: 'celery', qty: '2', unit: 'stalks' }, { name: 'apple', qty: '1/2', unit: '' }, { name: 'butter lettuce', qty: '1', unit: 'head' }, { name: 'lemon', qty: '1', unit: '' }
      ],
      instructions: ['Mix chicken, Greek yogurt, celery, apple, lemon, salt, pepper, and herbs.', 'Spoon into butter lettuce cups and serve cold.'],
      notes: 'Simple Sunday lunch.'
    },
    {
      name: 'Protein Waffles', servings: '3-4', prep_time: '10 min', cook_time: '10 min', source: 'Life Manager',
      tags: ['weekly menu', 'breakfast'],
      ingredients: [
        { name: 'waffle mix or protein waffle batter', qty: '1', unit: 'batch' }, { name: 'Greek yogurt', qty: '1', unit: 'cup' }, { name: 'berries', qty: '1', unit: 'cup' }, { name: 'peanut butter', qty: '2', unit: 'tbsp' }
      ],
      instructions: ['Prepare waffles until crisp.', 'Serve with Greek yogurt, berries, and a small peanut butter drizzle.'],
      notes: 'Saturday breakfast.'
    }
  ];

  const MS_DAY = 86400000;

  function parseBootstrap() {
    const el = document.getElementById('recipes-bootstrap');
    if (!el) return null;
    try { return JSON.parse(el.textContent || '{}'); } catch (_) { return null; }
  }

  function recipesState() {
    if (!window.Alpine) return null;
    const root = document.querySelector('[x-data="recipesPage()"]');
    if (!root) return null;
    try { return window.Alpine.$data(root); } catch (_) { return null; }
  }

  function pad(n) { return String(n).padStart(2, '0'); }
  function iso(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
  function mondayFor(d) { const x = new Date(d); x.setHours(0,0,0,0); x.setDate(x.getDate() - ((x.getDay() + 6) % 7)); return x; }
  function weekKeyForDate(d) {
    const x = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    const day = x.getUTCDay() || 7;
    x.setUTCDate(x.getUTCDate() + 4 - day);
    const yearStart = new Date(Date.UTC(x.getUTCFullYear(), 0, 1));
    const week = Math.ceil((((x - yearStart) / MS_DAY) + 1) / 7);
    return x.getUTCFullYear() + '-W' + pad(week);
  }
  function mondayForWeekKey(wk) {
    const m = String(wk || '').match(/^(\d{4})-W(\d{1,2})$/);
    if (!m) return mondayFor(new Date());
    const year = Number(m[1]);
    const week = Number(m[2]);
    const simple = new Date(Date.UTC(year, 0, 1 + (week - 1) * 7));
    const dow = simple.getUTCDay() || 7;
    if (dow <= 4) simple.setUTCDate(simple.getUTCDate() - dow + 1);
    else simple.setUTCDate(simple.getUTCDate() + 8 - dow);
    return new Date(simple.getUTCFullYear(), simple.getUTCMonth(), simple.getUTCDate());
  }

  function injectMenuSheetsLink() {
    if (!location.pathname.startsWith('/recipes')) return;
    if (document.getElementById('weekly-menu-sheets-entry')) return;
    const tabs = document.querySelector('.rcp-tabs');
    const header = document.querySelector('.page-header');
    const anchor = tabs || header;
    if (!anchor || !anchor.parentNode) return;
    const card = document.createElement('div');
    card.id = 'weekly-menu-sheets-entry';
    card.className = 'card';
    card.style.margin = '0 0 1rem';
    card.style.padding = '0.9rem 1rem';
    card.innerHTML = '<div style="display:flex;align-items:center;justify-content:space-between;gap:.75rem;flex-wrap:wrap">' +
      '<div><div class="card-title" style="margin-bottom:.2rem">Menu Sheets</div>' +
      '<p class="subtitle" style="margin:0">Editable seven-day menu pages with a print-friendly layout.</p></div>' +
      '<a class="btn btn-primary btn-sm" href="/static/weekly-menu-sheets.html">Open Menu Sheets</a>' +
      '</div>';
    anchor.parentNode.insertBefore(card, tabs ? tabs.nextSibling : anchor.nextSibling);
  }

  function injectMenuWeekPicker() {
    if (!location.pathname.startsWith('/recipes')) return;
    if (document.getElementById('recipes-menu-week-picker')) return;
    const menuSection = Array.from(document.querySelectorAll('section')).find((s) => s.textContent && s.textContent.includes('Send menu'));
    const menuHeader = menuSection ? menuSection.querySelector('.rcp-menu-header') : null;
    if (!menuHeader || !menuHeader.parentNode) return;

    const state = recipesState();
    const boot = parseBootstrap();
    const wk = (state && state.currentWeek) || (boot && boot.current_week) || weekKeyForDate(new Date());
    const monday = mondayForWeekKey(wk);

    const picker = document.createElement('div');
    picker.id = 'recipes-menu-week-picker';
    picker.className = 'card';
    picker.style.margin = '0 0 1rem';
    picker.style.padding = '.8rem 1rem';
    picker.innerHTML = '<div style="display:flex;align-items:center;justify-content:space-between;gap:.75rem;flex-wrap:wrap">' +
      '<div><div class="card-title" style="margin-bottom:.2rem">Menu week</div><p class="subtitle" style="margin:0">Build the menu for any Monday-start week.</p></div>' +
      '<div style="display:flex;align-items:center;gap:.45rem;flex-wrap:wrap">' +
      '<button type="button" class="btn btn-outline btn-sm" data-menu-week-prev>‹ Previous</button>' +
      '<label class="rcp-hint" style="display:flex;align-items:center;gap:.4rem">Week starts <input type="date" class="rcp-input" data-menu-week-date style="width:auto;min-width:145px" value="' + iso(monday) + '"></label>' +
      '<button type="button" class="btn btn-outline btn-sm" data-menu-week-next>Next ›</button>' +
      '</div></div>';
    menuHeader.parentNode.insertBefore(picker, menuHeader);

    const input = picker.querySelector('[data-menu-week-date]');
    const prev = picker.querySelector('[data-menu-week-prev]');
    const next = picker.querySelector('[data-menu-week-next]');

    async function loadFromDate(dateIso) {
      const mondayDate = mondayFor(new Date(dateIso + 'T00:00:00'));
      input.value = iso(mondayDate);
      await loadMenuWeek(weekKeyForDate(mondayDate));
    }

    input.addEventListener('change', () => loadFromDate(input.value));
    prev.addEventListener('click', () => loadFromDate(iso(addDays(new Date(input.value + 'T00:00:00'), -7))));
    next.addEventListener('click', () => loadFromDate(iso(addDays(new Date(input.value + 'T00:00:00'), 7))));

    const params = new URLSearchParams(location.search);
    const requested = params.get('menu_week_start');
    if (requested) loadFromDate(requested);
  }

  async function loadMenuWeek(weekKey) {
    const state = recipesState();
    if (!state) return;
    try {
      const res = await fetch('/api/recipes/menu?week=' + encodeURIComponent(weekKey));
      const data = await res.json();
      if (!data || !data.ok || !data.menu) return;
      state.menu = {
        week_key: data.menu.week_key || weekKey,
        breakfast: data.menu.breakfast || [],
        lunch: data.menu.lunch || [],
        dinner: data.menu.dinner || []
      };
      state.currentWeek = state.menu.week_key;
      state.addMenuRecipe = { breakfast: '', lunch: '', dinner: '' };
      state.addMenuText = { breakfast: '', lunch: '', dinner: '' };
      if (typeof state.flash === 'function') state.flash('Loaded ' + state.weekLabel + '.');
      const monday = iso(mondayForWeekKey(state.currentWeek));
      const url = new URL(location.href);
      url.searchParams.set('menu_week_start', monday);
      history.replaceState(null, '', url.toString());
    } catch (_) {}
  }

  async function seedStarterRecipes() {
    if (!location.pathname.startsWith('/recipes')) return;
    const boot = parseBootstrap();
    const existing = new Set(((boot && boot.recipes) || []).map((r) => String(r.name || '').trim().toLowerCase()));
    const missing = STARTER_RECIPES.filter((r) => !existing.has(r.name.toLowerCase()));
    if (!missing.length) return;
    for (const recipe of missing) {
      try {
        await fetch('/api/recipes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(recipe),
        });
      } catch (_) {}
    }
    try { sessionStorage.setItem('weekly-menu-recipes-seeded', String(missing.length)); } catch (_) {}
  }

  function run() {
    injectMenuSheetsLink();
    seedStarterRecipes();
    setTimeout(injectMenuWeekPicker, 250);
    setTimeout(injectMenuWeekPicker, 900);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run);
  else run();
})();
