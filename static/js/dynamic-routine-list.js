(function () {
  if (new URLSearchParams(location.search).get('legacy') === '1') return;
  const BUCKETS = ['Morning / Start Here', 'Daytime', 'Evening', 'Lower Priority / Due Soon'];
  const WONT_BUCKET = "Won't Do";
  const OVERRIDE_PREFIX = 'lm:routine-bucket:';
  const WONT_PREFIX = 'lm:routine-wont-do:';

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
      .dyn-sub { margin:0; color:var(--text-muted); line-height:1.35; max-width:42rem; }
      .dyn-hero-actions { display:flex; flex-direction:column; align-items:flex-end; gap:.45rem; min-width:max-content; }
      .dyn-recent { display:flex; flex-wrap:wrap; gap:.4rem; margin:.35rem 0 1rem; }
      .dyn-recent a { border:1px solid rgba(148,163,184,.2); border-radius:999px; padding:.35rem .6rem; background:rgba(255,255,255,.035); color:inherit; text-decoration:none; font-size:.82rem; }
      .dyn-summary { display:flex; gap:.5rem; flex-wrap:wrap; margin:.65rem 0 1rem; }
      .dyn-summary span { border:1px solid rgba(148,163,184,.2); border-radius:999px; padding:.35rem .65rem; background:rgba(255,255,255,.04); font-size:.82rem; color:var(--text-muted); }
      .dyn-list { display:grid; gap:.85rem; }
      .dyn-section { padding:.9rem; }
      .dyn-section h3 { margin:0 0 .65rem; font-size:1rem; display:flex; justify-content:space-between; gap:.75rem; }
      .dyn-section h3 small { font-weight:500; color:var(--text-muted); }
      .dyn-task { width:100%; display:flex; align-items:center; gap:.7rem; border:1px solid rgba(148,163,184,.18); border-radius:.9rem; padding:.7rem .75rem; margin:.45rem 0; background:rgba(255,255,255,.035); color:inherit; text-align:left; cursor:pointer; touch-action:manipulation; }
      .dyn-task.overdue { border-color:rgba(251,146,60,.42); background:rgba(251,146,60,.08); }
      .dyn-task.due { border-color:rgba(250,204,21,.28); background:rgba(250,204,21,.05); }
      .dyn-task.done { border-color:rgba(134,239,172,.32); background:rgba(134,239,172,.07); }
      .dyn-task.wont { border-color:rgba(148,163,184,.25); background:rgba(148,163,184,.06); opacity:.72; }
      .dyn-task.readonly { cursor:default; opacity:.85; }
      .dyn-task strong { display:block; font-size:.95rem; }
      .dyn-task small { display:block; color:var(--text-muted); margin-top:.15rem; }
      .dyn-check { display:grid; place-items:center; flex:0 0 1.6rem; width:1.6rem; height:1.6rem; border-radius:999px; background:rgba(255,255,255,.06); font-weight:800; }
      .dyn-empty { padding:1rem; color:var(--text-muted); }
      @media (max-width:640px){ .dyn-routine-hero{display:block}.dyn-hero-actions{align-items:flex-start;margin-top:.75rem}.dyn-task{padding:.8rem} }
    `;
    document.head.appendChild(style);
  }

  function parseDate(s) { return new Date(String(s || '').slice(0, 10) + 'T00:00:00'); }
  function iso(d) { return d.toISOString().slice(0, 10); }
  function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
  function daysBetween(a, b) { return Math.round((parseDate(a) - parseDate(b)) / 86400000); }
  function intervalDays(freq) { const f = Number(freq || 0); if (f <= 0) return 9999; if (f >= 7) return 1; return Math.max(1, Math.round(7 / f)); }
  function scheduledCount(task, di) { const n = Number((task.scheduled || [])[di] || 0); return Number.isFinite(n) ? Math.max(0, Math.floor(n)) : 0; }
  function selectedDate() { const inp = document.querySelector('.picker-date'); if (inp && inp.value) return inp.value; return iso(new Date()); }
  function dayIdxFor(dateStr, weekStart) { return Math.max(0, Math.min(6, daysBetween(dateStr, weekStart))); }
  function taskKey(areaKey, taskName) { return areaKey + '::' + taskName; }
  function overrideKey(areaKey, taskName, instance) { return OVERRIDE_PREFIX + taskKey(areaKey, taskName) + '::' + instance; }
  function wontKey(areaKey, taskName, instance, dayIso) { return WONT_PREFIX + dayIso + '::' + taskKey(areaKey, taskName) + '::' + instance; }
  function getOverride(areaKey, taskName, instance) { try { return localStorage.getItem(overrideKey(areaKey, taskName, instance)); } catch (_) { return null; } }
  function setOverride(areaKey, taskName, instance, bucket) { try { const key = overrideKey(areaKey, taskName, instance); if (!bucket) localStorage.removeItem(key); else localStorage.setItem(key, bucket); } catch (_) {} }
  function isWontDo(it, dayIso) { try { return localStorage.getItem(wontKey(it.areaKey, it.rawName, it.instance, dayIso)) === '1'; } catch (_) { return false; } }
  function setWontDo(it, dayIso, value) { try { const key = wontKey(it.areaKey, it.rawName, it.instance, dayIso); if (value) localStorage.setItem(key, '1'); else localStorage.removeItem(key); } catch (_) {} }

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
  function ordinal(n) { return ['First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth'][n - 1] || ('#' + n); }
  function inferredBucket(name, instance, total, interval, status) {
    const n = String(name || '').toLowerCase();
    if (status === 'overdue' && interval >= 7) return 'Lower Priority / Due Soon';
    if (n.includes('water')) { if (instance <= 1) return 'Morning / Start Here'; if (instance <= 3) return 'Daytime'; return 'Evening'; }
    if (n.includes('brush') || n.includes('floss')) return instance <= 1 ? 'Morning / Start Here' : 'Evening';
    if (n.includes('coffee') || n.includes('breakfast') || n.includes('vitamin') || n.includes('med')) return 'Morning / Start Here';
    if (n.includes('dinner') || n.includes('evening') || n.includes('trash') || n.includes('dish')) return 'Evening';
    if (interval <= 2) return 'Morning / Start Here';
    if (interval <= 4) return 'Daytime';
    return 'Lower Priority / Due Soon';
  }
  function bucketFor(areaKey, name, instance, total, interval, status) { return getOverride(areaKey, name, instance) || inferredBucket(name, instance, total, interval, status); }
  function bucketRank(bucket) { return {'Morning / Start Here':10,'Daytime':20,'Evening':30,'Lower Priority / Due Soon':40,"Won't Do":80,'Done Today':90,'Coming Up':95}[bucket] || 50; }

  function collectItems(cards, selIso) {
    const hist = scanCompletions(cards);
    const items = [];
    cards.forEach(({ card, areaKey }) => {
      const weekStart = card.week_start;
      const selectedDayIdx = dayIdxFor(selIso, weekStart);
      (card.tasks || []).forEach((task, taskIndex) => {
        const key = taskKey(areaKey, task.name);
        const rowToday = (task.days || [])[selectedDayIdx] || [];
        const completedTodayCount = rowToday.filter(Boolean).length;
        const todaySlots = Math.max(scheduledCount(task, selectedDayIdx), rowToday.length > 1 ? rowToday.length : 0);
        const interval = intervalDays(task.freq);
        const name = task.name;
        if (todaySlots > 1 || Number(task.freq || 0) >= 7) {
          const count = Math.max(1, todaySlots || Math.round(Number(task.freq || 7) / 7));
          for (let instance = 1; instance <= count; instance++) {
            const done = completedTodayCount >= instance;
            let bucket = done ? 'Done Today' : bucketFor(areaKey, name, instance, count, interval, 'due');
            const item = {card, areaKey, areaName: card.area_name || areaKey, task, taskIndex, name: count > 1 ? (ordinal(instance) + ' ' + name) : name, rawName: name, instance, dotIndex: instance - 1, completedToday: done, due: !done, upcoming: false, nextDue: selIso, interval, status: done ? 'done' : 'due', label: bucket, bucket, sort: bucketRank(bucket) * 100 + instance};
            if (!done && isWontDo(item, selIso)) { item.bucket = WONT_BUCKET; item.status = 'wont'; item.due = false; item.wontDo = true; item.sort = bucketRank(WONT_BUCKET) * 100 + instance; }
            items.push(item);
          }
          return;
        }
        const completions = (hist[key] || []).filter((d) => d <= selIso);
        const lastDone = completions.length ? completions[completions.length - 1] : null;
        const completedToday = completions.includes(selIso);
        let nextDue = lastDone ? iso(addDays(parseDate(lastDone), interval)) : null;
        const scheduled = [];
        (task.scheduled || []).forEach((count, di) => { if (Number(count || 0) > 0) scheduled.push(iso(addDays(parseDate(weekStart), di))); });
        const pastSched = scheduled.filter((d) => d <= selIso).sort();
        const futureSched = scheduled.filter((d) => d > selIso).sort();
        if (!nextDue) nextDue = pastSched[0] || futureSched[0] || selIso;
        const due = nextDue <= selIso && !completedToday;
        const upcoming = nextDue > selIso && daysBetween(nextDue, selIso) <= 7;
        if (!due && !upcoming && !completedToday) return;
        const status = completedToday ? 'done' : (due ? (nextDue < selIso ? 'overdue' : 'due') : 'upcoming');
        const bucket = completedToday ? 'Done Today' : (upcoming ? 'Coming Up' : bucketFor(areaKey, name, 1, 1, interval, status));
        const item = {card, areaKey, areaName: card.area_name || areaKey, task, taskIndex, name, rawName: name, instance: 1, dotIndex: 0, completedToday, due, upcoming, nextDue, interval, status, label: friendlyDue(nextDue, selIso), bucket, sort: bucketRank(bucket) * 100 + (status === 'overdue' ? 0 : interval)};
        if (!completedToday && due && isWontDo(item, selIso)) { item.bucket = WONT_BUCKET; item.status = 'wont'; item.due = false; item.wontDo = true; item.sort = bucketRank(WONT_BUCKET) * 100 + interval; }
        items.push(item);
      });
    });
    items.sort((a, b) => a.sort - b.sort || a.areaName.localeCompare(b.areaName) || a.name.localeCompare(b.name));
    return items;
  }
  function groupedByBucket(items, pred) {
    const out = [], map = {};
    items.filter(pred).forEach((it) => { if (!map[it.bucket]) { map[it.bucket] = { bucket: it.bucket, items: [] }; out.push(map[it.bucket]); } map[it.bucket].items.push(it); });
    out.sort((a, b) => bucketRank(a.bucket) - bucketRank(b.bucket));
    return out;
  }
  function esc(s) { return String(s || '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  async function toggleItem(it, selIso) {
    if (it.wontDo) { setWontDo(it, selIso, false); render(); return; }
    const day = dayIdxFor(selIso, it.card.week_start);
    const dot = Math.max(0, it.dotIndex || 0);
    if (!it.task.days[day]) it.task.days[day] = [false];
    while (it.task.days[day].length <= dot) it.task.days[day].push(false);
    it.task.days[day][dot] = !it.task.days[day][dot];
    await fetch('/api/routine-cards/' + it.card.week_key + '/' + it.areaKey + '/toggle', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task: it.taskIndex, day, dot, list: 'tasks' }) });
    render();
  }
  function editTiming(it, selIso) {
    const current = it.wontDo ? WONT_BUCKET : (getOverride(it.areaKey, it.rawName, it.instance) || it.bucket);
    const promptText = 'Move "' + it.name + '" to:\n1 Morning / Start Here\n2 Daytime\n3 Evening\n4 Lower Priority / Due Soon\n5 Won\'t Do today\n0 Reset automatic\n\nCurrent: ' + current;
    const answer = window.prompt(promptText, '');
    if (answer === null) return;
    const trimmed = String(answer).trim().toLowerCase();
    let bucket = null, wont = false, reset = false;
    if (trimmed === '1' || trimmed.includes('morning')) bucket = BUCKETS[0];
    else if (trimmed === '2' || trimmed.includes('day')) bucket = BUCKETS[1];
    else if (trimmed === '3' || trimmed.includes('evening')) bucket = BUCKETS[2];
    else if (trimmed === '4' || trimmed.includes('lower') || trimmed.includes('soon')) bucket = BUCKETS[3];
    else if (trimmed === '5' || trimmed.includes('wont') || trimmed.includes("won't") || trimmed.includes('skip')) wont = true;
    else if (trimmed === '0' || trimmed.includes('reset') || trimmed === '') reset = true;
    else return;
    if (wont) { setWontDo(it, selIso, true); }
    else { setWontDo(it, selIso, false); setOverride(it.areaKey, it.rawName, it.instance, reset ? null : bucket); }
    render();
  }
  function taskHtml(it, readonly) {
    const moved = getOverride(it.areaKey, it.rawName, it.instance) ? ' · custom timing' : '';
    const wont = it.wontDo ? ' · not marked done' : '';
    const small = it.completedToday ? it.areaName : ((it.wontDo ? WONT_BUCKET : it.label) + moved + wont + (it.interval && it.interval < 30 ? ' · every ' + it.interval + 'd' : '') + ' · ' + it.areaName);
    return '<' + (readonly ? 'div' : 'button') + ' class="dyn-task ' + esc(it.status) + (readonly ? ' readonly' : '') + '" ' + (readonly ? '' : 'data-key="' + esc(it.areaKey + '|' + it.rawName + '|' + it.instance) + '"') + '><span class="dyn-check">' + (it.completedToday ? '✓' : (it.wontDo ? '−' : (readonly ? '·' : '○'))) + '</span><span><strong>' + esc(it.name) + '</strong><small>' + esc(small) + '</small></span></' + (readonly ? 'div' : 'button') + '>';
  }
  function recentLinks(sel) {
    const base = parseDate(sel), links = ['<a href="/cards">Today</a>'];
    for (let i = 1; i <= 7; i++) { const d = iso(addDays(base, -i)); links.push('<a href="/cards/day?date=' + d + '">' + (i === 1 ? 'Yesterday' : i + ' days ago') + '</a>'); }
    return '<div class="dyn-recent">' + links.join('') + '</div>';
  }
  function render() {
    if (!location.pathname.startsWith('/cards')) return;
    injectStyles();
    const cards = getAlpineCards();
    if (!cards.length) return;
    const sel = selectedDate();
    const items = collectItems(cards, sel);
    let mount = document.querySelector('#dynamic-routine-app');
    if (!mount) { mount = document.createElement('div'); mount.id = 'dynamic-routine-app'; const header = document.querySelector('.page-header'); if (header && header.parentNode) header.parentNode.insertBefore(mount, header.nextSibling); }
    document.body.classList.add('dynamic-routines-active');
    const activeGroups = groupedByBucket(items, (x) => x.due && !x.completedToday && !x.wontDo);
    const wontGroups = groupedByBucket(items, (x) => x.wontDo);
    const done = items.filter((x) => x.completedToday);
    const upcoming = items.filter((x) => x.upcoming).slice(0, 12);
    const activeCount = activeGroups.reduce((n, g) => n + g.items.length, 0);
    let html = '<div class="dyn-routine-hero card"><div><p class="dyn-eyebrow">Today Stack</p><h2>Do this in order</h2><p class="dyn-sub">Use Recent to fix the last week. Long-press an item to move it or mark it won\'t do for today.</p></div><div class="dyn-hero-actions"></div></div>';
    html += recentLinks(sel);
    html += '<div class="dyn-summary"><span>' + activeCount + ' active</span><span>' + done.length + ' done</span><span>' + wontGroups.reduce((n,g)=>n+g.items.length,0) + ' won\'t do</span><span>' + upcoming.length + ' upcoming</span></div>';
    html += '<div class="dyn-list">';
    if (!activeGroups.length) html += '<div class="card dyn-empty">Nothing active right now.</div>';
    activeGroups.forEach((g) => { html += '<section class="card dyn-section"><h3><span>' + esc(g.bucket) + '</span><small>' + g.items.length + '</small></h3>'; g.items.forEach((it) => { html += taskHtml(it, false); }); html += '</section>'; });
    if (done.length) { html += '<section class="card dyn-section dyn-done"><h3><span>Done Today</span><small>' + done.length + '</small></h3>'; done.forEach((it) => { html += taskHtml(it, false); }); html += '</section>'; }
    if (wontGroups.length) { html += '<section class="card dyn-section"><h3><span>Won\'t Do</span><small>' + wontGroups.reduce((n,g)=>n+g.items.length,0) + '</small></h3>'; wontGroups.forEach((g) => g.items.forEach((it) => { html += taskHtml(it, false); })); html += '</section>'; }
    if (upcoming.length) { html += '<section class="card dyn-section dyn-upcoming"><h3><span>Coming Up</span><small>' + upcoming.length + '</small></h3>'; upcoming.forEach((it) => { html += taskHtml(it, true); }); html += '</section>'; }
    html += '</div>';
    mount.innerHTML = html;
    mount.querySelectorAll('.dyn-task[data-key]').forEach((btn) => {
      let longPressTimer = null, longPressed = false;
      const key = btn.getAttribute('data-key');
      const itemForKey = () => items.find((x) => (x.areaKey + '|' + x.rawName + '|' + x.instance) === key);
      btn.addEventListener('pointerdown', () => { longPressed = false; clearTimeout(longPressTimer); longPressTimer = setTimeout(() => { const it = itemForKey(); if (it) { longPressed = true; editTiming(it, sel); } }, 650); });
      ['pointerup', 'pointercancel', 'pointerleave'].forEach((evt) => btn.addEventListener(evt, () => clearTimeout(longPressTimer)));
      btn.addEventListener('contextmenu', (e) => { e.preventDefault(); const it = itemForKey(); if (it) editTiming(it, sel); });
      btn.addEventListener('click', (e) => { if (longPressed) { e.preventDefault(); longPressed = false; return; } const it = itemForKey(); if (it) toggleItem(it, sel); });
    });
  }
  document.addEventListener('alpine:initialized', () => setTimeout(render, 50));
  window.addEventListener('load', () => setTimeout(render, 150));
  document.addEventListener('click', () => setTimeout(render, 50));
})();
