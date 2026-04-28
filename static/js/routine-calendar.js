(function () {
  const params = new URLSearchParams(location.search);
  if (location.pathname !== '/routines' || params.get('view') !== 'calendar') return;

  const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

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
  function dayLabel(d) { return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' }); }
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
      .routine-subtabs { display:flex; gap:.4rem; flex-wrap:wrap; margin:-.4rem 0 .25rem; }
      .routine-subtabs a { border:1px solid var(--border); border-radius:999px; padding:.42rem .7rem; color:var(--text-muted); text-decoration:none; background:rgba(255,255,255,.035); font-size:.78rem; font-weight:700; }
      .routine-subtabs a.active { color:white; border-color:rgba(99,179,255,.34); background:rgba(99,179,255,.16); }
      .cal-hero { display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; padding:1rem; }
      .cal-hero h1 { margin:0; font-size:1.45rem; }
      .cal-hero p { margin:.25rem 0 0; color:var(--text-muted); font-size:.86rem; max-width:46rem; }
      .cal-actions { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:.45rem; }
      .cal-toolbar { display:flex; align-items:center; justify-content:space-between; gap:.75rem; padding:.75rem; }
      .cal-toolbar h2 { margin:0; font-size:1.05rem; }
      .cal-nav { display:flex; gap:.4rem; flex-wrap:wrap; }
      .cal-grid { display:grid; grid-template-columns:repeat(7, minmax(0, 1fr)); gap:.5rem; }
      .cal-dow { color:var(--text-muted); font-size:.68rem; font-weight:800; letter-spacing:.06em; text-transform:uppercase; padding:0 .25rem; }
      .cal-day { min-height:7.3rem; padding:.45rem; border:1px solid var(--border); border-radius:var(--radius-sm); background:var(--surface); overflow:hidden; cursor:pointer; text-align:left; }
      .cal-day:hover { border-color:var(--glass-border); background:var(--surface-hover); }
      .cal-day.is-other { opacity:.42; }
      .cal-day.is-today { border-color:rgba(99,179,255,.45); box-shadow:0 0 0 1px rgba(99,179,255,.14), 0 0 16px rgba(99,179,255,.08); }
      .cal-day.is-selected { outline:2px solid rgba(99,179,255,.45); outline-offset:2px; }
      .cal-date-row { display:flex; align-items:center; justify-content:space-between; gap:.25rem; margin-bottom:.32rem; }
      .cal-date-num { font-size:.82rem; font-weight:800; color:var(--text-bright); }
      .cal-count { font-size:.62rem; color:var(--text-muted); }
      .cal-tasks { display:flex; flex-direction:column; gap:.18rem; }
      .cal-task { width:100%; border:0; border-radius:.42rem; padding:.18rem .28rem; background:rgba(255,255,255,.055); color:var(--text); text-align:left; font:inherit; font-size:.64rem; line-height:1.13; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; pointer-events:none; }
      .cal-task.done { text-decoration:line-through; opacity:.55; }
      .cal-task.overdue { background:rgba(251,146,60,.16); }
      .cal-task.extra { outline:1px dashed rgba(148,163,184,.32); }
      .cal-empty { color:var(--text-light); font-size:.64rem; padding-top:.2rem; }
      .cal-more { color:var(--text-muted); font-size:.62rem; margin-top:.12rem; }
      .cal-legend { display:flex; flex-wrap:wrap; gap:.45rem; color:var(--text-muted); font-size:.72rem; padding:.65rem .75rem; }
      .cal-legend span { border:1px solid var(--border); border-radius:999px; padding:.25rem .5rem; background:rgba(255,255,255,.035); }
      .cal-loading { padding:1rem; color:var(--text-muted); }
      .cal-day-detail { padding:.9rem; }
      .cal-day-detail h3 { margin:0 0 .2rem; font-size:1rem; }
      .cal-day-detail p { margin:0 0 .7rem; color:var(--text-muted); font-size:.8rem; }
      .cal-detail-list { display:grid; gap:.35rem; }
      .cal-detail-item { display:flex; align-items:center; gap:.55rem; border:1px solid var(--border); border-radius:.75rem; padding:.55rem .65rem; background:rgba(255,255,255,.035); }
      .cal-detail-item.done { opacity:.58; }
      .cal-detail-item.overdue { border-color:rgba(251,146,60,.35); background:rgba(251,146,60,.08); }
      .cal-detail-check { flex:0 0 1.3rem; width:1.3rem; height:1.3rem; display:grid; place-items:center; border-radius:999px; background:rgba(255,255,255,.06); font-weight:800; font-size:.75rem; }
      .cal-detail-name { font-weight:700; font-size:.88rem; }
      .cal-detail-meta { color:var(--text-muted); font-size:.72rem; margin-top:.05rem; }
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
        <nav class="routine-subtabs" aria-label="Routine views">
          <a href="/cards">Today Stack</a>
          <a href="/routines?view=calendar" class="active">Calendar</a>
          <a href="/routines">Manage</a>
        </nav>
        <section class="card cal-hero">
          <div>
            <h1>Routine Calendar</h1>
            <p>Month view of what is due each day. The task chips are just a view. Click a day to expand the full task list for that day.</p>
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
          <span>View only</span>
          <span>Click a day to expand</span>
          <span>Orange = overdue</span>
        </section>
        <div id="cal-mount" class="cal-loading">Loading calendar…</div>
        <section id="cal-day-detail" class="card cal-day-detail" hidden></section>
      </div>`;
    return main;
  }

  const state = {
    current: parseIso((params.get('month') || new Date().toISOString().slice(0, 7)) + '-01'),
    selectedDay: params.get('day') || null,
    weekCache: new Map(),
    dayItems: new Map(),
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

  function monthRange(monthDate) {
    const first = new Date(monthDate.getFullYear(), monthDate.getMonth(), 1);
    const last = new Date(monthDate.getFullYear(), monthDate.getMonth() + 1, 0);
    const start = mondayFor(first);
    const end = addDays(mondayFor(last), 6);
    return { first, last, start, end };
  }

  function renderDayDetail(dayIso) {
    const detail = document.getElementById('cal-day-detail');
    if (!detail) return;
    if (!dayIso) {
      detail.hidden = true;
      detail.innerHTML = '';
      return;
    }
    const items = state.dayItems.get(dayIso) || [];
    const d = parseIso(dayIso);
    let html = '<h3>' + esc(dayLabel(d)) + '</h3>';
    html += '<p>' + items.length + ' item' + (items.length === 1 ? '' : 's') + ' shown. Complete tasks from the Today Stack/day view, not the calendar.</p>';
    if (!items.length) {
      html += '<div class="cal-empty">No routine tasks scheduled or completed for this day.</div>';
    } else {
      html += '<div class="cal-detail-list">';
      items.forEach((it) => {
        const cls = ['cal-detail-item'];
        if (it.done) cls.push('done');
        if (it.overdue) cls.push('overdue');
        html += '<div class="' + cls.join(' ') + '"><span class="cal-detail-check">' + (it.done ? '✓' : '○') + '</span><span><span class="cal-detail-name">' + esc(it.name) + '</span><div class="cal-detail-meta">' + esc(it.areaName + (it.extra ? ' · one-off' : '') + (it.dot > 0 ? ' · #' + (it.dot + 1) : '')) + '</div></span></div>';
      });
      html += '</div>';
    }
    detail.innerHTML = html;
    detail.hidden = false;
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
    state.dayItems = new Map();
    let html = '<div class="cal-grid">' + DAYS.map((d) => '<div class="cal-dow">' + d + '</div>').join('');
    for (let d = new Date(start); d <= end; d = addDays(d, 1)) {
      const key = iso(d);
      const items = itemsForDay(cardsByWeek, d);
      state.dayItems.set(key, items);
      const inMonth = d >= first && d <= last;
      const cls = ['cal-day'];
      if (!inMonth) cls.push('is-other');
      if (key === todayIso) cls.push('is-today');
      if (key === state.selectedDay) cls.push('is-selected');
      const visible = items.slice(0, 7);
      html += '<button type="button" class="' + cls.join(' ') + '" data-day="' + key + '">';
      html += '<div class="cal-date-row"><span class="cal-date-num">' + d.getDate() + '</span><span class="cal-count">' + items.length + '</span></div>';
      html += '<div class="cal-tasks">';
      if (!items.length) html += '<div class="cal-empty">clear</div>';
      visible.forEach((it) => {
        const taskCls = ['cal-task'];
        if (it.done) taskCls.push('done');
        if (it.overdue) taskCls.push('overdue');
        if (it.extra) taskCls.push('extra');
        html += '<span class="' + taskCls.join(' ') + '" title="' + esc(it.areaName + ' · ' + it.name) + '">' + esc((it.done ? '✓ ' : '') + it.name) + '</span>';
      });
      if (items.length > visible.length) html += '<div class="cal-more">+' + (items.length - visible.length) + ' more</div>';
      html += '</div></button>';
    }
    html += '</div>';
    mount.className = '';
    mount.innerHTML = html;
    mount.querySelectorAll('.cal-day[data-day]').forEach((btn) => {
      btn.addEventListener('click', () => {
        state.selectedDay = btn.getAttribute('data-day');
        const url = new URL(location.href);
        url.searchParams.set('view', 'calendar');
        url.searchParams.set('month', monthKey(state.current));
        url.searchParams.set('day', state.selectedDay);
        history.replaceState(null, '', url.toString());
        mount.querySelectorAll('.cal-day').forEach((el) => el.classList.toggle('is-selected', el.getAttribute('data-day') === state.selectedDay));
        renderDayDetail(state.selectedDay);
      });
    });
    if (state.selectedDay) renderDayDetail(state.selectedDay);
  }

  function setMonth(delta) {
    state.current = new Date(state.current.getFullYear(), state.current.getMonth() + delta, 1);
    state.selectedDay = null;
    const url = new URL(location.href);
    url.searchParams.set('view', 'calendar');
    url.searchParams.set('month', monthKey(state.current));
    url.searchParams.delete('day');
    history.replaceState(null, '', url.toString());
    renderDayDetail(null);
    renderCalendar();
  }

  replacePageShell();
  document.getElementById('cal-prev')?.addEventListener('click', () => setMonth(-1));
  document.getElementById('cal-next')?.addEventListener('click', () => setMonth(1));
  document.getElementById('cal-today')?.addEventListener('click', () => { state.current = parseIso(new Date().toISOString().slice(0, 7) + '-01'); setMonth(0); });
  renderCalendar();
})();
