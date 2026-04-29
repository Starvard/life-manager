(function () {
  const params = new URLSearchParams(location.search);
  if (location.pathname !== '/routines' || params.get('view') !== 'calendar') return;

  const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const MS_DAY = 86400000;
  const CACHE = new Map();

  function parseIso(s) { return new Date(String(s || '').slice(0, 10) + 'T00:00:00'); }
  function iso(d) {
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
  function mondayFor(d) { const x = new Date(d); const n = (x.getDay() + 6) % 7; x.setDate(x.getDate() - n); return x; }
  function daysBetween(a, b) { return Math.round((parseIso(a) - parseIso(b)) / MS_DAY); }
  function monthKey(d) { return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0'); }
  function monthLabel(d) { return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }); }
  function dayLabel(d) { return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' }); }
  function intervalDays(freq) {
    const f = Number(freq || 0);
    if (f <= 0) return 9999;
    if (f >= 7) return 1;
    return Math.max(1, Math.round(7 / f));
  }
  function esc(s) { return String(s || '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function weekKeyFor(d) {
    const x = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    const day = x.getUTCDay() || 7;
    x.setUTCDate(x.getUTCDate() + 4 - day);
    const yearStart = new Date(Date.UTC(x.getUTCFullYear(), 0, 1));
    const week = Math.ceil((((x - yearStart) / MS_DAY) + 1) / 7);
    return x.getUTCFullYear() + '-W' + String(week).padStart(2, '0');
  }

  function injectStyles() {
    if (document.getElementById('routine-calendar-effective-styles')) return;
    const style = document.createElement('style');
    style.id = 'routine-calendar-effective-styles';
    style.textContent = `
      .routine-calendar-shell { display:grid; gap:.85rem; }
      .routine-subtabs { display:flex; gap:.4rem; flex-wrap:wrap; margin:-.4rem 0 .25rem; }
      .routine-subtabs a { border:1px solid var(--border); border-radius:999px; padding:.42rem .7rem; color:var(--text-muted); text-decoration:none; background:rgba(255,255,255,.035); font-size:.78rem; font-weight:700; }
      .routine-subtabs a.active { color:white; border-color:rgba(99,179,255,.34); background:rgba(99,179,255,.16); }
      .cal-hero,.cal-toolbar,.cal-legend,.cal-day-detail { padding:.85rem; }
      .cal-hero { display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; }
      .cal-hero h1 { margin:0; font-size:1.45rem; }
      .cal-hero p,.cal-day-detail p { margin:.25rem 0 0; color:var(--text-muted); font-size:.82rem; line-height:1.35; }
      .cal-actions,.cal-nav,.cal-legend { display:flex; flex-wrap:wrap; gap:.45rem; }
      .cal-toolbar { display:flex; justify-content:space-between; align-items:center; gap:.75rem; }
      .cal-toolbar h2 { margin:0; font-size:1.05rem; }
      .cal-legend span { border:1px solid var(--border); border-radius:999px; padding:.25rem .5rem; background:rgba(255,255,255,.035); color:var(--text-muted); font-size:.72rem; }
      .cal-grid { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:.5rem; }
      .cal-dow { color:var(--text-muted); font-size:.68rem; font-weight:800; text-transform:uppercase; padding:0 .25rem; }
      .cal-day { min-height:7.3rem; padding:.45rem; border:1px solid var(--border); border-radius:var(--radius-sm); background:var(--surface); overflow:hidden; cursor:pointer; }
      .cal-day:hover { border-color:var(--glass-border); background:var(--surface-hover); }
      .cal-day.is-other { opacity:.42; }
      .cal-day.is-today { border-color:rgba(99,179,255,.45); box-shadow:0 0 0 1px rgba(99,179,255,.14),0 0 16px rgba(99,179,255,.08); }
      .cal-day.is-selected { outline:2px solid rgba(99,179,255,.45); outline-offset:2px; background:rgba(99,179,255,.08); }
      .cal-date-row { display:flex; justify-content:space-between; gap:.25rem; margin-bottom:.32rem; }
      .cal-date-num { font-size:.82rem; font-weight:800; color:var(--text-bright); }
      .cal-count { font-size:.62rem; color:var(--text-muted); }
      .cal-tasks { display:flex; flex-direction:column; gap:.18rem; }
      .cal-task { border:0; border-radius:.42rem; padding:.18rem .28rem; background:rgba(255,255,255,.055); color:var(--text); font-size:.64rem; line-height:1.13; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; pointer-events:none; }
      .cal-task.done { text-decoration:line-through; opacity:.55; }
      .cal-task.overdue { background:rgba(251,146,60,.16); }
      .cal-empty,.cal-more { color:var(--text-muted); font-size:.62rem; }
      .cal-detail-head { display:flex; justify-content:space-between; gap:.75rem; align-items:flex-start; }
      .cal-day-detail h3 { margin:0 0 .2rem; font-size:1rem; }
      .cal-detail-list { display:grid; gap:.35rem; margin-top:.7rem; }
      .cal-detail-item { display:flex; gap:.55rem; align-items:center; border:1px solid var(--border); border-radius:.75rem; padding:.55rem .65rem; background:rgba(255,255,255,.035); }
      .cal-detail-item.done { opacity:.58; }
      .cal-detail-item.overdue { border-color:rgba(251,146,60,.35); background:rgba(251,146,60,.08); }
      .cal-detail-check { flex:0 0 1.3rem; width:1.3rem; height:1.3rem; border-radius:999px; display:grid; place-items:center; background:rgba(255,255,255,.06); font-weight:800; font-size:.75rem; }
      .cal-detail-name { font-weight:700; font-size:.88rem; }
      .cal-detail-meta { color:var(--text-muted); font-size:.72rem; margin-top:.05rem; }
      .cal-loading { padding:1rem; color:var(--text-muted); }
      @media(max-width:760px){.cal-grid{gap:.3rem}.cal-day{min-height:5.8rem;padding:.32rem}.cal-task{font-size:.57rem;padding:.14rem .22rem}.cal-hero,.cal-toolbar,.cal-detail-head{display:block}.cal-actions{margin-top:.7rem}.cal-dow{font-size:.58rem}}
    `;
    document.head.appendChild(style);
  }

  const state = {
    current: parseIso((params.get('month') || new Date().toISOString().slice(0, 7)) + '-01'),
    selectedDay: params.get('day') || null,
    dayItems: new Map(),
  };

  async function fetchWeek(wk) {
    if (CACHE.has(wk)) return CACHE.get(wk);
    const p = fetch('/api/routine-cards/' + encodeURIComponent(wk))
      .then((r) => r.ok ? r.json() : { areas: {} })
      .then((data) => data.areas || {})
      .catch(() => ({}));
    CACHE.set(wk, p);
    return p;
  }

  async function weeksForRange(start, end) {
    const weeks = new Set();
    for (let d = new Date(start); d <= end; d = addDays(d, 1)) weeks.add(weekKeyFor(d));
    const out = {};
    await Promise.all(Array.from(weeks).map(async (wk) => { out[wk] = await fetchWeek(wk); }));
    return out;
  }

  function addHistoryFromCard(card, hist) {
    const areaKey = card.area_key || '';
    if (!areaKey || !card.week_start) return;
    (card.tasks || []).forEach((task) => {
      const key = areaKey + '::' + task.name;
      (task.days || []).forEach((row, di) => {
        if ((row || []).some(Boolean)) {
          if (!hist[key]) hist[key] = [];
          hist[key].push(iso(addDays(parseIso(card.week_start), di)));
        }
      });
    });
  }

  function sortItems(items) {
    return items.sort((a, b) => {
      if (a.done !== b.done) return Number(a.done) - Number(b.done);
      if (a.overdueDays !== b.overdueDays) return b.overdueDays - a.overdueDays;
      if (a.overdue !== b.overdue) return Number(b.overdue) - Number(a.overdue);
      return a.areaName.localeCompare(b.areaName) || a.name.localeCompare(b.name) || a.dot - b.dot;
    });
  }

  function monthRange(monthDate) {
    const first = new Date(monthDate.getFullYear(), monthDate.getMonth(), 1);
    const last = new Date(monthDate.getFullYear(), monthDate.getMonth() + 1, 0);
    const start = mondayFor(first);
    const end = addDays(mondayFor(last), 6);
    return { first, last, start, end };
  }

  function itemsForDay(cardsByWeek, hist, day) {
    const wk = weekKeyFor(day);
    const cards = cardsByWeek[wk] || {};
    const monday = mondayFor(day);
    const dayIso = iso(day);
    const di = Math.round((day - monday) / MS_DAY);
    const todayIso = iso(new Date());
    const overdueDays = Math.max(0, daysBetween(todayIso, dayIso));
    const out = [];

    Object.entries(cards).forEach(([areaKey, card]) => {
      (card.tasks || []).forEach((task, taskIndex) => {
        const key = areaKey + '::' + task.name;
        const freq = Number(task.freq || 0);
        const dayRow = (task.days || [])[di] || [];
        const doneCount = dayRow.filter(Boolean).length;
        const scheduled = Number((task.scheduled || [])[di] || 0);
        const last = (hist[key] || []).filter((d) => d < dayIso).pop();
        const nextDue = last ? iso(addDays(parseIso(last), intervalDays(freq))) : null;
        const suppressedByRecentCompletion = !doneCount && nextDue && nextDue > dayIso && freq < 7;

        for (let dot = 0; dot < doneCount; dot++) {
          out.push({ areaKey, areaName: card.area_name || areaKey, taskIndex, name: task.name, dot, done: true, overdue: false, overdueDays: 0 });
        }
        if (!suppressedByRecentCompletion) {
          for (let dot = doneCount; dot < scheduled; dot++) {
            out.push({ areaKey, areaName: card.area_name || areaKey, taskIndex, name: task.name, dot, done: false, overdue: overdueDays > 0, overdueDays });
          }
        }
      });
    });
    return sortItems(out);
  }

  function renderShell() {
    injectStyles();
    const main = document.querySelector('.main-content');
    if (!main) return;
    main.innerHTML = `
      <div class="routine-calendar-shell">
        <nav class="routine-subtabs" aria-label="Routine views"><a href="/cards">Today Stack</a><a href="/routines?view=calendar" class="active">Calendar</a><a href="/routines">Manage</a></nav>
        <section class="card cal-hero"><div><h1>Routine Calendar</h1><p>Month view of effective due dates. Recent early/late completions suppress future stale schedule slots. Click a day to isolate it.</p></div><div class="cal-actions"><a class="btn btn-secondary btn-sm" href="/cards">Today Stack</a><a class="btn btn-secondary btn-sm" href="/routines">Manage</a></div></section>
        <section class="card cal-toolbar"><div class="cal-nav"><button type="button" class="btn btn-secondary btn-sm" id="cal-prev">← Month</button><button type="button" class="btn btn-secondary btn-sm" id="cal-today">Today</button><button type="button" class="btn btn-secondary btn-sm" id="cal-next">Month →</button></div><h2 id="cal-title"></h2></section>
        <section class="cal-legend card"><span>View only</span><span>Recent completions move future due dates</span><span>Open overdue items sort first</span></section>
        <section id="cal-day-detail" class="card cal-day-detail" hidden></section>
        <div id="cal-mount" class="cal-loading">Loading calendar…</div>
      </div>`;
    document.getElementById('cal-prev')?.addEventListener('click', () => setMonth(-1));
    document.getElementById('cal-next')?.addEventListener('click', () => setMonth(1));
    document.getElementById('cal-today')?.addEventListener('click', () => { state.current = parseIso(new Date().toISOString().slice(0, 7) + '-01'); setMonth(0); });
  }

  function renderDayDetail(dayIso, shouldScroll) {
    const detail = document.getElementById('cal-day-detail');
    if (!detail) return;
    if (!dayIso) { detail.hidden = true; detail.innerHTML = ''; return; }
    const items = sortItems([...(state.dayItems.get(dayIso) || [])]);
    const overdueOpen = items.filter((x) => x.overdue && !x.done).length;
    let html = '<div class="cal-detail-head"><div><h3>' + esc(dayLabel(parseIso(dayIso))) + '</h3><p>' + items.length + ' item' + (items.length === 1 ? '' : 's') + ' shown';
    if (overdueOpen) html += ' · ' + overdueOpen + ' overdue/open first';
    html += '. Complete from the day view, not the calendar.</p></div><a class="btn btn-secondary btn-sm" href="/cards/day?date=' + esc(dayIso) + '">Open day view</a></div>';
    if (!items.length) html += '<div class="cal-empty">No routine tasks due or completed for this day.</div>';
    else {
      html += '<div class="cal-detail-list">';
      items.forEach((it) => {
        const cls = ['cal-detail-item'];
        if (it.done) cls.push('done');
        if (it.overdue) cls.push('overdue');
        const overdueText = it.overdueDays ? ' · ' + it.overdueDays + ' day' + (it.overdueDays === 1 ? '' : 's') + ' overdue' : '';
        html += '<div class="' + cls.join(' ') + '"><span class="cal-detail-check">' + (it.done ? '✓' : '○') + '</span><span><span class="cal-detail-name">' + esc(it.name) + '</span><div class="cal-detail-meta">' + esc(it.areaName + (it.dot > 0 ? ' · #' + (it.dot + 1) : '') + overdueText) + '</div></span></div>';
      });
      html += '</div>';
    }
    detail.innerHTML = html;
    detail.hidden = false;
    if (shouldScroll) detail.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function selectDay(dayIso, shouldScroll) {
    state.selectedDay = dayIso;
    const url = new URL(location.href);
    url.searchParams.set('view', 'calendar');
    url.searchParams.set('month', monthKey(state.current));
    url.searchParams.set('day', dayIso);
    history.replaceState(null, '', url.toString());
    document.querySelectorAll('.cal-day').forEach((el) => el.classList.toggle('is-selected', el.getAttribute('data-day') === dayIso));
    renderDayDetail(dayIso, shouldScroll);
  }

  async function renderCalendar() {
    const mount = document.getElementById('cal-mount');
    const title = document.getElementById('cal-title');
    if (!mount || !title) return;
    title.textContent = monthLabel(state.current);
    mount.className = 'cal-loading';
    mount.textContent = 'Loading calendar…';
    const { first, last, start, end } = monthRange(state.current);
    const historyStart = addDays(start, -12 * 7);
    const cardsByWeek = await weeksForRange(historyStart, end);
    const hist = {};
    Object.values(cardsByWeek).forEach((areas) => Object.values(areas || {}).forEach((card) => addHistoryFromCard(card, hist)));
    Object.keys(hist).forEach((k) => hist[k] = Array.from(new Set(hist[k])).sort());
    const todayIso = iso(new Date());
    state.dayItems = new Map();
    let html = '<div class="cal-grid">' + DAYS.map((d) => '<div class="cal-dow">' + d + '</div>').join('');
    for (let d = new Date(start); d <= end; d = addDays(d, 1)) {
      const key = iso(d);
      const items = itemsForDay(cardsByWeek, hist, d);
      state.dayItems.set(key, items);
      const cls = ['cal-day'];
      if (d < first || d > last) cls.push('is-other');
      if (key === todayIso) cls.push('is-today');
      if (key === state.selectedDay) cls.push('is-selected');
      html += '<div role="button" tabindex="0" class="' + cls.join(' ') + '" data-day="' + key + '" aria-label="Open tasks for ' + esc(dayLabel(d)) + '"><div class="cal-date-row"><span class="cal-date-num">' + d.getDate() + '</span><span class="cal-count">' + items.length + '</span></div><div class="cal-tasks">';
      if (!items.length) html += '<div class="cal-empty">clear</div>';
      items.slice(0, 7).forEach((it) => {
        const taskCls = ['cal-task'];
        if (it.done) taskCls.push('done');
        if (it.overdue) taskCls.push('overdue');
        html += '<span class="' + taskCls.join(' ') + '" title="' + esc(it.areaName + ' · ' + it.name) + '">' + esc((it.done ? '✓ ' : '') + it.name) + '</span>';
      });
      if (items.length > 7) html += '<div class="cal-more">+' + (items.length - 7) + ' more</div>';
      html += '</div></div>';
    }
    html += '</div>';
    mount.className = '';
    mount.innerHTML = html;
    mount.querySelectorAll('.cal-day[data-day]').forEach((cell) => {
      cell.addEventListener('click', () => selectDay(cell.getAttribute('data-day'), true));
      cell.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectDay(cell.getAttribute('data-day'), true); } });
    });
    if (state.selectedDay) renderDayDetail(state.selectedDay, false);
  }

  function setMonth(delta) {
    state.current = new Date(state.current.getFullYear(), state.current.getMonth() + delta, 1);
    state.selectedDay = null;
    const url = new URL(location.href);
    url.searchParams.set('view', 'calendar');
    url.searchParams.set('month', monthKey(state.current));
    url.searchParams.delete('day');
    history.replaceState(null, '', url.toString());
    renderDayDetail(null, false);
    renderCalendar();
  }

  window.addEventListener('load', () => { renderShell(); renderCalendar(); });
})();
