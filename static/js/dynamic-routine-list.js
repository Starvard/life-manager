(function () {
  if (new URLSearchParams(location.search).get('legacy') === '1') return;
  function injectStyles() {
    if (document.getElementById('dynamic-routine-styles')) return;
    const style = document.createElement('style');
    style.id = 'dynamic-routine-styles';
    style.textContent = `
      body.dynamic-routines-active .notecard,
      body.dynamic-routines-active .area-tabs,
      body.dynamic-routines-active .cards-today-score { display: none !important; }
      #dynamic-routine-app { margin: 1rem 0 1.5rem; }
      .dyn-routine-hero { display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; padding:1rem; margin-bottom:.8rem; }
      .dyn-routine-hero h2 { margin:.1rem 0 .25rem; font-size:1.25rem; }
      .dyn-eyebrow { margin:0; text-transform:uppercase; letter-spacing:.08em; font-size:.72rem; color:var(--text-muted); font-weight:800; }
      .dyn-sub { margin:0; color:var(--text-muted); line-height:1.35; max-width:40rem; }
      .dyn-summary { display:flex; gap:.5rem; flex-wrap:wrap; margin:.65rem 0 1rem; }
      .dyn-summary span { border:1px solid rgba(148,163,184,.2); border-radius:999px; padding:.35rem .65rem; background:rgba(255,255,255,.04); font-size:.82rem; color:var(--text-muted); }
      .dyn-list { display:grid; gap:.85rem; }
      .dyn-section { padding:.9rem; }
      .dyn-section h3 { margin:0 0 .65rem; font-size:1rem; }
      .dyn-task { width:100%; display:flex; align-items:center; gap:.7rem; border:1px solid rgba(148,163,184,.18); border-radius:.9rem; padding:.7rem .75rem; margin:.45rem 0; background:rgba(255,255,255,.035); color:inherit; text-align:left; cursor:pointer; }
      .dyn-task.overdue { border-color:rgba(251,146,60,.42); background:rgba(251,146,60,.08); }
      .dyn-task.due { border-color:rgba(250,204,21,.28); background:rgba(250,204,21,.05); }
      .dyn-task.done { border-color:rgba(134,239,172,.32); background:rgba(134,239,172,.07); }
      .dyn-task.readonly { cursor:default; opacity:.85; }
      .dyn-task strong { display:block; font-size:.95rem; }
      .dyn-task small { display:block; color:var(--text-muted); margin-top:.15rem; }
      .dyn-check { display:grid; place-items:center; flex:0 0 1.6rem; width:1.6rem; height:1.6rem; border-radius:999px; background:rgba(255,255,255,.06); font-weight:800; }
      .dyn-empty { padding:1rem; color:var(--text-muted); }
      @media (max-width:640px){ .dyn-routine-hero{display:block}.dyn-routine-hero .btn{margin-top:.75rem}.dyn-task{padding:.8rem} }
    `;
    document.head.appendChild(style);
  }
  function parseDate(s) { return new Date(String(s || '').slice(0, 10) + 'T00:00:00'); }
  function iso(d) { return d.toISOString().slice(0, 10); }
  function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
  function daysBetween(a, b) { return Math.round((parseDate(a) - parseDate(b)) / 86400000); }
  function intervalDays(freq) {
    const f = Number(freq || 0);
    if (f <= 0) return 9999;
    if (f >= 7) return 1;
    return Math.max(1, Math.round(7 / f));
  }
  function selectedDate() {
    const inp = document.querySelector('.picker-date');
    if (inp && inp.value) return inp.value;
    const today = new Date();
    return iso(today);
  }
  function dayIdxFor(dateStr, weekStart) {
    return Math.max(0, Math.min(6, daysBetween(dateStr, weekStart)));
  }
  function taskKey(areaKey, taskName) { return areaKey + '::' + taskName; }
  function getAlpineCards() {
    const cards = [];
    if (!window.Alpine) return cards;
    document.querySelectorAll('.notecard[x-data]').forEach((el) => {
      let data;
      try { data = window.Alpine.$data(el); } catch (_) { return; }
      if (!data || !data.card || !Array.isArray(data.card.tasks)) return;
      cards.push({ root: el, data, card: data.card, areaKey: data.card.area_key || '', weekKey: data.card.week_key || data.card.weekKey || '' });
    });
    return cards;
  }
  function scanCompletions(cards) {
    const hist = {};
    cards.forEach(({ card }) => {
      const weekStart = card.week_start;
      const areaKey = card.area_key || '';
      (card.tasks || []).forEach((task) => {
        const key = taskKey(areaKey, task.name);
        (task.days || []).forEach((row, di) => {
          if ((row || []).some(Boolean)) {
            const d = addDays(parseDate(weekStart), di);
            if (!hist[key]) hist[key] = [];
            hist[key].push(iso(d));
          }
        });
      });
    });
    Object.keys(hist).forEach((k) => hist[k].sort());
    return hist;
  }
  function friendlyDue(dueIso, selIso) {
    const delta = daysBetween(dueIso, selIso);
    if (delta === 0) return 'Today';
    if (delta === 1) return 'Tomorrow';
    if (delta === -1) return 'Yesterday';
    if (delta < 0) return Math.abs(delta) + ' days overdue';
    if (delta < 7) return parseDate(dueIso).toLocaleDateString(undefined, { weekday: 'short' });
    return dueIso;
  }
  function collectItems(cards, selIso) {
    const hist = scanCompletions(cards);
    const items = [];
    cards.forEach(({ card, areaKey }) => {
      const weekStart = card.week_start;
      (card.tasks || []).forEach((task, taskIndex) => {
        const key = taskKey(areaKey, task.name);
        const completions = (hist[key] || []).filter((d) => d <= selIso);
        const lastDone = completions.length ? completions[completions.length - 1] : null;
        const completedToday = completions.includes(selIso);
        const interval = intervalDays(task.freq);
        let nextDue = null;
        if (lastDone) nextDue = iso(addDays(parseDate(lastDone), interval));
        const scheduled = [];
        (task.scheduled || []).forEach((count, di) => {
          if (Number(count || 0) > 0) scheduled.push(iso(addDays(parseDate(weekStart), di)));
        });
        const pastSched = scheduled.filter((d) => d <= selIso).sort();
        const futureSched = scheduled.filter((d) => d > selIso).sort();
        if (!nextDue) nextDue = pastSched[0] || futureSched[0] || selIso;
        const due = nextDue <= selIso && !completedToday;
        const upcoming = nextDue > selIso && daysBetween(nextDue, selIso) <= 7;
        if (!due && !upcoming && !completedToday) return;
        items.push({ card, areaKey, areaName: card.area_name || areaKey, task, taskIndex, name: task.name, completedToday, due, upcoming, nextDue, interval, status: completedToday ? 'done' : (due ? (nextDue < selIso ? 'overdue' : 'due') : 'upcoming'), label: friendlyDue(nextDue, selIso) });
      });
    });
    items.sort((a, b) => (a.status === 'overdue' ? -1 : 0) - (b.status === 'overdue' ? -1 : 0) || a.nextDue.localeCompare(b.nextDue) || a.areaName.localeCompare(b.areaName) || a.name.localeCompare(b.name));
    return items;
  }
  function grouped(items, pred) {
    const out = [];
    const map = {};
    items.filter(pred).forEach((it) => {
      if (!map[it.areaKey]) { map[it.areaKey] = { areaName: it.areaName, items: [] }; out.push(map[it.areaKey]); }
      map[it.areaKey].items.push(it);
    });
    return out;
  }
  function esc(s) { return String(s || '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  async function toggleItem(it, selIso) {
    const day = dayIdxFor(selIso, it.card.week_start);
    const row = it.task.days[day] || [false];
    let dot = row.findIndex(Boolean);
    if (dot < 0) dot = 0;
    if (!it.task.days[day]) it.task.days[day] = [false];
    it.task.days[day][dot] = !it.task.days[day][dot];
    await fetch('/api/routine-cards/' + it.card.week_key + '/' + it.areaKey + '/toggle', {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: it.taskIndex, day, dot, list: 'tasks' })
    });
    render();
  }
  function render() {
    if (!location.pathname.startsWith('/cards')) return;
    injectStyles();
    const cards = getAlpineCards();
    if (!cards.length) return;
    const sel = selectedDate();
    const items = collectItems(cards, sel);
    let mount = document.querySelector('#dynamic-routine-app');
    if (!mount) {
      mount = document.createElement('div');
      mount.id = 'dynamic-routine-app';
      const header = document.querySelector('.page-header');
      if (header && header.parentNode) header.parentNode.insertBefore(mount, header.nextSibling);
    }
    document.body.classList.add('dynamic-routines-active');
    const dueGroups = grouped(items, (x) => x.due);
    const done = items.filter((x) => x.completedToday);
    const upcoming = items.filter((x) => x.upcoming).slice(0, 12);
    let html = '<div class="dyn-routine-hero card"><div><p class="dyn-eyebrow">Dynamic routines</p><h2>Today / selected day</h2><p class="dyn-sub">Completing a task records the actual day done and hides stale future slots until the interval says it is due again.</p></div><a class="btn btn-sm btn-secondary" href="?legacy=1">Legacy cards</a></div>';
    html += '<div class="dyn-summary"><span>' + dueGroups.reduce((n,g)=>n+g.items.length,0) + ' due</span><span>' + done.length + ' done</span><span>' + upcoming.length + ' upcoming</span></div>';
    html += '<div class="dyn-list">';
    if (!dueGroups.length) html += '<div class="card dyn-empty">Nothing due right now.</div>';
    dueGroups.forEach((g) => {
      html += '<section class="card dyn-section"><h3>' + esc(g.areaName) + '</h3>';
      g.items.forEach((it) => { html += '<button class="dyn-task ' + esc(it.status) + '" data-key="' + esc(it.areaKey + '|' + it.name) + '"><span class="dyn-check">○</span><span><strong>' + esc(it.name) + '</strong><small>' + esc(it.label) + (it.interval ? ' · every ' + esc(it.interval) + 'd' : '') + '</small></span></button>'; });
      html += '</section>';
    });
    if (done.length) {
      html += '<section class="card dyn-section dyn-done"><h3>Done</h3>';
      done.forEach((it) => { html += '<button class="dyn-task done" data-key="' + esc(it.areaKey + '|' + it.name) + '"><span class="dyn-check">✓</span><span><strong>' + esc(it.name) + '</strong><small>' + esc(it.areaName) + '</small></span></button>'; });
      html += '</section>';
    }
    if (upcoming.length) {
      html += '<section class="card dyn-section dyn-upcoming"><h3>Coming up</h3>';
      upcoming.forEach((it) => { html += '<div class="dyn-task readonly"><span class="dyn-check">·</span><span><strong>' + esc(it.name) + '</strong><small>' + esc(it.areaName) + ' · ' + esc(it.label) + '</small></span></div>'; });
      html += '</section>';
    }
    html += '</div>';
    mount.innerHTML = html;
    mount.querySelectorAll('.dyn-task[data-key]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const key = btn.getAttribute('data-key');
        const it = items.find((x) => (x.areaKey + '|' + x.name) === key);
        if (it) toggleItem(it, sel);
      });
    });
  }
  document.addEventListener('alpine:initialized', () => setTimeout(render, 50));
  window.addEventListener('load', () => setTimeout(render, 150));
  document.addEventListener('click', () => setTimeout(render, 50));
})();
