(function () {
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
    cards.forEach(({ data, card, areaKey }) => {
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
        items.push({ data, card, areaKey, areaName: card.area_name || areaKey, task, taskIndex, name: task.name, completedToday, due, upcoming, nextDue, status: completedToday ? 'done' : (due ? (nextDue < selIso ? 'overdue' : 'due') : 'upcoming'), label: friendlyDue(nextDue, selIso) });
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
      g.items.forEach((it) => { html += '<button class="dyn-task ' + esc(it.status) + '" data-key="' + esc(it.areaKey + '|' + it.name) + '"><span class="dyn-check">○</span><span><strong>' + esc(it.name) + '</strong><small>' + esc(it.label) + (it.task.interval_days ? ' · every ' + esc(it.task.interval_days) + 'd' : '') + '</small></span></button>'; });
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
