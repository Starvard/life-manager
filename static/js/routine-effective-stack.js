(function () {
  if (!location.pathname.startsWith('/cards')) return;

  const MS_DAY = 86400000;
  const TZ = 'America/New_York';
  const CACHE = new Map();
  const HIST_CACHE = new Map();
  const SECTION_KEY = 'lm:routine-section:';

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
    const inp = document.querySelector('.picker-date');
    return inp && inp.value ? inp.value : todayIso();
  }
  function dayIndex(dateIso, weekStartIso) { return Math.max(0, Math.min(6, daysBetween(dateIso, weekStartIso))); }
  function dateLabel(dateIso, long) { return parseIso(dateIso).toLocaleDateString('en-US', long ? { weekday: 'long', month: 'long', day: 'numeric', timeZone: 'UTC' } : { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC' }); }
  function esc(s) { return String(s || '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function intervalDays(freq) {
    const f = Number(freq || 0);
    if (f <= 0) return 9999;
    if (f >= 7) return 1;
    return Math.max(1, Math.round(7 / f));
  }
  function freqFromEveryDays(days) {
    const d = Number(days || 0);
    if (!Number.isFinite(d) || d <= 0) return 1;
    return Number((7 / d).toFixed(3));
  }
  function isDaily(freq) { return Number(freq || 0) >= 7; }
  function keyOf(areaKey, name) { return areaKey + '::' + name; }

  function dailyBucket(name, dot, total, areaKey) {
    const sectionOverride = localStorage.getItem(SECTION_KEY + areaKey + '::' + name);
    if (sectionOverride) return sectionOverride;
    const n = String(name || '').toLowerCase();
    if (n.includes('brush') || n.includes('floss')) return dot === 0 ? 'Morning' : 'Evening';
    if (n.includes('water')) {
      if (dot === 0) return 'Morning';
      if (dot >= Math.max(1, total - 2)) return 'Evening';
      return 'Midday';
    }
    if (n.includes('coffee') || n.includes('breakfast') || n.includes('vitamin') || n.includes('med') || n.includes('morning')) return 'Morning';
    if (n.includes('dinner') || n.includes('evening') || n.includes('bed') || n.includes('trash') || n.includes('dish')) return 'Evening';
    return 'Midday';
  }

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
      .eff-secondary { margin-top:1.25rem; padding-top:1rem; border-top:1px solid rgba(148,163,184,.12); }
      .eff-hero-compact { padding:.75rem 1rem; margin-bottom:.35rem; }
      .eff-hero-compact .eff-date { margin:0 0 .35rem; font-weight:700; color:var(--text-muted); }
      .eff-sub-tight { margin:0; color:var(--text-muted); line-height:1.35; font-size:.78rem; max-width:42rem; }
      .eff-secondary .eff-summary { margin:.45rem 0 .55rem; }
      .eff-secondary .eff-recent { margin:.35rem 0 .55rem; }
      .eff-hero { display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; padding:1rem; margin-bottom:.8rem; }
      .eff-hero h2 { margin:.1rem 0 .25rem; font-size:1.25rem; }
      .eff-eyebrow { margin:0; text-transform:uppercase; letter-spacing:.08em; font-size:.72rem; color:var(--text-muted); font-weight:800; }
      .eff-date { margin:0 0 .1rem; color:var(--text-muted); font-weight:700; }
      .eff-sub { margin:0; color:var(--text-muted); line-height:1.35; max-width:48rem; }
      .eff-actions { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:.45rem; }
      .eff-summary { display:flex; gap:.5rem; flex-wrap:wrap; margin:.65rem 0 1rem; }
      .eff-summary span { border:1px solid rgba(148,163,184,.2); border-radius:999px; padding:.35rem .65rem; background:rgba(255,255,255,.04); font-size:.82rem; color:var(--text-muted); }
      .eff-columns { display:grid; grid-template-columns:minmax(280px, .95fr) minmax(320px, 1.35fr); gap:.9rem; align-items:start; }
      .eff-column { display:grid; gap:.85rem; }
      .eff-column-title { padding:.9rem 1rem; }
      .eff-column-title h3 { margin:0 0 .2rem; font-size:1rem; }
      .eff-column-title p { margin:0; color:var(--text-muted); font-size:.78rem; line-height:1.35; }
      .eff-section { padding:.9rem; }
      .eff-section h3 { margin:0 0 .65rem; display:flex; justify-content:space-between; gap:.75rem; font-size:1rem; }
      .eff-section h3 small { color:var(--text-muted); font-weight:500; }
      .eff-task { width:100%; display:flex; align-items:center; gap:.7rem; border:1px solid rgba(148,163,184,.18); border-left-width:5px; border-radius:.9rem; padding:.72rem .75rem; margin:.45rem 0; background:rgba(255,255,255,.035); color:inherit; text-align:left; cursor:pointer; }
      .eff-task:hover { background:rgba(255,255,255,.06); }
      .eff-task.overdue { border-color:rgba(248,113,113,.48); border-left-color:rgba(248,113,113,1); background:rgba(248,113,113,.11); }
      .eff-task.due { border-left-color:rgba(250,204,21,.95); background:rgba(250,204,21,.07); }
      .eff-task.daily { border-left-color:rgba(99,179,255,.8); }
      .eff-task.upcoming { border-left-color:rgba(148,163,184,.65); opacity:.94; }
      .eff-task.done { border-left-color:rgba(134,239,172,.9); background:rgba(134,239,172,.07); }
      .eff-task.done strong { text-decoration:line-through; opacity:.72; }
      .eff-task strong { display:block; font-size:.95rem; }
      .eff-task small { display:block; color:var(--text-muted); margin-top:.15rem; }
      .eff-check { display:grid; place-items:center; flex:0 0 1.6rem; width:1.6rem; height:1.6rem; border-radius:999px; background:rgba(255,255,255,.06); font-weight:900; }
      .eff-task.overdue .eff-check { background:rgba(248,113,113,.2); color:#fecaca; }
      .eff-task.done .eff-check { background:rgba(134,239,172,.16); color:#bbf7d0; }
      .eff-empty { padding:1rem; color:var(--text-muted); }
      .eff-recent { display:flex; flex-wrap:wrap; gap:.4rem; margin:.35rem 0 1rem; }
      .eff-recent a { border:1px solid rgba(148,163,184,.2); border-radius:999px; padding:.35rem .6rem; background:rgba(255,255,255,.035); color:inherit; text-decoration:none; font-size:.82rem; }
      .eff-add-card { padding:.75rem; display:flex; gap:.5rem; flex-wrap:wrap; }
      .eff-hint { color:var(--text-muted); font-size:.72rem; margin:.35rem 0 0; }
      .lm-sheet-backdrop { position:fixed; inset:0; z-index:10000; background:rgba(0,0,0,.48); display:flex; align-items:flex-end; justify-content:center; padding:.75rem; }
      .lm-edit-sheet { width:min(480px,100%); border:1px solid rgba(148,163,184,.25); border-radius:1.05rem; background:rgb(15,23,42); box-shadow:0 28px 90px rgba(0,0,0,.48); padding:.95rem; }
      .lm-edit-sheet h3 { margin:0 0 .25rem; font-size:1rem; }
      .lm-edit-sheet p { margin:0 0 .75rem; color:var(--text-muted); font-size:.8rem; line-height:1.35; }
      .lm-edit-grid { display:grid; gap:.55rem; }
      .lm-edit-grid label { display:grid; gap:.22rem; font-size:.76rem; color:var(--text-muted); font-weight:700; }
      .lm-edit-grid input,.lm-edit-grid select { width:100%; border:1px solid var(--border); border-radius:.65rem; padding:.62rem .65rem; background:rgba(255,255,255,.055); color:var(--text); }
      .lm-edit-actions { display:flex; gap:.45rem; justify-content:space-between; margin-top:.85rem; }
      .lm-edit-actions .right { margin-left:auto; display:flex; gap:.45rem; }
      @media(max-width:840px){.eff-columns{grid-template-columns:1fr}.eff-hero{display:block}.eff-actions{justify-content:flex-start;margin-top:.75rem}.eff-task{padding:.82rem .78rem}}
    `;
    document.head.appendChild(style);
  }

  async function fetchWeek(wk) {
    if (CACHE.has(wk)) return CACHE.get(wk);
    const p = fetch('/api/routine-cards/' + encodeURIComponent(wk))
      .then((r) => r.ok ? r.json() : { areas: {} })
      .then((data) => data.areas || {})
      .catch(() => ({}));
    CACHE.set(wk, p);
    return p;
  }

  function alpineCards() {
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

  function catalogFrom(cards) {
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
    if (!areaKey || !card.week_start) return;
    (card.tasks || []).forEach((task) => {
      const key = keyOf(areaKey, task.name);
      (task.days || []).forEach((row, di) => {
        if ((row || []).some(Boolean)) {
          if (!hist[key]) hist[key] = [];
          hist[key].push(iso(addDays(parseIso(card.week_start), di)));
        }
      });
    });
  }

  async function loadHistory(selIso) {
    if (HIST_CACHE.has(selIso)) return HIST_CACHE.get(selIso);
    const promise = (async () => {
      const sel = parseIso(selIso);
      const start = addDays(mondayFor(sel), -16 * 7);
      const end = addDays(mondayFor(sel), 4 * 7);
      const weeks = new Set();
      for (let d = new Date(start); d <= end; d = addDays(d, 7)) weeks.add(weekKeyFor(d));
      const hist = {};
      await Promise.all(Array.from(weeks).map(async (wk) => {
        const areas = await fetchWeek(wk);
        Object.values(areas || {}).forEach((card) => addHistoryFromCard(card, hist));
      }));
      alpineCards().forEach((card) => addHistoryFromCard(card, hist));
      Object.keys(hist).forEach((k) => { hist[k] = Array.from(new Set(hist[k])).sort(); });
      return hist;
    })();
    HIST_CACHE.set(selIso, promise);
    return promise;
  }

  function scheduledDates(item) {
    const out = [];
    const start = parseIso(item.card.week_start);
    (item.task.scheduled || []).forEach((n, di) => {
      if (Number(n || 0) > 0) out.push(iso(addDays(start, di)));
    });
    return out.sort();
  }

  function stateForFlexible(item, hist, selIso) {
    const key = keyOf(item.areaKey, item.name);
    const completions = (hist[key] || []).filter((d) => d <= selIso).sort();
    const completedToday = completions.includes(selIso);
    const last = completions.length ? completions[completions.length - 1] : null;
    const interval = intervalDays(item.freq);
    let dueIso = null;
    if (last) {
      dueIso = iso(addDays(parseIso(last), interval));
    } else {
      const sched = scheduledDates(item);
      dueIso = sched.find((d) => d >= selIso) || sched.filter((d) => d <= selIso).pop() || selIso;
    }
    if (completedToday) return { kind: 'done', dueIso, completedToday, interval };
    const delta = daysBetween(selIso, dueIso);
    if (delta >= 0) return { kind: delta > 0 ? 'overdue' : 'due', dueIso, overdueDays: delta, interval };
    if (delta >= -7) return { kind: 'upcoming', dueIso, inDays: -delta, interval };
    return { kind: 'future', dueIso, inDays: -delta, interval };
  }

  function dailyItems(item, selIso) {
    const di = dayIndex(selIso, item.card.week_start);
    const row = (item.task.days || [])[di] || [];
    const freqCount = Math.max(1, Math.round(Number(item.task.freq || 7) / 7));
    const scheduledMax = Math.max(0, ...((item.task.scheduled || []).map((n) => Number(n || 0))));
    const rowMax = Math.max(0, ...((item.task.days || []).map((drow) => (Array.isArray(drow) ? drow.length : 0))));
    const count = Math.max(1, freqCount, scheduledMax, rowMax);
    const out = [];
    for (let dot = 0; dot < count; dot++) {
      const done = !!row[dot];
      const bucket = dailyBucket(item.name, dot, count, item.areaKey);
      out.push({ item, dot, bucket, status: done ? 'done' : 'daily', label: done ? 'Done today' : 'Due today' });
    }
    return out;
  }

  async function saveDot(item, selIso, dotHint) {
    const di = dayIndex(selIso, item.card.week_start);
    if (!item.task.days[di]) item.task.days[di] = [false];
    let dot = Number.isInteger(dotHint) ? dotHint : item.task.days[di].findIndex((v) => !v);
    if (dot < 0) dot = item.task.days[di].length;
    while (item.task.days[di].length <= dot) item.task.days[di].push(false);
    const next = !item.task.days[di][dot];
    item.task.days[di][dot] = next;
    await fetch('/api/routine-cards/' + item.card.week_key + '/' + item.areaKey + '/set-dot', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: item.taskIndex, day: di, dot, value: next, list: 'tasks' }),
    });
    CACHE.clear();
    HIST_CACHE.clear();
    return next;
  }

  function updateDailyButton(btn, row, done) {
    row.status = done ? 'done' : 'daily';
    row.label = done ? 'Done today' : 'Due today';
    btn.classList.toggle('done', done);
    btn.classList.toggle('daily', !done);
    const check = btn.querySelector('.eff-check');
    const small = btn.querySelector('small');
    if (check) check.textContent = done ? '✓' : '○';
    if (small) small.textContent = row.label + ' · ' + row.areaName;
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
    const nameEl = doc.querySelector('[name="task_name_' + CSS.escape(area) + '_' + idx + '"]');
    const freqEl = doc.querySelector('[name="task_freq_' + CSS.escape(area) + '_' + idx + '"]');
    const fpyEl = doc.querySelector('[name="task_fpy_' + CSS.escape(area) + '_' + idx + '"]');
    const delEl = doc.querySelector('[name="task_delete_' + CSS.escape(area) + '_' + idx + '"]');
    if (!nameEl) throw new Error('Could not find task in manage form.');
    if (vals.deleteTask) {
      if (delEl) delEl.checked = true;
    } else {
      nameEl.value = vals.name || row.name;
      if (fpyEl) fpyEl.value = '';
      if (freqEl) freqEl.value = freqInputValue(vals.freq, vals.everyDays);
      if (vals.section && isDaily(freqEl ? Number(freqEl.value) : row.item.freq)) {
        localStorage.setItem(SECTION_KEY + area + '::' + nameEl.value, vals.section);
      }
    }
    await submitManageForm(doc);
  }

  async function addRoutineTask(vals) {
    const doc = await getManageFormDoc();
    const area = vals.areaKey;
    const nameEl = doc.querySelector('[name="new_task_name_' + CSS.escape(area) + '"]');
    const freqEl = doc.querySelector('[name="new_task_freq_' + CSS.escape(area) + '"]');
    const fpyEl = doc.querySelector('[name="new_task_fpy_' + CSS.escape(area) + '"]');
    if (!nameEl || !freqEl) throw new Error('Could not find add-task fields.');
    nameEl.value = vals.name || 'New task';
    if (fpyEl) fpyEl.value = '';
    freqEl.value = freqInputValue(vals.freq, vals.everyDays);
    if (vals.section && Number(freqEl.value) >= 7) {
      localStorage.setItem(SECTION_KEY + area + '::' + nameEl.value, vals.section);
    }
    await submitManageForm(doc);
  }

  function closeSheet() { document.querySelector('.lm-sheet-backdrop')?.remove(); }

  function areaOptions(cards, selected) {
    const seen = new Set();
    return cards.map((c) => ({ key: c.area_key || '', name: c.area_name || c.area_key || '' }))
      .filter((a) => a.key && !seen.has(a.key) && seen.add(a.key))
      .map((a) => '<option value="' + esc(a.key) + '"' + (a.key === selected ? ' selected' : '') + '>' + esc(a.name) + '</option>').join('');
  }

  function openAddSheet(cards) {
    closeSheet();
    const firstArea = (cards[0] && cards[0].area_key) || '';
    const wrap = document.createElement('div');
    wrap.className = 'lm-sheet-backdrop';
    wrap.innerHTML = '<div class="lm-edit-sheet" role="dialog" aria-modal="true"><h3>Add routine task</h3><p>Adds to your saved routine list (same as long-press edit).</p><div class="lm-edit-grid">' +
      '<label>Area<select id="lm-add-area">' + areaOptions(cards, firstArea) + '</select></label>' +
      '<label>Name<input id="lm-add-name" type="text" placeholder="Freeze milk"></label>' +
      '<label>Type<select id="lm-add-type"><option value="daily">Daily</option><option value="every">Every N days</option><option value="freq">Times per week</option></select></label>' +
      '<label id="lm-add-days-wrap" style="display:none">Every N days<input id="lm-add-days" type="number" min="1" step="1" value="3"></label>' +
      '<label id="lm-add-freq-wrap" style="display:none">Frequency per week<input id="lm-add-freq" type="number" min="0" step="0.01" value="1"></label>' +
      '<label id="lm-add-section-wrap">Daily section<select id="lm-add-section"><option>Morning</option><option selected>Midday</option><option>Evening</option></select></label>' +
      '</div><div class="lm-edit-actions"><button type="button" class="btn btn-secondary btn-sm" data-action="cancel">Cancel</button><span class="right"><button type="button" class="btn btn-primary btn-sm" data-action="save">Add</button></span></div></div>';
    const typeChanged = () => {
      const t = wrap.querySelector('#lm-add-type')?.value || 'daily';
      wrap.querySelector('#lm-add-days-wrap').style.display = t === 'every' ? '' : 'none';
      wrap.querySelector('#lm-add-freq-wrap').style.display = t === 'freq' ? '' : 'none';
      wrap.querySelector('#lm-add-section-wrap').style.display = t === 'daily' ? '' : 'none';
    };
    wrap.addEventListener('change', (e) => { if (e.target && e.target.id === 'lm-add-type') typeChanged(); });
    wrap.addEventListener('click', async (e) => {
      if (e.target === wrap) closeSheet();
      const action = e.target.closest('[data-action]')?.getAttribute('data-action');
      if (!action) return;
      if (action === 'cancel') { closeSheet(); return; }
      const type = wrap.querySelector('#lm-add-type').value;
      const vals = {
        areaKey: wrap.querySelector('#lm-add-area').value,
        name: wrap.querySelector('#lm-add-name').value.trim(),
        freq: type === 'daily' ? 7 : wrap.querySelector('#lm-add-freq').value,
        everyDays: type === 'every' ? wrap.querySelector('#lm-add-days').value : '',
        section: type === 'daily' ? wrap.querySelector('#lm-add-section').value : '',
      };
      if (!vals.name) return;
      await addRoutineTask(vals);
      location.reload();
    });
    document.body.appendChild(wrap);
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
    const syncType = () => {
      const type = wrap.querySelector('#lm-edit-type')?.value || 'daily';
      wrap.querySelector('#lm-edit-days-wrap').style.display = type === 'every' ? '' : 'none';
      wrap.querySelector('#lm-edit-freq-wrap').style.display = type === 'freq' ? '' : 'none';
      wrap.querySelector('#lm-edit-section-wrap').style.display = type === 'daily' ? '' : 'none';
    };
    wrap.addEventListener('change', (e) => { if (e.target && e.target.id === 'lm-edit-type') syncType(); });
    wrap.addEventListener('click', async (e) => {
      if (e.target === wrap) closeSheet();
      const action = e.target.closest('[data-action]')?.getAttribute('data-action');
      if (!action) return;
      if (action === 'cancel') { closeSheet(); return; }
      if (action === 'delete' && !confirm('Delete ' + item.name + '?')) return;
      const type = wrap.querySelector('#lm-edit-type').value;
      await saveRoutineEdit(row, {
        deleteTask: action === 'delete',
        name: wrap.querySelector('#lm-edit-name').value.trim(),
        freq: type === 'daily' ? 7 : wrap.querySelector('#lm-edit-freq').value,
        everyDays: type === 'every' ? wrap.querySelector('#lm-edit-days').value : '',
        section: type === 'daily' ? wrap.querySelector('#lm-edit-section').value : '',
      });
      location.reload();
    });
    document.body.appendChild(wrap);
    const section = wrap.querySelector('#lm-edit-section');
    if (section) section.value = currentSection;
    syncType();
  }

  function bindLongPress(btn, row) {
    let timer = null;
    let fired = false;
    btn.addEventListener('pointerdown', () => {
      fired = false;
      clearTimeout(timer);
      timer = setTimeout(() => { fired = true; openEditSheet(row); }, 650);
    });
    ['pointerup', 'pointercancel', 'pointerleave'].forEach((ev) => btn.addEventListener(ev, () => clearTimeout(timer)));
    btn.addEventListener('contextmenu', (e) => { e.preventDefault(); openEditSheet(row); });
    btn.addEventListener('click', (e) => {
      if (fired) {
        e.preventDefault();
        e.stopPropagation();
        fired = false;
      }
    }, true);
  }

  function taskButton(row, idx) {
    const status = row.status;
    const icon = status === 'done' ? '✓' : status === 'overdue' ? '!' : '○';
    const label = row.label || '';
    const kind = row.isDaily ? 'daily' : 'flex';
    return '<button type="button" class="eff-task ' + esc(status) + '" data-eff-idx="' + idx + '" data-row-kind="' + kind + '"><span class="eff-check">' + icon + '</span><span><strong>' + esc(row.name) + '</strong><small>' + esc(label + ' · ' + row.areaName) + '</small></span></button>';
  }

  function recentLinks(sel) {
    const base = parseIso(sel);
    const links = ['<a href="/cards">Today</a>'];
    for (let i = 1; i <= 7; i++) {
      const d = iso(addDays(base, -i));
      links.push('<a href="/cards/day?date=' + d + '">' + (i === 1 ? 'Yesterday' : i + ' days ago') + '</a>');
    }
    return '<div class="eff-recent">' + links.join('') + '</div>';
  }

  function sectionHtml(title, list, rowRefs) {
    if (!list.length) return '';
    let html = '<section class="card eff-section"><h3><span>' + esc(title) + '</span><small>' + list.length + '</small></h3>';
    list.forEach((r) => { rowRefs.push(r); html += taskButton(r, rowRefs.length - 1); });
    html += '</section>';
    return html;
  }

  async function render() {
    injectStyles();
    document.body.classList.add('dynamic-routines-active');
    const cards = alpineCards();
    if (!cards.length) return;
    const selIso = selectedIso();
    const hist = await loadHistory(selIso);
    const dailyRows = [];
    const flexRows = [];

    catalogFrom(cards).forEach((item) => {
      if (isDaily(item.freq)) {
        dailyItems(item, selIso).forEach((x) => dailyRows.push({ ...x, isDaily: true, name: item.name, areaName: item.areaName, sort: x.status === 'done' ? 90 : 20 }));
        return;
      }
      const st = stateForFlexible(item, hist, selIso);
      if (st.kind === 'future') return;
      let label = '';
      let sort = 50;
      if (st.kind === 'done') { label = 'Done today · next due ' + dateLabel(st.dueIso, false); sort = 90; }
      else if (st.kind === 'overdue') { label = st.overdueDays + ' day' + (st.overdueDays === 1 ? '' : 's') + ' overdue · due ' + dateLabel(st.dueIso, false); sort = 1; }
      else if (st.kind === 'due') { label = 'Due today'; sort = 10; }
      else if (st.kind === 'upcoming') { label = 'Due ' + dateLabel(st.dueIso, false) + ' · tap if done today'; sort = 70; }
      flexRows.push({ item, isDaily: false, name: item.name, areaName: item.areaName, status: st.kind, label, sort, dueIso: st.dueIso });
    });

    dailyRows.sort((a, b) => ['Morning', 'Midday', 'Evening'].indexOf(a.bucket) - ['Morning', 'Midday', 'Evening'].indexOf(b.bucket) || a.sort - b.sort || a.name.localeCompare(b.name));
    flexRows.sort((a, b) => a.sort - b.sort || a.areaName.localeCompare(b.areaName) || a.name.localeCompare(b.name));

    let mount = document.getElementById('dynamic-routine-app');
    if (!mount) {
      mount = document.createElement('div');
      mount.id = 'dynamic-routine-app';
      const header = document.querySelector('.page-header');
      header.parentNode.insertBefore(mount, header.nextSibling);
    }

    const today = selIso === todayIso();
    const overdue = flexRows.filter((r) => r.status === 'overdue');
    const due = flexRows.filter((r) => r.status === 'due');
    const upcoming = flexRows.filter((r) => r.status === 'upcoming');
    const flexDone = flexRows.filter((r) => r.status === 'done');
    const dailyDoneCount = dailyRows.filter((r) => r.status === 'done').length;

    const rowRefs = [];
    let html = '<div class="eff-columns">';
    html += '<div class="eff-column eff-daily-column"><section class="card eff-column-title"><h3>Daily checklist</h3><p>Organized by time of day. Long-press to edit.</p></section>';
    ['Morning', 'Midday', 'Evening'].forEach((bucket) => {
      html += sectionHtml(bucket, dailyRows.filter((r) => r.bucket === bucket), rowRefs);
    });
    if (!dailyRows.length) html += '<div class="card eff-empty">No daily tasks for this day.</div>';
    html += '<section class="card eff-add-card"><button type="button" class="btn btn-primary btn-sm" id="eff-add-daily">Add daily</button><p class="eff-hint">Adds a daily task to your routine list.</p></section>';
    html += '</div>';

    html += '<div class="eff-column eff-flex-column"><section class="card eff-column-title"><h3>Recurring due dates</h3><p>These use last completion + interval. Long-press to edit frequency or delete.</p></section>';
    html += sectionHtml('Overdue', overdue, rowRefs);
    html += sectionHtml('Due Today', due, rowRefs);
    html += sectionHtml('Coming Up', upcoming, rowRefs);
    html += sectionHtml('Done Today', flexDone, rowRefs);
    if (!flexRows.length) html += '<div class="card eff-empty">No recurring due-date tasks active right now.</div>';
    html += '<section class="card eff-add-card"><button type="button" class="btn btn-primary btn-sm" id="eff-add-recurring">Add recurring</button><p class="eff-hint">Example: Freeze milk every 3 days.</p></section>';
    html += '</div></div>';

    html += '<div class="eff-secondary">';
    html += '<section class="card eff-hero eff-hero-compact"><p class="eff-date">' + esc(dateLabel(selIso, true)) + (today ? ' · Today' : '') + '</p><p class="eff-sub eff-sub-tight">Tap to complete. Long-press a task to rename, change how often it runs, or remove it.</p></section>';
    html += recentLinks(selIso);
    html += '<div class="eff-summary"><span data-daily-done-count>' + dailyDoneCount + '/' + dailyRows.length + ' daily done</span><span>' + overdue.length + ' overdue</span><span>' + due.length + ' due today</span><span>' + upcoming.length + ' coming up</span></div>';
    html += '</div>';

    mount.innerHTML = html;
    mount.querySelector('#eff-add-daily')?.addEventListener('click', () => openAddSheet(cards));
    mount.querySelector('#eff-add-recurring')?.addEventListener('click', () => openAddSheet(cards));
    mount.querySelectorAll('[data-eff-idx]').forEach((btn) => {
      const r = rowRefs[Number(btn.getAttribute('data-eff-idx'))];
      if (r) bindLongPress(btn, r);
      btn.addEventListener('click', async () => {
        const r = rowRefs[Number(btn.getAttribute('data-eff-idx'))];
        if (!r || !r.item) return;
        if (r.isDaily) {
          const done = await saveDot(r.item, selIso, r.dot);
          updateDailyButton(btn, r, done);
        } else {
          await saveDot(r.item, selIso, r.dot);
          setTimeout(() => location.reload(), 80);
        }
      });
    });
  }

  window.__lmBindRoutineEditButton = bindLongPress;

  function schedule() { setTimeout(render, 180); }
  window.addEventListener('load', schedule);
  document.addEventListener('alpine:initialized', schedule);
})();
