(function () {
  if (!location.pathname.startsWith('/cards')) return;

  const MS_DAY = 86400000;
  const CACHE = new Map();
  let patchRun = 0;

  function parseIso(s) { return new Date(String(s || '').slice(0, 10) + 'T00:00:00'); }
  function iso(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
  }
  function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
  function mondayFor(d) { const x = new Date(d); const n = (x.getDay() + 6) % 7; x.setDate(x.getDate() - n); return x; }
  function daysBetween(aIso, bIso) { return Math.round((parseIso(aIso) - parseIso(bIso)) / MS_DAY); }
  function weekKeyFor(d) {
    const x = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    const day = x.getUTCDay() || 7;
    x.setUTCDate(x.getUTCDate() + 4 - day);
    const yearStart = new Date(Date.UTC(x.getUTCFullYear(), 0, 1));
    const week = Math.ceil((((x - yearStart) / MS_DAY) + 1) / 7);
    return x.getUTCFullYear() + '-W' + String(week).padStart(2, '0');
  }
  function selectedDate() {
    const inp = document.querySelector('.picker-date');
    if (inp && inp.value) return inp.value;
    const p = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
    const got = Object.fromEntries(p.map((x) => [x.type, x.value]));
    return got.year + '-' + got.month + '-' + got.day;
  }
  function dayIndex(dateIso, weekStartIso) { return Math.max(0, Math.min(6, daysBetween(dateIso, weekStartIso))); }
  function labelDate(dateIso) { return parseIso(dateIso).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC' }); }
  function intervalDays(freq) {
    const f = Number(freq || 0);
    if (f <= 0) return 9999;
    if (f >= 7) return 1;
    return Math.max(1, Math.round(7 / f));
  }
  function esc(s) { return String(s || '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

  async function fetchWeek(wk) {
    if (CACHE.has(wk)) return CACHE.get(wk);
    const p = fetch('/api/routine-cards/' + encodeURIComponent(wk))
      .then((r) => r.ok ? r.json() : { areas: {} })
      .then((data) => data.areas || {})
      .catch(() => ({}));
    CACHE.set(wk, p);
    return p;
  }

  function collectAlpineCards() {
    const out = [];
    if (!window.Alpine) return out;
    document.querySelectorAll('.notecard[x-data]').forEach((el) => {
      try {
        const data = window.Alpine.$data(el);
        if (data && data.card) out.push(data.card);
      } catch (_) {}
    });
    return out;
  }

  function buildCatalog(cards) {
    const out = [];
    cards.forEach((card) => {
      const areaKey = card.area_key || '';
      const areaName = card.area_name || areaKey;
      (card.tasks || []).forEach((task, taskIndex) => {
        out.push({ card, areaKey, areaName, task, taskIndex, name: task.name, freq: Number(task.freq || 0) });
      });
    });
    return out;
  }

  function addHistoryFromCard(card, hist) {
    const areaKey = card.area_key || '';
    const weekStart = card.week_start;
    if (!areaKey || !weekStart) return;
    (card.tasks || []).forEach((task) => {
      const key = areaKey + '::' + task.name;
      (task.days || []).forEach((row, di) => {
        if ((row || []).some(Boolean)) {
          if (!hist[key]) hist[key] = [];
          hist[key].push(iso(addDays(parseIso(weekStart), di)));
        }
      });
    });
  }

  async function loadHistoryAndCatalog(selIso) {
    const sel = parseIso(selIso);
    const start = addDays(mondayFor(sel), -12 * 7);
    const end = addDays(mondayFor(sel), 7);
    const weeks = new Set();
    for (let d = new Date(start); d <= end; d = addDays(d, 7)) weeks.add(weekKeyFor(d));
    const hist = {};
    await Promise.all(Array.from(weeks).map(async (wk) => {
      const areas = await fetchWeek(wk);
      Object.values(areas || {}).forEach((card) => addHistoryFromCard(card, hist));
    }));
    collectAlpineCards().forEach((card) => addHistoryFromCard(card, hist));
    Object.keys(hist).forEach((k) => hist[k] = Array.from(new Set(hist[k])).sort());
    return { hist, catalog: buildCatalog(collectAlpineCards()) };
  }

  function findCatalogItem(catalog, areaKey, areaName, rawName) {
    return catalog.find((x) => x.areaKey === areaKey && x.name === rawName)
      || catalog.find((x) => x.areaName === areaName && x.name === rawName)
      || catalog.find((x) => x.name === rawName);
  }

  function parseTaskDom(el) {
    const strong = el.querySelector('strong');
    const small = el.querySelector('small');
    const name = strong ? strong.textContent.trim() : '';
    const bits = small ? small.textContent.split(' · ').map((x) => x.trim()).filter(Boolean) : [];
    const areaName = bits.length ? bits[bits.length - 1] : '';
    const dataKey = el.getAttribute('data-key') || '';
    const parts = dataKey.split('|');
    return {
      name,
      areaName,
      areaKey: parts[0] || '',
      rawName: parts[1] || name,
      instance: Number(parts[2] || 1),
    };
  }

  function ensureComingUpSection() {
    let section = document.querySelector('.dyn-section.dyn-upcoming');
    if (section) return section;
    const list = document.querySelector('.dyn-list');
    if (!list) return null;
    section = document.createElement('section');
    section.className = 'card dyn-section dyn-upcoming';
    section.innerHTML = '<h3><span>Coming Up</span><small>0</small></h3>';
    list.appendChild(section);
    return section;
  }

  function updateSectionCount(section) {
    const small = section && section.querySelector('h3 small');
    if (small) small.textContent = String(section.querySelectorAll('.dyn-task').length);
  }

  async function completeEarly(item, selIso) {
    const card = item.card;
    const day = dayIndex(selIso, card.week_start);
    const row = (item.task.days && item.task.days[day]) || [false];
    let dot = row.findIndex((v) => !v);
    if (dot < 0) dot = row.length;
    if (!item.task.days[day]) item.task.days[day] = [false];
    while (item.task.days[day].length <= dot) item.task.days[day].push(false);
    item.task.days[day][dot] = true;
    await fetch('/api/routine-cards/' + card.week_key + '/' + item.areaKey + '/set-dot', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: item.taskIndex, day, dot, value: true, list: 'tasks' }),
    });
    CACHE.clear();
    location.reload();
  }

  function makeTaskEarlyCompletable(el, item, selIso, label) {
    if (el.dataset.earlyCompletable === '1') return;
    el.dataset.earlyCompletable = '1';
    el.classList.remove('readonly');
    el.style.cursor = 'pointer';
    const check = el.querySelector('.dyn-check');
    if (check && check.textContent.trim() === '·') check.textContent = '○';
    const small = el.querySelector('small');
    if (small) small.textContent = label + ' · tap to complete today · ' + item.areaName;
    el.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      completeEarly(item, selIso);
    }, { capture: true });
  }

  async function patchRoutineStack() {
    const myRun = ++patchRun;
    const app = document.getElementById('dynamic-routine-app');
    if (!app) return;
    const selIso = selectedDate();
    const { hist, catalog } = await loadHistoryAndCatalog(selIso);
    if (myRun !== patchRun) return;

    // Make Coming Up tasks actionable so an early completion can reset the next due date.
    app.querySelectorAll('.dyn-section.dyn-upcoming .dyn-task').forEach((el) => {
      const info = parseTaskDom(el);
      const item = findCatalogItem(catalog, info.areaKey, info.areaName, info.rawName || info.name);
      if (!item || item.freq >= 7) return;
      makeTaskEarlyCompletable(el, item, selIso, 'Coming up');
    });

    // If a current-week scheduled slot is stale because of an earlier completion
    // from a prior week, move it out of the active stack into Coming Up.
    app.querySelectorAll('.dyn-task[data-key]').forEach((el) => {
      if (el.classList.contains('done') || el.classList.contains('wont')) return;
      if (el.closest('.dyn-upcoming')) return;
      const info = parseTaskDom(el);
      const item = findCatalogItem(catalog, info.areaKey, info.areaName, info.rawName || info.name);
      if (!item || item.freq >= 7) return;
      const key = item.areaKey + '::' + item.name;
      const last = (hist[key] || []).filter((d) => d <= selIso).pop();
      if (!last) return;
      const nextDue = iso(addDays(parseIso(last), intervalDays(item.freq)));
      if (nextDue <= selIso) return;
      const section = ensureComingUpSection();
      if (!section) return;
      const oldSection = el.closest('.dyn-section');
      el.classList.remove('due', 'overdue');
      el.classList.add('upcoming');
      makeTaskEarlyCompletable(el, item, selIso, 'Due ' + labelDate(nextDue));
      section.appendChild(el);
      updateSectionCount(section);
      updateSectionCount(oldSection);
    });
  }

  function schedulePatch() { setTimeout(patchRoutineStack, 80); }
  window.addEventListener('load', schedulePatch);
  document.addEventListener('alpine:initialized', schedulePatch);
  document.addEventListener('click', schedulePatch);
  const obs = new MutationObserver(() => schedulePatch());
  obs.observe(document.body, { childList: true, subtree: true });
})();
