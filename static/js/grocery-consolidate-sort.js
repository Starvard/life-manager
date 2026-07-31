(function () {
  const ORDER = ['Vegetables', 'Meat', 'Dairy and eggs', 'Middle aisle stuff', 'Other'];
  const UNDO_KEY = 'life-manager.grocery-cleanup.undo';
  let internal = false;

  function onRecipesPage() {
    return location.pathname.startsWith('/recipes');
  }

  function state() {
    if (!window.Alpine) return null;
    const root = document.querySelector('[x-data="recipesPage()"]');
    if (!root) return null;
    try { return window.Alpine.$data(root); } catch (_) { return null; }
  }

  function norm(s) {
    return String(s || '').trim().toLowerCase().replace(/\s+/g, ' ');
  }

  function canonicalName(name) {
    const n = norm(name).replace(/[’']/g, '');
    const aliases = new Map([
      ['greek yogurt?', 'greek yogurt'],
      ['yogurt', 'greek yogurt'],
      ['plain greek yogurt', 'greek yogurt'],
      ['snacking cheese', 'cheese'],
      ['cheddar cheese', 'cheddar'],
      ['whole grain crackers', 'whole-grain crackers'],
      ['crackers', 'whole-grain crackers'],
      ['pickles', 'pickles'],
      ['deli turkey', 'turkey'],
      ['ground turkey', 'ground turkey'],
      ['cauliflower ice', 'cauliflower rice'],
      ['cauliflower rice', 'cauliflower rice'],
      ['red peppers', 'red pepper'],
      ['tomatoes', 'tomatoes'],
      ['apple', 'apples'],
      ['lime', 'limes'],
      ['lemon', 'lemons'],
      ['egg', 'eggs'],
    ]);
    if (aliases.has(n)) return aliases.get(n);
    return n.replace(/\borganic\b|\bfresh\b/g, '').replace(/\s+/g, ' ').trim();
  }

  function prettyName(name) {
    const key = canonicalName(name);
    const map = {
      'greek yogurt': 'Greek yogurt',
      'whole-grain crackers': 'Whole-grain crackers',
      'ground turkey': 'Ground turkey',
      'cauliflower rice': 'Cauliflower rice',
      'red pepper': 'Red pepper',
      'chipotle in adobo': 'Chipotle in adobo',
      'chia seeds': 'Chia seeds',
      'peanut butter': 'Peanut butter',
      'cottage cheese': 'Cottage cheese',
      'deli turkey': 'Deli turkey',
      'snacking cheese': 'Snacking cheese',
    };
    if (map[key]) return map[key];
    return String(name || '').trim().replace(/\s+/g, ' ').replace(/^./, (c) => c.toUpperCase());
  }

  function classifyName(name) {
    const n = canonicalName(name);
    if (/\b(chicken|turkey|beef|steak|shrimp|salmon|bacon|meatball|chuck roast|ground beef|ground turkey)\b/.test(n)) return 'Meat';
    if (/\b(yogurt|cheese|brie|cheddar|cottage cheese|egg|eggs|milk|butter|cream|half and half|sour cream|parmesan)\b/.test(n)) return 'Dairy and eggs';
    if (/\b(cucumber|zucchini|pepper|tomato|tomatoes|lettuce|greens|microgreens|cabbage|slaw|carrot|celery|broccoli|avocado|apple|apples|berries|banana|lime|limes|lemon|lemons|basil|onion|onions|garlic|sweet potato|beets|corn|edamame)\b/.test(n)) return 'Vegetables';
    if (/\b(cracker|crackers|rice|chips|salsa|pico|pickle|pickles|peanut butter|chia|granola|nuts|almonds|cinnamon|seasoning|tortilla|bread|bagel|jam|stock|adobo|cocoa|powder|salt|oil|vinegar)\b/.test(n)) return 'Middle aisle stuff';
    return 'Other';
  }

  function categoryRank(cat) {
    const idx = ORDER.indexOf(cat || 'Other');
    return idx === -1 ? ORDER.length : idx;
  }

  function normalizeQty(q) {
    const s = String(q || '').trim();
    if (!s) return null;
    const frac = s.match(/^(\d+)\/(\d+)$/);
    if (frac) return Number(frac[1]) / Number(frac[2]);
    const num = Number(s);
    return Number.isFinite(num) ? num : null;
  }

  function formatQty(n) {
    if (!Number.isFinite(n)) return '';
    if (Math.abs(n - Math.round(n)) < 0.0001) return String(Math.round(n));
    return String(Math.round(n * 100) / 100);
  }

  function combineQty(a, b) {
    const aq = String(a.qty || '').trim();
    const bq = String(b.qty || '').trim();
    const au = String(a.unit || '').trim();
    const bu = String(b.unit || '').trim();
    if (!aq && !bq) return { qty: '', unit: au || bu };
    if (!aq) return { qty: bq, unit: bu || au };
    if (!bq) return { qty: aq, unit: au || bu };
    if (au.toLowerCase() === bu.toLowerCase()) {
      const an = normalizeQty(aq);
      const bn = normalizeQty(bq);
      if (an !== null && bn !== null) return { qty: formatQty(an + bn), unit: au || bu };
      if (aq === bq) return { qty: aq, unit: au || bu };
      return { qty: Array.from(new Set([aq, bq])).join(' + '), unit: au || bu };
    }
    return { qty: Array.from(new Set([aq + (au ? ' ' + au : ''), bq + (bu ? ' ' + bu : '')])).join(' + '), unit: '' };
  }

  function buildGroups(items) {
    const buckets = new Map(ORDER.map((cat) => [cat, []]));
    (items || []).forEach((item) => {
      const cat = item.category || classifyName(item.name);
      if (!buckets.has(cat)) buckets.set(cat, []);
      buckets.get(cat).push(item);
    });
    return Array.from(buckets.entries())
      .filter(([, items]) => items.length)
      .map(([category, items]) => ({
        category,
        items: items.slice().sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''))),
      }));
  }

  function sortAndClassify(items) {
    return (items || []).map((item) => ({
      ...item,
      category: classifyName(item.name),
      name: String(item.name || '').trim(),
    })).sort((a, b) => {
      const cr = categoryRank(a.category) - categoryRank(b.category);
      if (cr) return cr;
      return String(a.name || '').localeCompare(String(b.name || ''));
    });
  }

  function consolidatedItems(items) {
    const byKey = new Map();
    for (const item of items || []) {
      const name = String(item.name || '').trim();
      if (!name) continue;
      const cat = classifyName(name);
      const key = canonicalName(name) + '::' + norm(item.unit);
      const incoming = { ...item, name: prettyName(name), category: cat, checked: !!item.checked };
      if (!byKey.has(key)) {
        byKey.set(key, { ...incoming });
        continue;
      }
      const current = byKey.get(key);
      const q = combineQty(current, incoming);
      current.qty = q.qty;
      current.unit = q.unit;
      current.checked = current.checked && incoming.checked;
      current.category = current.category || cat;
      byKey.set(key, current);
    }
    return sortAndClassify(Array.from(byKey.values()));
  }

  function saveUndoSnapshot(items) {
    localStorage.setItem(UNDO_KEY, JSON.stringify({ at: new Date().toISOString(), items: JSON.parse(JSON.stringify(items || [])) }));
    updateUndoButton();
  }

  function readUndoSnapshot() {
    try { return JSON.parse(localStorage.getItem(UNDO_KEY) || 'null'); } catch (_) { return null; }
  }

  function updateUndoButton() {
    const btn = document.getElementById('grocery-undo-cleanup');
    if (btn) btn.disabled = !readUndoSnapshot();
  }

  async function directAdd(item) {
    const payload = {
      name: item.name || '', qty: item.qty || '', unit: item.unit || '', category: item.category || classifyName(item.name), checked: !!item.checked,
    };
    for (const url of ['/api/recipes/grocery', '/api/grocery']) {
      try {
        const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        if (!res.ok) continue;
        const data = await res.json().catch(() => ({}));
        return data.item || data.grocery_item || data;
      } catch (_) {}
    }
    return null;
  }

  async function directDelete(item) {
    if (!item || !item.id) return false;
    for (const url of ['/api/recipes/grocery/' + encodeURIComponent(item.id), '/api/grocery/' + encodeURIComponent(item.id)]) {
      try {
        const res = await fetch(url, { method: 'DELETE' });
        if (res.ok) return true;
      } catch (_) {}
    }
    return false;
  }

  async function stateAdd(s, item) {
    const beforeIds = new Set((s.grocery || []).map((x) => x.id));
    const old = { ...(s.newGrocery || {}) };
    s.newGrocery = { name: item.name || '', qty: item.qty || '', unit: item.unit || '', category: item.category || classifyName(item.name) };
    await s.addGrocery();
    s.newGrocery = old;
    return (s.grocery || []).find((x) => !beforeIds.has(x.id)) || null;
  }

  async function addItem(s, item) {
    let added = await directAdd(item);
    if (added && added.ok === false) added = null;
    if (added && added.id) {
      s.grocery = sortAndClassify([...(s.grocery || []), added]);
      return added;
    }
    if (typeof s.addGrocery === 'function') return stateAdd(s, item);
    return null;
  }

  async function deleteItem(s, item) {
    if (!item) return;
    const ok = await directDelete(item);
    if (ok) {
      s.grocery = (s.grocery || []).filter((x) => x.id !== item.id);
      return;
    }
    if (typeof s.deleteGrocery === 'function') await s.deleteGrocery(item);
    else s.grocery = (s.grocery || []).filter((x) => x.id !== item.id);
  }

  function installGroceryGroupsOverride(s) {
    if (!s || s.__grocerySortInstalled) return;
    try {
      Object.defineProperty(s, 'groceryGroups', {
        configurable: true,
        get() { return buildGroups(sortAndClassify(this.grocery || [])); },
      });
    } catch (_) {}
    s.__grocerySortInstalled = true;
  }

  function sortOnly() {
    const s = state();
    if (!s) return;
    installGroceryGroupsOverride(s);
    s.categories = ORDER.concat((s.categories || []).filter((c) => !ORDER.includes(c)));
    s.grocery = sortAndClassify(s.grocery || []);
  }

  async function consolidateAndSort() {
    const s = state();
    if (!s || internal) return;
    internal = true;
    try {
      installGroceryGroupsOverride(s);
      const before = JSON.parse(JSON.stringify(s.grocery || []));
      saveUndoSnapshot(before);
      const next = consolidatedItems(before);
      for (const item of before) await deleteItem(s, item);
      s.grocery = [];
      const added = [];
      for (const item of next) {
        const row = await addItem(s, item);
        added.push(row && row.id ? row : { ...item, id: 'local-' + Math.random().toString(36).slice(2) });
      }
      s.grocery = sortAndClassify(added);
      if (typeof s.flash === 'function') s.flash('Grocery list consolidated and sorted.');
    } finally {
      internal = false;
      updateUndoButton();
    }
  }

  async function undoCleanup() {
    const snap = readUndoSnapshot();
    const s = state();
    if (!snap || !s || internal) return;
    internal = true;
    try {
      const current = JSON.parse(JSON.stringify(s.grocery || []));
      for (const item of current) await deleteItem(s, item);
      s.grocery = [];
      const restored = [];
      for (const item of snap.items || []) {
        const row = await addItem(s, item);
        restored.push(row && row.id ? row : { ...item, id: 'local-' + Math.random().toString(36).slice(2) });
      }
      s.grocery = sortAndClassify(restored);
      localStorage.removeItem(UNDO_KEY);
      if (typeof s.flash === 'function') s.flash('Restored grocery list.');
    } finally {
      internal = false;
      updateUndoButton();
    }
  }

  function injectControls() {
    if (!onRecipesPage() || document.getElementById('grocery-cleanup-controls')) return;
    const actions = document.querySelector('section[x-show="tab === \'grocery\'"] .rcp-list-actions .btn-group')
      || Array.from(document.querySelectorAll('.rcp-list-actions .btn-group')).find((el) => el.textContent.includes('Clear checked'));
    if (!actions) return;
    const wrap = document.createElement('span');
    wrap.id = 'grocery-cleanup-controls';
    wrap.style.display = 'inline-flex';
    wrap.style.gap = '.4rem';
    wrap.style.flexWrap = 'wrap';
    wrap.innerHTML = '<button type="button" class="btn btn-primary btn-sm" id="grocery-consolidate-sort">Consolidate & sort</button>' +
      '<button type="button" class="btn btn-outline btn-sm" id="grocery-undo-cleanup">Undo cleanup</button>';
    actions.prepend(wrap);
    document.getElementById('grocery-consolidate-sort').addEventListener('click', consolidateAndSort);
    document.getElementById('grocery-undo-cleanup').addEventListener('click', undoCleanup);
    updateUndoButton();
  }

  function wrapAddMethods() {
    const s = state();
    if (!s || s.__groceryCleanupWrapped) return;
    installGroceryGroupsOverride(s);
    ['addGrocery', 'addRecipeToGrocery', 'menuToGrocery'].forEach((name) => {
      if (typeof s[name] !== 'function') return;
      const original = s[name].bind(s);
      s[name] = async function (...args) {
        const out = await original(...args);
        if (!internal) setTimeout(sortOnly, 250);
        return out;
      };
    });
    s.__groceryCleanupWrapped = true;
  }

  function run() {
    if (!onRecipesPage()) return;
    wrapAddMethods();
    injectControls();
    sortOnly();
    setTimeout(() => { wrapAddMethods(); injectControls(); sortOnly(); }, 500);
    setTimeout(() => { wrapAddMethods(); injectControls(); sortOnly(); }, 1400);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run);
  else run();
})();
