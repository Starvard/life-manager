(function () {
  const SLOTS = ['breakfast', 'lunch', 'snack', 'dinner'];

  function onRecipesPage() {
    return location.pathname.startsWith('/recipes');
  }

  function state() {
    if (!window.Alpine) return null;
    const root = document.querySelector('[x-data="recipesPage()"]');
    if (!root) return null;
    try { return window.Alpine.$data(root); } catch (_) { return null; }
  }

  function ensureSnackState() {
    const s = state();
    if (!s) return null;
    s.menuSlots = SLOTS;
    s.menuTargets = Object.assign({}, s.menuTargets || {}, { snack: { min: 4, max: 10 } });
    s.addMenuRecipe = Object.assign({ breakfast: '', lunch: '', snack: '', dinner: '' }, s.addMenuRecipe || {});
    s.addMenuText = Object.assign({ breakfast: '', lunch: '', snack: '', dinner: '' }, s.addMenuText || {});
    if (s.menu) s.menu.snack = s.menu.snack || [];
    return s;
  }

  async function refreshSnackForCurrentWeek() {
    const s = ensureSnackState();
    if (!s || !s.currentWeek) return;
    try {
      const res = await fetch('/api/recipes/menu?week=' + encodeURIComponent(s.currentWeek));
      const data = await res.json();
      if (!data || !data.ok || !data.menu) return;
      s.menuSlots = SLOTS;
      s.menu = {
        week_key: data.menu.week_key || s.currentWeek,
        breakfast: data.menu.breakfast || [],
        lunch: data.menu.lunch || [],
        snack: data.menu.snack || [],
        dinner: data.menu.dinner || []
      };
      s.currentWeek = s.menu.week_key;
    } catch (_) {}
  }

  function bindWeekPicker() {
    const input = document.querySelector('[data-menu-week-date]');
    if (!input || input.dataset.snackSlotBound === '1') return;
    input.dataset.snackSlotBound = '1';
    input.addEventListener('change', () => setTimeout(refreshSnackForCurrentWeek, 700));
    document.querySelectorAll('[data-menu-week-prev], [data-menu-week-next]').forEach((btn) => {
      btn.addEventListener('click', () => setTimeout(refreshSnackForCurrentWeek, 700));
    });
  }

  function run() {
    if (!onRecipesPage()) return;
    ensureSnackState();
    bindWeekPicker();
    setTimeout(() => { ensureSnackState(); bindWeekPicker(); refreshSnackForCurrentWeek(); }, 500);
    setTimeout(() => { ensureSnackState(); bindWeekPicker(); refreshSnackForCurrentWeek(); }, 1200);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run);
  else run();
})();
