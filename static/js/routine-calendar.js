(function () {
  const params = new URLSearchParams(location.search);
  if (location.pathname !== '/routines' || params.get('view') !== 'calendar') return;

  const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const AREA_CLASS_PREFIX = 'cal-area-';

  function parseIso(s) { return new Date(String(s).slice(0, 10) + 'T00:00:00'); }
  function iso(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
  }
  function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
  function monthKey(d) { return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0'); }
  function monthLabel(d) { return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }); }
  function weekKeyFor(d) {
    const x = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    const day = x.getUTCDay() || 7;
    x.setUTCDate(x.getUTCDate() + 4 - day);
    const yearStart = new Date(Date.UTC(x.getUTCFullYear(), 0, 1));
    const week = Math.ceil((((x - yearStart) / 86400000) + 1) / 7);
    return x.getUTCFullYear() + '-W' + String(week).padStart(2, '0');
  }
  function mondayFor(d) { const x = new Date(d); const n = (x.getDay() + 6) % 7; x.setDate(x.getDate() - n); return x; }
  function esc(s) { return String(s || '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

  function injectStyles() {
    if (document.getElementById('routine-calendar-styles')) return;
    const style = document.createElement('style');
    style.id = 'routine-calendar-styles';
    style.textContent = `
      .routine-calendar-shell { display:grid; gap:.85rem; }
      .cal-hero { display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; padding:1rem; }
      .cal-hero h1 { margin:0; font-size:1.45rem; }
      .cal-hero p { margin:.25rem 0 0; color:var(--text-muted); font-size:.86rem; max-width:46rem; }
      .cal-actions { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:.45rem; }
      .cal-toolbar { display:flex; align-items:center; justify-content:space-between; gap:.75rem; padding:.75rem; }
      .cal-toolbar h2 { margin:0; font-size:1.05rem; }
      .cal-nav { display:flex; gap:.4rem; flex-wrap:wrap; }
      .cal-grid { display:grid; grid-template-columns:repeat(7, minmax(0, 1fr)); gap:.5rem; }
      .cal-dow { color:var(--text-muted); font-size:.68rem; font-weight:800; letter-spacing:.06em; text-transform:uppercase; padding:0 .25rem; }
      .cal-day { min-height:7.3rem; padding:.45rem; border:1px solid var(--border); border-radius:var(--radius-sm); background:var(--surface); overflow:hidden; }
      .cal-day.is-other { opacity:.42; }
      .cal-day.is-today { border-color:rgba(99,179,255,.45); box-shadow:0 0 0 1px rgba(99,179,255,.14), 0 0 16px rgba(99,179,255,.08); }
      .cal-date-row { display:flex; align-items:center; justify-content:space-between; gap:.25rem; margin-bottom:.32rem; }
      .cal-date-num { font-size:.82rem; font-weight:800; color:var(--text-bright); }
      .cal-count { font-size:.62rem; color:var(--text-muted); }
      .cal-tasks { display:flex; flex-direction:column; gap:.18rem; }
      .cal-task { width:100%; border:0; border-radius:.42rem; padding:.18rem .28rem; background:rgba(255,255,255,.055); color:var(--text); text-align:left; font:inherit; font-size:.64rem; line-height:1.13; cursor:pointer; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
      .cal-task:hover { background:rgba(99,179,255,.14); }
      .cal-task.done { text-decoration:line-through; opacity:.55; }
      .cal-task.overdue { background:rgba(251,146,60,.16); }
      .cal-task.extra { outline:1px dashed rgba(148,163,184,.32); }
      .cal-empty { color:var(--text-light); font-size:.64rem; padding-top:.2rem; }
      .cal-more { color:var(--text-muted); font-size:.62rem; margin-top:.12rem; }
      .cal-legend { display:flex; flex-wrap:wrap; gap:.45rem; color:var(--text-muted); font-size:.72rem; padding:.65rem .75rem; }
      .cal-legend span { border:1px solid var(--border); border-radius:999px; padding:.25rem .5rem; background:rgba(255,255,255,.035); }
      .cal-loading { padding:1rem; color:var(--text-muted); }
      @media (max-width:760px) {
        .cal-grid { gap:.3rem; }
        .cal-day { min-height:5.8rem; padding:.32rem; }
        .cal-task { font-size:.57rem; padding:.14rem .22rem; }
        .cal-dow { font-size:.58rem; }
        .cal-hero { display:block; }
        .cal-actions { justify-content:flex-start; margin-top:.7rem; }
      }
    `;
    document.head.appendChild(style);
  }

  function replacePageShell() {
    injectStyles();
    const main = document.querySelector('.main-content');
    if (!main) return null;
    main.innerHTML = `
      <div class="routine-calendar-shell">
        <section class="card cal-hero">
          <div>
            <h1>Routine Calendar</h1>
            <p>Live month view of what is due each day. Tap a task to mark that exact day done or undone. The month re-renders immediately after each change.</p>
          </div>
          <div class="cal-actions">
            <a class="btn btn-secondary btn-sm" href="/cards">Today Stack</a>
            <a class="btn btn-secondary btn-sm" href="/routines">Manage Routines</a>
          </div>
        </section>
        <section class="card cal-toolbar">
          <div class="cal-nav">
            <button type="button" class="btn btn-secondary btn-sm" id="cal-prev">← Month</button>
            <button type="button" class="btn btn-secondary btn-sm" id="cal-today">Today</button>
            <button type="button" class="btn btn-secondary btn-sm" id="cal-next">Month →</button>
          </div>
          <h2 id="cal-title"></h2>
        </section>
        <section class="cal-legend card">
          <span>Shown tight so you can scan the month</span>
          <span>Tap = done / undo</span>
          <span>Orange = overdue relative to viewed day</span>
        </section>
        <div id="cal-mount" class="cal-loading">Loading calendar…</div>
      </div>`;
    return main;
  }

  const state = {
    current: parseIso((params.get('month') || new Date().toISOString().slice(0, 7)) + '-01'),
    weekCache: new Map(),
  };

  async function fetchWeek(wk) {
    if (state.weekCache.has(wk)) return state.weekCache.get(wk);
    const p = fetch('/api/routine-cards/' + encodeURIComponent(wk))
      .then((r) => r.json())
      .then((data) => data.areas || {});
    state.weekCache.set(wk, p);
    return p;
  }

  async function weeksForRange(start, end) {
    const weeks = new Set();
    for (let d = new Date(start); d <= end; d = addDays(d, 1)) weeks.add(weekKeyFor(d));
    const out = {};
    await Promise.all(Array.from(weeks).map(async (wk) => { out[wk] = await fetchWeek(wk); }));
    return out;
  }

  function itemsForDay(cardsByWeek, day) {
    const wk = weekKeyFor(day);
    const cards = cardsByWeek[wk] || {};
    const monday = mondayFor(day);
    const di = Math.round((day - monday) / 86400000);
    const today = new Date(); today.setHours(0,0,0,0);
    const out = [];
    Object.entries(cards).forEach(([areaKey, card]) => {
      const all = [];
      (card.tasks || []).forEach((task, taskIndex) => all.push({ task, taskIndex, list: 'tasks', areaKey, areaName: card.area_name || areaKey, weekKey: card.week_key }));
      (card.extra_tasks || []).forEach((task, taskIndex) => all.push({ task, taskIndex, list: 'extra_tasks', areaKey, areaName: card.area_name || areaKey, weekKey: card.week_key, extra: true }));
      all.forEach((row) => {
        const task = row.task;
        const scheduled = Number((task.scheduled || [])[di] || 0);
        const dayRow = (task.days || [])[di] || [];
        const slots = Math.max(scheduled, dayRow.length > 1 ? dayRow.length : 0);
        for (let dot = 0; dot < slots; dot++) {
          const done = !!dayRow[dot];
          const isScheduled = dot < scheduled;
          if (!isScheduled && !done) continue;
          out.push({ ...row, name: task.name, dot, done, scheduled: isScheduled, overdue: !done && day < today });
        }
      });
    });
    out.sort((a, b) => Number(a.done) - Number(b.done) || a.areaName.localeCompare(b.areaName) || a.name.localeCompare(b.name));
    return out;
  }

  async function toggleItem(item, day) {
    const di = Math.round((day - mondayFor(day)) / 86400000);
    const next = !item.done;
    await fetch('/api/routine-cards/' + item.weekKey + '/' + item.areaKey + '/set-dot', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: item.taskIndex, day: di, dot: item.dot, value: next, list: item.list }),
    });
    state.weekCache.delete(item.weekKey);
    await renderCalendar();
  }

  function monthRange(monthDate) {
    const first = new Date(monthDate.getFullYear(), monthDate.getMonth(), 1);
    const last = new Date(monthDate.getFullYear(), monthDate.getMonth() + 1, 0);
    const start = mondayFor(first);
    const end = addDays(mondayFor(last), 6);
    return { first, last, start, end };
  }

  async function renderCalendar() {
    const mount = document.getElementById('cal-mount');
    const title = document.getElementById('cal-title');
    if (!mount || !title) return;
    title.textContent = monthLabel(state.current);
    mount.className = 'cal-loading';
    mount.textContent = 'Loading calendar…';

    const { first, last, start, end } = monthRange(state.current);
    const cardsByWeek = await weeksForRange(start, end);
    const todayIso = iso(new Date());
    let html = '<div class="cal-grid">' + DAYS.map((d) => '<div class="cal-dow">' + d + '</div>').join('');
    const dayItems = new Map();
    for (let d = new Date(start); d <= end; d = addDays(d, 1)) {
      const key = iso(d);
      const items = itemsForDay(cardsByWeek, d);
      dayItems.set(key, items);
      const inMonth = d >= first && d <= last;
      const cls = ['cal-day'];
      if (!inMonth) cls.push('is-other');
      if (key === todayIso) cls.push('is-today');
      const visible = items.slice(0, 7);
      html += '<div class="' + cls.join(' ') + '" data-day="' + key + '">';
      html += '<div class="cal-date-row"><span class="cal-date-num">' + d.getDate() + '</span><span class="cal-count">' + items.length + '</span></div>';
      html += '<div class="cal-tasks">';
      if (!items.length) html += '<div class="cal-empty">clear</div>';
      visible.forEach((it, idx) => {
        const taskCls = ['cal-task'];
        if (it.done) taskCls.push('done');
        if (it.overdue) taskCls.push('overdue');
        if (it.extra) taskCls.push('extra');
        html += '<button type="button" class="' + taskCls.join(' ') + '" data-day="' + key + '" data-idx="' + idx + '" title="' + esc(it.areaName + ' · ' + it.name) + '">' + esc((it.done ? '✓ ' : '') + it.name) + '</button>';
      });
      if (items.length > visible.length) html += '<div class="cal-more">+' + (items.length - visible.length) + ' more</div>';
      html += '</div></div>';
    }
    html += '</div>';
    mount.className = '';
    mount.innerHTML = html;
    mount.querySelectorAll('.cal-task').forEach((btn) => {
      btn.addEventListener('click', () => {
        const key = btn.getAttribute('data-day');
        const idx = Number(btn.getAttribute('data-idx'));
        const item = (dayItems.get(key) || [])[idx];
        if (item) toggleItem(item, parseIso(key));
      });
    });
  }

  function setMonth(delta) {
    state.current = new Date(state.current.getFullYear(), state.current.getMonth() + delta, 1);
    const url = new URL(location.href);
    url.searchParams.set('view', 'calendar');
    url.searchParams.set('month', monthKey(state.current));
    history.replaceState(null, '', url.toString());
    renderCalendar();
  }

  replacePageShell();
  document.getElementById('cal-prev')?.addEventListener('click', () => setMonth(-1));
  document.getElementById('cal-next')?.addEventListener('click', () => setMonth(1));
  document.getElementById('cal-today')?.addEventListener('click', () => { state.current = parseIso(new Date().toISOString().slice(0, 7) + '-01'); setMonth(0); });
  renderCalendar();
})();
