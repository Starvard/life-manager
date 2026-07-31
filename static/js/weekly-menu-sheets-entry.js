(function () {
  const MS_DAY = 86400000;

  function onRecipesPage() {
    return location.pathname.startsWith('/recipes');
  }

  function recipesState() {
    if (!window.Alpine) return null;
    const root = document.querySelector('[x-data="recipesPage()"]');
    if (!root) return null;
    try { return window.Alpine.$data(root); } catch (_) { return null; }
  }

  function pad(n) { return String(n).padStart(2, '0'); }

  function iso(d) {
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  }

  function addDays(d, n) {
    const x = new Date(d);
    x.setDate(x.getDate() + n);
    return x;
  }

  function mondayFor(d) {
    const x = new Date(d);
    x.setHours(0, 0, 0, 0);
    x.setDate(x.getDate() - ((x.getDay() + 6) % 7));
    return x;
  }

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
    if (!onRecipesPage()) return;
    if (document.getElementById('weekly-menu-sheets-entry')) return;
    const tabs = document.querySelector('.rcp-tabs');
    const header = document.querySelector('.page-header');
    const anchor = tabs || header;
    if (!anchor || !anchor.parentNode) return;

    const cacheKey = 'may18-healthy-review-v3';
    const href = '/static/weekly-menu-sheets.html?v=' + encodeURIComponent(cacheKey);
    const card = document.createElement('div');
    card.id = 'weekly-menu-sheets-entry';
    card.className = 'card';
    card.style.margin = '0 0 1rem';
    card.style.padding = '0.9rem 1rem';
    card.innerHTML = '<div style="display:flex;align-items:center;justify-content:space-between;gap:.75rem;flex-wrap:wrap">' +
      '<div><div class="card-title" style="margin-bottom:.2rem">Printable Menu Review</div>' +
      '<p class="subtitle" style="margin:0">Review this week\'s healthy menu here first. After approval, recipes can be added to the Recipe tab/menu.</p></div>' +
      '<a class="btn btn-primary btn-sm" href="' + href + '">Open Printable Menu</a>' +
      '</div>';
    anchor.parentNode.insertBefore(card, tabs ? tabs.nextSibling : anchor.nextSibling);
  }

  function injectMenuWeekPicker() {
    if (!onRecipesPage()) return;
    if (document.getElementById('recipes-menu-week-picker')) return;
    const menuSection = Array.from(document.querySelectorAll('section')).find((s) => s.textContent && s.textContent.includes('Send menu'));
    const menuHeader = menuSection ? menuSection.querySelector('.rcp-menu-header') : null;
    if (!menuHeader || !menuHeader.parentNode) return;

    const state = recipesState();
    const wk = (state && state.currentWeek) || weekKeyForDate(new Date());
    const monday = mondayForWeekKey(wk);

    const picker = document.createElement('div');
    picker.id = 'recipes-menu-week-picker';
    picker.className = 'card';
    picker.style.margin = '0 0 1rem';
    picker.style.padding = '.8rem 1rem';
    picker.innerHTML = '<div style="display:flex;align-items:center;justify-content:space-between;gap:.75rem;flex-wrap:wrap">' +
      '<div><div class="card-title" style="margin-bottom:.2rem">Menu week</div><p class="subtitle" style="margin:0">Build the approved menu for any Monday-start week.</p></div>' +
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
      state.menuSlots = ['breakfast', 'lunch', 'snack', 'dinner'];
      state.menuTargets = Object.assign({}, state.menuTargets || {}, { snack: { min: 4, max: 10 } });
      state.menu = {
        week_key: data.menu.week_key || weekKey,
        breakfast: data.menu.breakfast || [],
        lunch: data.menu.lunch || [],
        snack: data.menu.snack || [],
        dinner: data.menu.dinner || []
      };
      state.currentWeek = state.menu.week_key;
      state.addMenuRecipe = { breakfast: '', lunch: '', snack: '', dinner: '' };
      state.addMenuText = { breakfast: '', lunch: '', snack: '', dinner: '' };
      if (typeof state.flash === 'function') state.flash('Loaded ' + state.weekLabel + '.');
      const monday = iso(mondayForWeekKey(state.currentWeek));
      const url = new URL(location.href);
      url.searchParams.set('menu_week_start', monday);
      history.replaceState(null, '', url.toString());
    } catch (_) {}
  }

  function run() {
    injectMenuSheetsLink();
    setTimeout(injectMenuWeekPicker, 250);
    setTimeout(injectMenuWeekPicker, 900);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run);
  else run();
})();
