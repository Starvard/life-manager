(function () {
  if (!location.pathname.startsWith('/cards')) return;

  const MS_DAY = 86400000;
  const TZ = 'America/New_York';
  const CACHE = new Map();

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
  function isDaily(freq) { return Number(freq || 0) >= 7; }
  function keyOf(areaKey, name) { return areaKey + '::' + name; }

  function dailyBucket(name, dot, total) {
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
      .routine-subtabs { display:flex; gap:.4rem; flex-wrap:wrap; margin:.25rem 0 .85rem; }
      .routine-subtabs a { border:1px solid var(--border); border-radius:999px; padding:.42rem .7rem; color:var(--text-muted); text-decoration:none; background:rgba(255,255,255,.035); font-size:.78rem; font-weight:700; }
      .routine-subtabs a.active { color:white; border-color:rgba(99,179,255,.34); background:rgba(99,179,255,.16); }
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
    const sel = parseIso(selIso);
    const start = addDays(mondayFor(sel), -26 * 7);
    const end = addDays(mondayFor(sel), 8 * 7);
    const weeks = new Set();
    for (let d = new Date(start); d <= end; d = addDays(d, 7)) weeks.add(weekKeyFor(d));
    const hist = {};
    await Promise.all(Array.from(weeks).map(async (wk) => {
      const areas = await fetchWeek(wk);
      Object.values(areas || {}).forEach((card) => addHistoryFromCard(card, hist));
    }));
    alpineCards().forEach((card) => addHistoryFromCard(card, hist));
    Object.keys(hist).forEach((k) => hist[k] = Array.from(new Set(hist[k])).sort());
    return hist;
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
    const scheduled = Number((item.task.scheduled || [])[di] || 0);
    const count = Math.max(scheduled, row.length > 1 ? row.length : 0);
    const out = [];
    for (let dot = 0; dot < count; dot++) {
      const done = !!row[dot];
      const bucket = dailyBucket(item.name, dot, count);
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

    let html = '<nav class="routine-subtabs" aria-label="Routine views"><a class="active" href="/cards">Today Stack</a><a href="/routines?view=calendar">Calendar</a><a href="/routines">Manage</a></nav>';
    html += '<section class="card eff-hero"><div><p class="eff-eyebrow">Routines · split view</p><p class="eff-date">' + esc(dateLabel(selIso, true)) + (today ? ' · Today' : '') + '</p><h2>Daily on the left, recurring on the right</h2><p class="eff-sub">Daily habits check off instantly without refreshing. Flexible routines recalculate from actual completion date, so those can refresh after you mark one done.</p></div><div class="eff-actions"><a class="btn btn-secondary btn-sm" href="/routines?view=calendar">Calendar</a><a class="btn btn-secondary btn-sm" href="/routines">Manage</a></div></section>';
    html += recentLinks(selIso);
    html += '<div class="eff-summary"><span data-daily-done-count>' + dailyDoneCount + '/' + dailyRows.length + ' daily done</span><span>' + overdue.length + ' overdue</span><span>' + due.length + ' due today</span><span>' + upcoming.length + ' coming up</span></div>';

    const rowRefs = [];
    html += '<div class="eff-columns">';
    html += '<div class="eff-column eff-daily-column"><section class="card eff-column-title"><h3>Daily checklist</h3><p>No refresh. Organized by rough time of day.</p></section>';
    ['Morning', 'Midday', 'Evening'].forEach((bucket) => {
      html += sectionHtml(bucket, dailyRows.filter((r) => r.bucket === bucket), rowRefs);
    });
    if (!dailyRows.length) html += '<div class="card eff-empty">No daily tasks for this day.</div>';
    html += '</div>';

    html += '<div class="eff-column eff-flex-column"><section class="card eff-column-title"><h3>Recurring due dates</h3><p>These use last completion + interval. Marking one done refreshes this side so the new due date is correct.</p></section>';
    html += sectionHtml('Overdue', overdue, rowRefs);
    html += sectionHtml('Due Today', due, rowRefs);
    html += sectionHtml('Coming Up', upcoming, rowRefs);
    html += sectionHtml('Done Today', flexDone, rowRefs);
    if (!flexRows.length) html += '<div class="card eff-empty">No recurring due-date tasks active right now.</div>';
    html += '</div></div>';

    mount.innerHTML = html;
    mount.querySelectorAll('[data-eff-idx]').forEach((btn) => {
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

  function schedule() { setTimeout(render, 180); }
  window.addEventListener('load', schedule);
  document.addEventListener('alpine:initialized', schedule);
})();
