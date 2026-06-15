(function () {
  if (!location.pathname.startsWith('/cards')) return;

  const MS_DAY = 86400000;
  const TZ = 'America/New_York';
  const SECTION_KEY = 'lm:routine-section:';
  const WEEK_CACHE = new Map();
  const HISTORY_CACHE = new Map();

  function parseIso(s) { return new Date(String(s || '').slice(0, 10) + 'T00:00:00'); }
  function iso(d) { return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }
  function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
  function daysBetween(a, b) { return Math.round((parseIso(a) - parseIso(b)) / MS_DAY); }
  function mondayFor(d) { const x = new Date(d); x.setDate(x.getDate() - ((x.getDay() + 6) % 7)); return x; }
  function weekKeyFor(d) {
    const x = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    const day = x.getUTCDay() || 7;
    x.setUTCDate(x.getUTCDate() + 4 - day);
    const yearStart = new Date(Date.UTC(x.getUTCFullYear(), 0, 1));
    const week = Math.ceil((((x - yearStart) / MS_DAY) + 1) / 7);
    return x.getUTCFullYear() + '-W' + String(week).padStart(2, '0');
  }
  function todayIso() {
    const p = new Intl.DateTimeFormat('en-US', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
    const got = Object.fromEntries(p.map((x) => [x.type, x.value]));
    return got.year + '-' + got.month + '-' + got.day;
  }
  function selectedIso() {
    const urlDate = new URLSearchParams(location.search).get('date');
    if (/^\d{4}-\d{2}-\d{2}$/.test(urlDate || '')) return urlDate;
    const inp = document.querySelector('.picker-date');
    return inp && inp.value ? inp.value : todayIso();
  }
  function dayIndex(dateIso, weekStartIso) { return Math.max(0, Math.min(6, daysBetween(dateIso, weekStartIso))); }
  function dateLabel(dateIso, long) { return parseIso(dateIso).toLocaleDateString('en-US', long ? { weekday: 'long', month: 'long', day: 'numeric', timeZone: 'UTC' } : { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC' }); }
  function esc(s) { return String(s || '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function css(s) { return (window.CSS && CSS.escape) ? CSS.escape(s) : String(s || '').replace(/[^a-zA-Z0-9_-]/g, '\\$&'); }
  function isDaily(freq) { return Number(freq || 0) >= 7; }
  function intervalDays(freq) {
    const f = Number(freq || 0);
    if (!Number.isFinite(f) || f <= 0) return 9999;
    if (f >= 7) return 1;
    return Math.max(1, Math.round(7 / f));
  }
  function freqFromEveryDays(days) {
    const d = Number(days || 0);
    if (!Number.isFinite(d) || d <= 0) return 1;
    return Number((7 / d).toFixed(3));
  }
  function keyOf(areaKey, name) { return areaKey + '::' + name; }

  function injectStyles() {
    if (document.getElementById('routine-effective-stack-styles')) return;
    const style = document.createElement('style');
    style.id = 'routine-effective-stack-styles';
    style.textContent = `
      body.dynamic-routines-active .notecard,
      body.dynamic-routines-active .area-tabs,
      body.dynamic-routines-active .cards-today-score,
      body.dynamic-routines-active .picker,
      body.dynamic-routines-active .view-toggle { display:none !important; }
      #dynamic-routine-app { margin:1rem 0 1.5rem; }
      .eff-columns { display:grid; grid-template-columns:minmax(280px,.95fr) minmax(320px,1.35fr); gap:.85rem; align-items:start; }
      .eff-column { display:grid; gap:.7rem; }
      .eff-section,.eff-column-title,.eff-add-card,.eff-nav-card { padding:.72rem; }
      .eff-column-title h3,.eff-section h3 { margin:0 0 .35rem; display:flex; justify-content:space-between; gap:.75rem; font-size:.92rem; }
      .eff-column-title p,.eff-nav-card p,.eff-hint { margin:.2rem 0 0; color:var(--text-muted); font-size:.76rem; line-height:1.35; }
      .eff-task { width:100%; display:flex; align-items:center; gap:.68rem; border:1px solid rgba(148,163,184,.18); border-left-width:5px; border-radius:.9rem; padding:.74rem .76rem; margin:.38rem 0; background:rgba(255,255,255,.035); color:inherit; text-align:left; cursor:pointer; }
      .eff-task:hover { background:rgba(255,255,255,.06); }
      .eff-task[disabled] { opacity:.68; cursor:wait; }
      .eff-task.overdue { border-color:rgba(248,113,113,.48); border-left-color:rgba(248,113,113,1); background:rgba(248,113,113,.11); }
      .eff-task.due,.eff-task.extra { border-left-color:rgba(250,204,21,.95); background:rgba(250,204,21,.07); }
      .eff-task.daily { border-left-color:rgba(99,179,255,.8); }
      .eff-task.upcoming { border-left-color:rgba(148,163,184,.65); opacity:.94; }
      .eff-task.future { border-left-color:rgba(148,163,184,.35); opacity:.72; }
      .eff-task.done { border-left-color:rgba(134,239,172,.9); background:rgba(134,239,172,.07); opacity:.82; }
      .eff-task.done strong { text-decoration:line-through; opacity:.72; }
      .eff-task strong { display:block; font-size:.95rem; }
      .eff-task small { display:block; color:var(--text-muted); margin-top:.13rem; }
      .eff-check { display:grid; place-items:center; flex:0 0 1.6rem; width:1.6rem; height:1.6rem; border-radius:999px; background:rgba(255,255,255,.06); font-weight:900; }
      .eff-summary,.eff-recent { display:flex; flex-wrap:wrap; gap:.45rem; margin:.45rem 0 0; }
      .eff-summary span,.eff-recent a,.eff-bottom-nav button,.eff-bottom-nav a { border:1px solid rgba(148,163,184,.2); border-radius:999px; padding:.36rem .62rem; background:rgba(255,255,255,.035); color:inherit; text-decoration:none; font-size:.82rem; }
      .eff-bottom-nav { margin-top:.8rem; display:flex; align-items:center; justify-content:center; gap:.45rem; flex-wrap:wrap; }
      .eff-bottom-nav input { border:1px solid rgba(148,163,184,.22); border-radius:.7rem; padding:.43rem .55rem; background:rgba(255,255,255,.04); color:inherit; }
      .eff-add-card { display:flex; align-items:center; gap:.55rem; flex-wrap:wrap; }
      .eff-empty { padding:.9rem; color:var(--text-muted); }
      .lm-sheet-backdrop { position:fixed; inset:0; z-index:10000; background:rgba(0,0,0,.48); display:flex; align-items:flex-end; justify-content:center; padding:.75rem; }
      .lm-edit-sheet { width:min(480px,100%); border:1px solid rgba(148,163,184,.25); border-radius:1.05rem; background:rgb(15,23,42); box-shadow:0 28px 90px rgba(0,0,0,.48); padding:.95rem; }
      .lm-edit-sheet h3 { margin:0 0 .25rem; font-size:1rem; }
      .lm-edit-sheet p { margin:0 0 .75rem; color:var(--text-muted); font-size:.8rem; line-height:1.35; }
      .lm-edit-grid { display:grid; gap:.55rem; }
      .lm-edit-grid label { display:grid; gap:.22rem; font-size:.76rem; color:var(--text-muted); font-weight:700; }
      .lm-edit-grid input,.lm-edit-grid select { width:100%; border:1px solid var(--border); border-radius:.65rem; padding:.62rem .65rem; background:rgba(255,255,255,.055); color:var(--text); }
      .lm-edit-actions { display:flex; gap:.45rem; justify-content:space-between; margin-top:.85rem; }
      .lm-edit-actions .right { margin-left:auto; display:flex; gap:.45rem; }
      .lm-edit-error { border:1px solid rgba(248,113,113,.4); background:rgba(248,113,113,.12); color:#fecaca; border-radius:.65rem; padding:.55rem .65rem; font-size:.78rem; margin-top:.75rem; }
      @media(max-width:840px){.eff-columns{grid-template-columns:1fr}.eff-task{padding:.82rem .78rem}.eff-column-title{display:none}.eff-add-card{align-items:flex-start;flex-direction:column}}
    `;
    document.head.appendChild(style);
  }

  function alpineCards() {
    const out = [];
    if (!window.Alpine) return out;
    document.querySelectorAll('.notecard[x-data]').forEach((el) => {
      try {
        const data = window.Alpine.$data(el);
        if (!data || !data.card) return;
        const card = data.card;
        const fallbackKey = String(el.id || '').replace(/^card-/, '');
        card.area_key = card.area_key || fallbackKey;
        card.week_key = card.week_key || (data.weekKey || data.week_key || '');
        out.push(card);
      } catch (_) {}
    });
    return out;
  }

  function catalogFrom(cards) {
    const out = [];
    cards.forEach((card, cardIndex) => {
      const areaKey = card.area_key || '';
      const areaName = card.area_name || areaKey;
      (card.tasks || []).forEach((task, taskIndex) => {
        out.push({ card, cardIndex, areaKey, areaName, task, taskIndex, name: task.name || '', freq: Number(task.freq || 0), configured: out.length });
      });
    });
    return out;
  }

  function dailyBucket(name, dot, total, areaKey) {
    const n = String(name || '').toLowerCase();
    if (n.includes('brush') || n.includes('floss')) return dot === 0 ? 'Morning' : 'Evening';
    if (n.includes('water')) {
      if (dot === 0) return 'Morning';
      if (dot >= Math.max(1, total - 2)) return 'Evening';
      return 'Midday';
    }
    if (total > 1) return ['Morning', 'Midday', 'Evening'][Math.round((dot / Math.max(1, total - 1)) * 2)] || 'Midday';
    const saved = localStorage.getItem(SECTION_KEY + areaKey + '::' + name);
    if (saved) return saved;
    if (n.includes('coffee') || n.includes('breakfast') || n.includes('vitamin') || n.includes('med') || n.includes('morning')) return 'Morning';
    if (n.includes('dinner') || n.includes('evening') || n.includes('bed') || n.includes('trash') || n.includes('dish')) return 'Evening';
    return 'Midday';
  }

  function dailyItems(item, selIso) {
    const di = dayIndex(selIso, item.card.week_start);
    const days = item.task.days || [];
    const row = days[di] || [];
    const freqCount = Math.max(1, Math.round(Number(item.task.freq || 7) / 7));
    const scheduledMax = Math.max(0, ...((item.task.scheduled || []).map((n) => Number(n || 0))));
    const rowMax = Math.max(0, ...(days.map((drow) => (Array.isArray(drow) ? drow.length : 0))));
    const count = Math.max(1, freqCount, scheduledMax, rowMax);
    const out = [];
    for (let dot = 0; dot < count; dot++) {
      const done = !!row[dot];
      out.push({ item, dot, isDaily: true, bucket: dailyBucket(item.name, dot, count, item.areaKey), status: done ? 'done' : 'daily', label: done ? 'Done today' : 'Due today', name: item.name, areaName: item.areaName, sort: done ? 90 : 20 });
    }
    return out;
  }

  function addHistoryFromCard(card, hist, selectedDate) {
    const areaKey = card.area_key || '';
    if (!areaKey || !card.week_start) return;
    (card.tasks || []).forEach((task) => {
      const key = keyOf(areaKey, task.name || '');
      (task.days || []).forEach((row, di) => {
        if (!(row || []).some(Boolean)) return;
        const doneIso = iso(addDays(parseIso(card.week_start), di));
        if (doneIso > selectedDate) return;
        if (!hist[key]) hist[key] = [];
        hist[key].push(doneIso);
      });
    });
  }

  async function fetchWeek(wk) {
    if (WEEK_CACHE.has(wk)) return WEEK_CACHE.get(wk);
    const p = fetch('/api/routine-cards/' + encodeURIComponent(wk), { cache: 'no-store' })
      .then((r) => r.ok ? r.json() : { areas: {} })
      .then((data) => data.areas || {})
      .catch(() => ({}));
    WEEK_CACHE.set(wk, p);
    return p;
  }

  function historyLookbackWeeks(items) {
    const maxDays = items.reduce((max, item) => isDaily(item.freq) ? max : Math.max(max, intervalDays(item.freq)), 0);
    return Math.max(6, Math.min(32, Math.ceil(maxDays / 7) + 2));
  }

  async function loadHistory(selIso, items) {
    const cacheKey = selIso + ':' + items.length;
    if (HISTORY_CACHE.has(cacheKey)) return HISTORY_CACHE.get(cacheKey);
    const promise = (async () => {
      const weeks = [];
      const lookback = historyLookbackWeeks(items);
      const selectedMonday = mondayFor(parseIso(selIso));
      for (let i = lookback; i >= 0; i--) weeks.push(weekKeyFor(addDays(selectedMonday, -7 * i)));
      const hist = {};
      for (let i = 0; i < weeks.length; i += 6) {
        const chunk = weeks.slice(i, i + 6);
        const areasByWeek = await Promise.all(chunk.map(fetchWeek));
        areasByWeek.forEach((areas) => {
          Object.values(areas || {}).forEach((card) => addHistoryFromCard(card, hist, selIso));
        });
        await new Promise((resolve) => setTimeout(resolve, 0));
      }
      alpineCards().forEach((card) => addHistoryFromCard(card, hist, selIso));
      Object.keys(hist).forEach((k) => { hist[k] = Array.from(new Set(hist[k])).sort(); });
      return hist;
    })();
    HISTORY_CACHE.set(cacheKey, promise);
    return promise;
  }

  function scheduledDates(item) {
    const out = [];
    const start = parseIso(item.card.week_start);
    (item.task.scheduled || []).forEach((n, di) => { if (Number(n || 0) > 0) out.push(iso(addDays(start, di))); });
    return out.sort();
  }

  function flexState(item, hist, selIso) {
    const completions = (hist[keyOf(item.areaKey, item.name)] || []).filter((d) => d <= selIso).sort();
    const doneToday = completions.includes(selIso);
    const last = completions.length ? completions[completions.length - 1] : null;
    const interval = intervalDays(item.freq);
    let dueIso = null;
    if (last) dueIso = iso(addDays(parseIso(last), interval));
    else {
      const sched = scheduledDates(item);
      dueIso = sched.find((d) => d >= selIso) || sched.filter((d) => d <= selIso).pop() || selIso;
    }
    if (doneToday) return { status: 'done', dueIso, sort: 90, label: dueIso ? 'Done today · next due ' + dateLabel(dueIso, false) : 'Done today' };
    const delta = daysBetween(selIso, dueIso);
    if (delta > 0) return { status: 'overdue', dueIso, sort: 1, label: delta + ' day' + (delta === 1 ? '' : 's') + ' overdue · due ' + dateLabel(dueIso, false) };
    if (delta === 0) return { status: 'due', dueIso, sort: 10, label: 'Due today' };
    if (delta >= -14) return { status: 'upcoming', dueIso, sort: 60, label: 'Due ' + dateLabel(dueIso, false) };
    return { status: 'future', dueIso, sort: 75, label: 'Due ' + dateLabel(dueIso, false) };
  }

  async function saveDot(item, selIso, dotHint) {
    const di = dayIndex(selIso, item.card.week_start);
    item.task.days = item.task.days || [];
    if (!Array.isArray(item.task.days[di])) item.task.days[di] = [false];
    let dot = Number.isInteger(dotHint) ? dotHint : item.task.days[di].findIndex((v) => !v);
    if (dot < 0) dot = item.task.days[di].length;
    while (item.task.days[di].length <= dot) item.task.days[di].push(false);
    const next = !item.task.days[di][dot];
    item.task.days[di][dot] = next;
    const res = await fetch('/api/routine-cards/' + item.card.week_key + '/' + item.areaKey + '/set-dot', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: item.taskIndex, day: di, dot, value: next, list: 'tasks' }),
    });
    if (!res.ok) throw new Error('Routine save failed');
    HISTORY_CACHE.clear();
    return next;
  }

  function updateDailyButton(btn, row, done) {
    row.status = done ? 'done' : 'daily';
    btn.classList.toggle('done', done);
    btn.classList.toggle('daily', !done);
    const check = btn.querySelector('.eff-check');
    const small = btn.querySelector('small');
    if (check) check.textContent = done ? '✓' : '○';
    if (small) small.textContent = (done ? 'Done today' : 'Due today') + ' · ' + row.areaName;
    const summaryDone = document.querySelector('[data-daily-done-count]');
    const allDaily = document.querySelectorAll('[data-row-kind="daily"]');
    const doneDaily = document.querySelectorAll('[data-row-kind="daily"].done');
    if (summaryDone) summaryDone.textContent = doneDaily.length + '/' + allDaily.length + ' daily done';
  }

  async function getManageFormDoc() {
    const html = await fetch('/routines/embed', { cache: 'no-store' }).then((r) => r.text());
    return new DOMParser().parseFromString(html, 'text/html');
  }
  function freqInputValue(freq, everyDays) {
    if (everyDays) return String(freqFromEveryDays(everyDays));
    const f = Number(freq || 0);
    return Number.isFinite(f) && f > 0 ? String(f) : '1';
  }
  async function submitManageForm(doc) {
    const form = doc.querySelector('form[action$="/routines/save"]') || doc.querySelector('form');
    if (!form) throw new Error('Could not find routine save form.');
    const res = await fetch('/routines/save', { method: 'POST', body: new FormData(form), redirect: 'follow' });
    if (!res.ok) throw new Error('Routine save failed.');
  }
  async function saveRoutineEdit(row, vals) {
    const doc = await getManageFormDoc();
    const area = row.item.areaKey;
    const idx = row.item.taskIndex;
    const nameEl = doc.querySelector('[name="task_name_' + css(area) + '_' + idx + '"]');
    const freqEl = doc.querySelector('[name="task_freq_' + css(area) + '_' + idx + '"]');
    const fpyEl = doc.querySelector('[name="task_fpy_' + css(area) + '_' + idx + '"]');
    const delEl = doc.querySelector('[name="task_delete_' + css(area) + '_' + idx + '"]');
    if (!nameEl) throw new Error('Could not find task in manage form.');
    if (vals.deleteTask) {
      if (delEl) delEl.checked = true;
    } else {
      nameEl.value = vals.name || row.name;
      if (fpyEl) fpyEl.value = '';
      if (freqEl) freqEl.value = freqInputValue(vals.freq, vals.everyDays);
      if (vals.section && isDaily(freqEl ? Number(freqEl.value) : row.item.freq)) localStorage.setItem(SECTION_KEY + area + '::' + nameEl.value, vals.section);
    }
    await submitManageForm(doc);
  }
  async function addRoutineTask(vals) {
    const doc = await getManageFormDoc();
    const area = vals.areaKey;
    const nameEl = doc.querySelector('[name="new_task_name_' + css(area) + '"]');
    const freqEl = doc.querySelector('[name="new_task_freq_' + css(area) + '"]');
    const fpyEl = doc.querySelector('[name="new_task_fpy_' + css(area) + '"]');
    if (!nameEl || !freqEl) throw new Error('Could not find add-task fields.');
    nameEl.value = vals.name || 'New task';
    if (fpyEl) fpyEl.value = '';
    freqEl.value = freqInputValue(vals.freq, vals.everyDays);
    if (vals.section && Number(freqEl.value) >= 7) localStorage.setItem(SECTION_KEY + area + '::' + nameEl.value, vals.section);
    await submitManageForm(doc);
  }

  function closeSheet() { document.querySelector('.lm-sheet-backdrop')?.remove(); }
  function showSheetError(wrap, msg) {
    let el = wrap.querySelector('.lm-edit-error');
    if (!el) { el = document.createElement('div'); el.className = 'lm-edit-error'; wrap.querySelector('.lm-edit-actions')?.before(el); }
    el.textContent = msg || 'Something went wrong.';
  }
  function areaOptions(cards, selected) {
    const seen = new Set();
    return cards.map((c) => ({ key: c.area_key || '', name: c.area_name || c.area_key || '' }))
      .filter((a) => a.key && !seen.has(a.key) && seen.add(a.key))
      .map((a) => '<option value="' + esc(a.key) + '"' + (a.key === selected ? ' selected' : '') + '>' + esc(a.name) + '</option>').join('');
  }
  function syncType(wrap, prefix) {
    const type = wrap.querySelector('#lm-' + prefix + '-type')?.value || 'daily';
    wrap.querySelector('#lm-' + prefix + '-days-wrap').style.display = type === 'every' ? '' : 'none';
    wrap.querySelector('#lm-' + prefix + '-freq-wrap').style.display = type === 'freq' ? '' : 'none';
    wrap.querySelector('#lm-' + prefix + '-section-wrap').style.display = type === 'daily' ? '' : 'none';
  }
  function openAddSheet(cards, preferredType) {
    closeSheet();
    const firstArea = (cards[0] && cards[0].area_key) || '';
    const daily = preferredType !== 'recurring';
    const wrap = document.createElement('div');
    wrap.className = 'lm-sheet-backdrop';
    wrap.innerHTML = '<div class="lm-edit-sheet" role="dialog" aria-modal="true"><h3>Add routine task</h3><p>Adds to your saved routine list.</p><div class="lm-edit-grid">' +
      '<label>Area<select id="lm-add-area">' + areaOptions(cards, firstArea) + '</select></label>' +
      '<label>Name<input id="lm-add-name" type="text" placeholder="Drink water"></label>' +
      '<label>Type<select id="lm-add-type"><option value="daily"' + (daily ? ' selected' : '') + '>Daily</option><option value="every"' + (!daily ? ' selected' : '') + '>Every N days</option><option value="freq">Times per week</option></select></label>' +
      '<label id="lm-add-days-wrap">Every N days<input id="lm-add-days" type="number" min="1" step="1" value="3"></label>' +
      '<label id="lm-add-freq-wrap" style="display:none">Frequency per week<input id="lm-add-freq" type="number" min="0" step="0.01" value="1"></label>' +
      '<label id="lm-add-section-wrap">Daily section<select id="lm-add-section"><option>Morning</option><option selected>Midday</option><option>Evening</option></select></label>' +
      '</div><div class="lm-edit-actions"><button type="button" class="btn btn-secondary btn-sm" data-action="cancel">Cancel</button><span class="right"><button type="button" class="btn btn-primary btn-sm" data-action="save">Add</button></span></div></div>';
    wrap.addEventListener('change', (e) => { if (e.target && e.target.id === 'lm-add-type') syncType(wrap, 'add'); });
    wrap.addEventListener('click', async (e) => {
      if (e.target === wrap) { closeSheet(); return; }
      const action = e.target.closest('[data-action]')?.getAttribute('data-action');
      if (!action) return;
      if (action === 'cancel') { closeSheet(); return; }
      const btn = e.target.closest('[data-action]');
      const type = wrap.querySelector('#lm-add-type').value;
      const vals = { areaKey: wrap.querySelector('#lm-add-area').value, name: wrap.querySelector('#lm-add-name').value.trim(), freq: type === 'daily' ? 7 : wrap.querySelector('#lm-add-freq').value, everyDays: type === 'every' ? wrap.querySelector('#lm-add-days').value : '', section: type === 'daily' ? wrap.querySelector('#lm-add-section').value : '' };
      if (!vals.name) return;
      if (btn) btn.disabled = true;
      try { await addRoutineTask(vals); location.reload(); } catch (err) { if (btn) btn.disabled = false; showSheetError(wrap, err && err.message ? err.message : 'Could not add routine.'); }
    });
    document.body.appendChild(wrap);
    syncType(wrap, 'add');
    setTimeout(() => wrap.querySelector('#lm-add-name')?.focus(), 50);
  }
  function openEditSheet(row) {
    closeSheet();
    const item = row.item;
    const daily = row.isDaily || isDaily(item.freq);
    const wrap = document.createElement('div');
    wrap.className = 'lm-sheet-backdrop';
    const currentSection = localStorage.getItem(SECTION_KEY + item.areaKey + '::' + item.name) || row.bucket || 'Midday';
    wrap.innerHTML = '<div class="lm-edit-sheet" role="dialog" aria-modal="true"><h3>Edit routine task</h3><p>' + esc(item.areaName + ' · long-press editor') + '</p><div class="lm-edit-grid">' +
      '<label>Name<input id="lm-edit-name" type="text" value="' + esc(item.name) + '"></label>' +
      '<label>Type<select id="lm-edit-type"><option value="daily"' + (daily ? ' selected' : '') + '>Daily</option><option value="every"' + (!daily ? ' selected' : '') + '>Every N days</option><option value="freq">Times per week</option></select></label>' +
      '<label id="lm-edit-days-wrap">Every N days<input id="lm-edit-days" type="number" min="1" step="1" value="' + intervalDays(item.freq) + '"></label>' +
      '<label id="lm-edit-freq-wrap" style="display:none">Frequency per week<input id="lm-edit-freq" type="number" min="0" step="0.01" value="' + esc(item.freq || 1) + '"></label>' +
      '<label id="lm-edit-section-wrap">Daily section<select id="lm-edit-section"><option>Morning</option><option>Midday</option><option>Evening</option></select></label>' +
      '</div><div class="lm-edit-actions"><button type="button" class="btn btn-danger btn-sm" data-action="delete">Delete</button><span class="right"><button type="button" class="btn btn-secondary btn-sm" data-action="cancel">Cancel</button><button type="button" class="btn btn-primary btn-sm" data-action="save">Save</button></span></div></div>';
    wrap.addEventListener('change', (e) => { if (e.target && e.target.id === 'lm-edit-type') syncType(wrap, 'edit'); });
    wrap.addEventListener('click', async (e) => {
      if (e.target === wrap) { closeSheet(); return; }
      const action = e.target.closest('[data-action]')?.getAttribute('data-action');
      if (!action) return;
      if (action === 'cancel') { closeSheet(); return; }
      if (action === 'delete' && !confirm('Delete ' + item.name + '?')) return;
      const btn = e.target.closest('[data-action]');
      const type = wrap.querySelector('#lm-edit-type').value;
      if (btn) btn.disabled = true;
      try {
        await saveRoutineEdit(row, { deleteTask: action === 'delete', name: wrap.querySelector('#lm-edit-name').value.trim(), freq: type === 'daily' ? 7 : wrap.querySelector('#lm-edit-freq').value, everyDays: type === 'every' ? wrap.querySelector('#lm-edit-days').value : '', section: type === 'daily' ? wrap.querySelector('#lm-edit-section').value : '' });
        location.reload();
      } catch (err) { if (btn) btn.disabled = false; showSheetError(wrap, err && err.message ? err.message : 'Routine save failed.'); }
    });
    document.body.appendChild(wrap);
    const section = wrap.querySelector('#lm-edit-section');
    if (section) section.value = currentSection;
    syncType(wrap, 'edit');
    setTimeout(() => wrap.querySelector('#lm-edit-name')?.focus(), 50);
  }
  function bindLongPress(btn, row) {
    let timer = null;
    let fired = false;
    const clear = () => { if (timer) clearTimeout(timer); timer = null; };
    btn.addEventListener('pointerdown', (e) => { if (e.button && e.button !== 0) return; fired = false; clear(); timer = setTimeout(() => { fired = true; openEditSheet(row); }, 750); });
    ['pointerup', 'pointercancel', 'pointerleave'].forEach((ev) => btn.addEventListener(ev, clear));
    btn.addEventListener('contextmenu', (e) => { e.preventDefault(); clear(); openEditSheet(row); });
    btn.addEventListener('click', (e) => { if (fired) { e.preventDefault(); e.stopImmediatePropagation(); fired = false; } }, true);
  }
  function taskButton(row, idx) {
    const icon = row.status === 'done' ? '✓' : row.status === 'overdue' ? '!' : '○';
    const kind = row.isDaily ? 'daily' : 'flex';
    return '<button type="button" class="eff-task ' + esc(row.status) + '" data-eff-idx="' + idx + '" data-row-kind="' + kind + '"><span class="eff-check">' + icon + '</span><span><strong>' + esc(row.name) + '</strong><small>' + esc(row.label + ' · ' + row.areaName) + '</small></span></button>';
  }
  function sectionHtml(title, list, refs) {
    if (!list.length) return '';
    let html = '<section class="card eff-section"><h3><span>' + esc(title) + '</span><small>' + list.length + '</small></h3>';
    list.forEach((r) => { refs.push(r); html += taskButton(r, refs.length - 1); });
    return html + '</section>';
  }
  function navHtml(selIso) {
    const base = parseIso(selIso);
    const links = ['<a href="/cards">Today</a>'];
    for (let i = 1; i <= 5; i++) {
      const d = iso(addDays(base, -i));
      links.push('<a href="/cards/day?date=' + d + '">' + (i === 1 ? 'Yesterday' : i + ' days ago') + '</a>');
    }
    return '<section class="card eff-nav-card"><p><strong>' + esc(dateLabel(selIso, true)) + (selIso === todayIso() ? ' · Today' : '') + '</strong></p><div class="eff-recent">' + links.join('') + '</div><div class="eff-bottom-nav"><button type="button" data-day-nav="-1">‹</button><input type="date" value="' + esc(selIso) + '" data-date-picker><button type="button" data-day-nav="1">›</button></div></section>';
  }
  function wireNav(root, selIso) {
    root.querySelectorAll('[data-day-nav]').forEach((btn) => btn.addEventListener('click', () => { location.href = '/cards/day?date=' + iso(addDays(parseIso(selIso), Number(btn.getAttribute('data-day-nav') || 0))); }));
    const picker = root.querySelector('[data-date-picker]');
    if (picker) picker.addEventListener('change', () => { if (picker.value) location.href = '/cards/day?date=' + picker.value; });
  }

  async function render() {
    injectStyles();
    document.body.classList.add('dynamic-routines-active');
    const cards = alpineCards();
    if (!cards.length) return;
    const sel = selectedIso();
    const items = catalogFrom(cards);
    const hist = await loadHistory(sel, items);
    const dailyRows = [];
    const flexRows = [];
    items.forEach((item) => {
      if (isDaily(item.freq)) {
        dailyItems(item, sel).forEach((row) => dailyRows.push(row));
        return;
      }
      const st = flexState(item, hist, sel);
      flexRows.push({ item, isDaily: false, name: item.name, areaName: item.areaName, status: st.status, label: st.label, sort: st.sort, dueIso: st.dueIso });
    });
    dailyRows.sort((a, b) => ['Morning', 'Midday', 'Evening'].indexOf(a.bucket) - ['Morning', 'Midday', 'Evening'].indexOf(b.bucket) || a.sort - b.sort || a.item.configured - b.item.configured || a.dot - b.dot);
    flexRows.sort((a, b) => a.sort - b.sort || (a.dueIso || '9999').localeCompare(b.dueIso || '9999') || a.item.configured - b.item.configured);

    let mount = document.getElementById('dynamic-routine-app');
    if (!mount) {
      mount = document.createElement('div');
      mount.id = 'dynamic-routine-app';
      const header = document.querySelector('.page-header');
      header.parentNode.insertBefore(mount, header.nextSibling);
    }
    const overdue = flexRows.filter((r) => r.status === 'overdue');
    const due = flexRows.filter((r) => r.status === 'due');
    const upcoming = flexRows.filter((r) => r.status === 'upcoming');
    const future = flexRows.filter((r) => r.status === 'future');
    const flexDone = flexRows.filter((r) => r.status === 'done');
    const dailyDoneCount = dailyRows.filter((r) => r.status === 'done').length;
    const refs = [];
    let html = '<div class="eff-columns"><div class="eff-column eff-daily-column"><section class="card eff-column-title"><h3>Daily checklist</h3><p>Fast, ordered, duplicate-friendly daily dots.</p></section>';
    ['Morning', 'Midday', 'Evening'].forEach((bucket) => { html += sectionHtml(bucket, dailyRows.filter((r) => r.bucket === bucket), refs); });
    if (!dailyRows.length) html += '<div class="card eff-empty">No daily tasks for this day.</div>';
    html += '<section class="card eff-add-card"><button type="button" class="btn btn-primary btn-sm" id="eff-add-daily">Add daily</button><p class="eff-hint">Adds a daily task to your routine list.</p></section></div>';
    html += '<div class="eff-column eff-flex-column"><section class="card eff-column-title"><h3>Recurring</h3><p>Based on last completion + interval. Done today means not due again until the interval passes.</p></section>';
    html += sectionHtml('Overdue', overdue, refs) + sectionHtml('Due Today', due, refs) + sectionHtml('Coming Up', upcoming, refs) + sectionHtml('Later', future, refs) + sectionHtml('Done Today', flexDone, refs);
    if (!flexRows.length) html += '<div class="card eff-empty">No recurring tasks yet.</div>';
    html += '<section class="card eff-add-card"><button type="button" class="btn btn-primary btn-sm" id="eff-add-recurring">Add recurring</button><p class="eff-hint">Example: Mow lawn every 7 days.</p></section></div></div>';
    html += navHtml(sel);
    html += '<div class="eff-summary"><span data-daily-done-count>' + dailyDoneCount + '/' + dailyRows.length + ' daily done</span><span>' + overdue.length + ' overdue</span><span>' + due.length + ' due today</span><span>' + upcoming.length + ' coming up</span></div>';
    mount.innerHTML = html;
    mount.querySelector('#eff-add-daily')?.addEventListener('click', () => openAddSheet(cards, 'daily'));
    mount.querySelector('#eff-add-recurring')?.addEventListener('click', () => openAddSheet(cards, 'recurring'));
    wireNav(mount, sel);
    mount.querySelectorAll('[data-eff-idx]').forEach((btn) => {
      const row = refs[Number(btn.getAttribute('data-eff-idx'))];
      if (!row) return;
      bindLongPress(btn, row);
      btn.addEventListener('click', async () => {
        if (!row.item) return;
        btn.disabled = true;
        try {
          if (row.isDaily) {
            const done = await saveDot(row.item, sel, row.dot);
            btn.disabled = false;
            updateDailyButton(btn, row, done);
          } else {
            await saveDot(row.item, sel, row.dot);
            render();
          }
        } catch (err) {
          console.error(err);
          btn.disabled = false;
          btn.classList.add('save-error');
        }
      });
    });
  }

  function schedule() { setTimeout(render, 120); }
  window.__lmBindRoutineEditButton = bindLongPress;
  window.addEventListener('load', schedule);
  document.addEventListener('alpine:initialized', schedule);
  if (document.readyState !== 'loading') schedule();
})();
