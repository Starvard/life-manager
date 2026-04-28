(function () {
  const TZ = 'America/New_York';
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
      body.dynamic-routines-active .cards-today-score,
      body.dynamic-routines-active .picker,
      body.dynamic-routines-active .view-toggle { display: none !important; }
      #dynamic-routine-app { margin: 1rem 0 1.5rem; }
      .routine-subtabs { display:flex; gap:.4rem; flex-wrap:wrap; margin:.25rem 0 .85rem; }
      .routine-subtabs a { border:1px solid var(--border); border-radius:999px; padding:.42rem .7rem; color:var(--text-muted); text-decoration:none; background:rgba(255,255,255,.035); font-size:.78rem; font-weight:700; }
      .routine-subtabs a.active { color:white; border-color:rgba(99,179,255,.34); background:rgba(99,179,255,.16); }
      .dyn-routine-hero { display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; padding:1rem; margin-bottom:.8rem; }
      .dyn-routine-hero h2 { margin:.1rem 0 .25rem; font-size:1.25rem; }
      .dyn-date { margin:0 0 .1rem; font-size:.95rem; color:var(--text-muted); font-weight:700; }
      .dyn-eyebrow { margin:0; text-transform:uppercase; letter-spacing:.08em; font-size:.72rem; color:var(--text-muted); font-weight:800; }
      .dyn-sub { margin:0; color:var(--text-muted); line-height:1.35; max-width:42rem; }
      .dyn-hero-actions { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:.45rem; min-width:max-content; }
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
      .dyn-task.upcoming { border-color:rgba(148,163,184,.2); background:rgba(148,163,184,.04); }
      .dyn-task.done { border-color:rgba(134,239,172,.32); background:rgba(134,239,172,.07); }
      .dyn-task.wont { border-color:rgba(148,163,184,.25); background:rgba(148,163,184,.06); opacity:.72; }
      .dyn-task.readonly { cursor:default; opacity:.85; }
      .dyn-task strong { display:block; font-size:.95rem; }
      .dyn-task small { display:block; color:var(--text-muted); margin-top:.15rem; }
      .dyn-check { display:grid; place-items:center; flex:0 0 1.6rem; width:1.6rem; height:1.6rem; border-radius:999px; background:rgba(255,255,255,.06); font-weight:800; }
      .dyn-empty { padding:1rem; color:var(--text-muted); }
      .dyn-sheet-backdrop { position:fixed; inset:0; z-index:9998; background:rgba(0,0,0,.42); display:flex; align-items:flex-end; justify-content:center; padding:1rem; }
      .dyn-sheet { width:min(520px, 100%); border:1px solid rgba(148,163,184,.22); border-radius:1.25rem; background:rgb(15,23,42); box-shadow:0 24px 80px rgba(0,0,0,.45); padding:1rem; }
      .dyn-sheet h3 { margin:0; font-size:1.05rem; }
      .dyn-sheet p { margin:.25rem 0 .8rem; color:var(--text-muted); font-size:.86rem; line-height:1.35; }
      .dyn-sheet-actions { display:grid; gap:.5rem; }
      .dyn-sheet-btn { width:100%; border:1px solid rgba(148,163,184,.22); border-radius:.9rem; padding:.8rem .85rem; background:rgba(255,255,255,.045); color:inherit; text-align:left; font-weight:700; }
      .dyn-sheet-btn small { display:block; margin-top:.16rem; color:var(--text-muted); font-weight:500; }
      .dyn-sheet-btn.wont { border-color:rgba(251,146,60,.36); background:rgba(251,146,60,.08); }
      .dyn-sheet-btn.cancel { text-align:center; background:transparent; color:var(--text-muted); }
      @media (max-width:640px){ .dyn-routine-hero{display:block}.dyn-hero-actions{justify-content:flex-start;margin-top:.75rem}.dyn-task{padding:.8rem}.dyn-sheet-backdrop{padding:.6rem}.dyn-sheet{border-radius:1.1rem} }
    `;
    document.head.appendChild(style);
  }

  function easternParts(d) {
    const parts = new Intl.DateTimeFormat('en-US', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(d);
    const got = Object.fromEntries(parts.map((p) => [p.type, p.value]));
    return { year: got.year, month: got.month, day: got.day };
  }
  function easternTodayIso() { const p = easternParts(new Date()); return p.year + '-' + p.month + '-' + p.day; }
  function parseDate(s) { return new Date(String(s || '').slice(0, 10) + 'T00:00:00'); }
  function iso(d) { const y = d.getFullYear(); const m = String(d.getMonth() + 1).padStart(2, '0'); const day = String(d.getDate()).padStart(2, '0'); return y + '-' + m + '-' + day; }
  function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
  function daysBetween(a, b) { return Math.round((parseDate(a) - parseDate(b)) / 86400000); }
  function labelDate(s, long) { return parseDate(s).toLocaleDateString('en-US', long ? { weekday: 'long', month: 'long', day: 'numeric', timeZone: 'UTC' } : { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC' }); }
  function intervalDays(freq) { const f = Number(freq || 0); if (f <= 0) return 9999; if (f >= 7) return 1; return Math.max(1, Math.round(7 / f)); }
  function scheduledCount(task, di) { const n = Number((task.scheduled || [])[di] || 0); return Number.isFinite(n) ? Math.max(0, Math.floor(n)) : 0; }
  function selectedDate() { const inp = document.querySelector('.picker-date'); if (inp && inp.value) return inp.value; return easternTodayIso(); }
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
            const d = iso(addDays(parseDate(weekStart), di));
            if (!hist[key]) hist[key] = [];
            hist[key].push(d);
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
    if (delta < 7) return labelDate(dueIso, false);
    return labelDate(dueIso, false);
  }
  function ordinal(n) { return ['First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth', 'Seventh', 'Eighth'][n - 1] || ('#' + n); }
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
  function bucketRank(bucket) { return {'Overdue':5,'Morning / Start Here':10,'Daytime':20,'Evening':30,'Lower Priority / Due Soon':40,"Won't Do":80,'Done Today':90,'Coming Up':95}[bucket] || 50; }

  function scheduledDates(task, weekStart) {
    const out = [];
    (task.scheduled || []).forEach((count, di) => {
      if (Number(count || 0) > 0) out.push(iso(addDays(parseDate(weekStart), di)));
    });
    return out.sort();
  }

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
        const interval = intervalDays(task.freq);
        const name = task.name;
        const areaName = card.area_name || areaKey;
        const freq = Number(task.freq || 0);
        const todaySlots = Math.max(scheduledCount(task, selectedDayIdx), rowToday.length > 1 ? rowToday.length : 0);

        if (todaySlots > 1 || freq >= 7) {
          const count = Math.max(1, todaySlots || Math.round(freq / 7) || 1);
          for (let instance = 1; instance <= count; instance++) {
            const done = completedTodayCount >= instance;
            const status = done ? 'done' : 'due';
            let bucket = done ? 'Done Today' : bucketFor(areaKey, name, instance, count, interval, status);
            const item = { card, areaKey, areaName, task, taskIndex, name: count > 1 ? (ordinal(instance) + ' ' + name) : name, rawName: name, instance, dotIndex: instance - 1, completedToday: done, due: !done, upcoming: false, nextDue: selIso, interval, status, label: done ? 'Done' : bucket, bucket, sort: bucketRank(bucket) * 100 + instance };
            if (!done && isWontDo(item, selIso)) { item.bucket = WONT_BUCKET; item.status = 'wont'; item.due = false; item.wontDo = true; item.sort = bucketRank(WONT_BUCKET) * 100 + instance; }
            items.push(item);
          }
          return;
        }

        const completions = (hist[key] || []).filter((d) => d <= selIso);
        const completedToday = completions.includes(selIso);
        const lastDone = completions.length ? completions[completions.length - 1] : null;
        const nextByCompletion = lastDone ? iso(addDays(parseDate(lastDone), interval)) : null;
        const sched = scheduledDates(task, weekStart);
        const pastSched = sched.filter((d) => d <= selIso);
        const futureSched = sched.filter((d) => d > selIso);
        let dueDate = null;

        if (!completedToday && nextByCompletion && nextByCompletion <= selIso) {
          dueDate = nextByCompletion;
        }
        pastSched.forEach((d) => {
          if (completedToday) return;
          if (lastDone && d <= lastDone) return;
          if (nextByCompletion && d < nextByCompletion) return;
          if (!dueDate || d < dueDate) dueDate = d;
        });
        if (!dueDate && !lastDone && pastSched.length && !completedToday) dueDate = pastSched[0];

        let nextDue = dueDate || null;
        if (!nextDue) nextDue = nextByCompletion || futureSched[0] || null;
        if (!nextDue && completedToday) nextDue = iso(addDays(parseDate(selIso), interval));
        if (!nextDue) return;

        const due = Boolean(dueDate && dueDate <= selIso && !completedToday);
        const upcoming = !due && !completedToday && nextDue > selIso && daysBetween(nextDue, selIso) <= 14;
        if (!due && !upcoming && !completedToday) return;

        const status = completedToday ? 'done' : (due ? (dueDate < selIso ? 'overdue' : 'due') : 'upcoming');
        const bucket = completedToday ? 'Done Today' : (upcoming ? 'Coming Up' : (status === 'overdue' ? 'Overdue' : bucketFor(areaKey, name, 1, 1, interval, status)));
        const item = { card, areaKey, areaName, task, taskIndex, name, rawName: name, instance: 1, dotIndex: 0, completedToday, due, upcoming, nextDue, interval, status, label: completedToday ? ('Next due ' + labelDate(nextDue, false)) : friendlyDue(nextDue, selIso), bucket, sort: bucketRank(bucket) * 100 + (status === 'overdue' ? daysBetween(selIso, nextDue) : interval) };
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
    const next = !it.task.days[day][dot];
    it.task.days[day][dot] = next;
    await fetch('/api/routine-cards/' + it.card.week_key + '/' + it.areaKey + '/set-dot', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task: it.taskIndex, day, dot, value: next, list: 'tasks' }) });
    render();
  }
  function applyAction(it, selIso, action) {
    if (!it || !action) return;
    if (action === 'wont') { setWontDo(it, selIso, true); }
    else if (action === 'reset') { setWontDo(it, selIso, false); setOverride(it.areaKey, it.rawName, it.instance, null); }
    else if (BUCKETS.includes(action)) { setWontDo(it, selIso, false); setOverride(it.areaKey, it.rawName, it.instance, action); }
    render();
  }
  function closeActionSheet() { const old = document.querySelector('.dyn-sheet-backdrop'); if (old) old.remove(); }
  function editTiming(it, selIso) {
    closeActionSheet();
    const current = it.wontDo ? WONT_BUCKET : (getOverride(it.areaKey, it.rawName, it.instance) || it.bucket);
    const wrap = document.createElement('div');
    wrap.className = 'dyn-sheet-backdrop';
    wrap.innerHTML = '<div class="dyn-sheet" role="dialog" aria-modal="true"><h3>Routine action</h3><p>' + esc(it.name) + ' · current: ' + esc(current) + '</p><div class="dyn-sheet-actions">' +
      BUCKETS.map((b) => '<button type="button" class="dyn-sheet-btn" data-action="' + esc(b) + '">' + esc(b) + '<small>Move this item to this section</small></button>').join('') +
      '<button type="button" class="dyn-sheet-btn wont" data-action="wont">Won\'t Do Today<small>Move to the bottom without marking done</small></button>' +
      '<button type="button" class="dyn-sheet-btn" data-action="reset">Reset Automatic<small>Clear custom timing and won\'t-do state</small></button>' +
      '<button type="button" class="dyn-sheet-btn cancel" data-action="cancel">Cancel</button>' +
      '</div></div>';
    wrap.addEventListener('click', (e) => {
      if (e.target === wrap) { closeActionSheet(); return; }
      const btn = e.target.closest('[data-action]');
      if (!btn) return;
      const action = btn.getAttribute('data-action');
      closeActionSheet();
      if (action !== 'cancel') applyAction(it, selIso, action);
    });
    document.body.appendChild(wrap);
  }
  function taskHtml(it, readonly) {
    const moved = getOverride(it.areaKey, it.rawName, it.instance) ? ' · custom timing' : '';
    const wont = it.wontDo ? ' · not marked done' : '';
    const next = it.completedToday && it.nextDue ? ' · ' + it.label : '';
    const small = it.completedToday ? ('Done' + next + ' · ' + it.areaName) : ((it.wontDo ? WONT_BUCKET : it.label) + moved + wont + (it.interval && it.interval < 30 ? ' · every ' + it.interval + 'd' : '') + ' · ' + it.areaName);
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
    const upcoming = items.filter((x) => x.upcoming).slice(0, 20);
    const activeCount = activeGroups.reduce((n, g) => n + g.items.length, 0);
    const todayIso = easternTodayIso();
    const isToday = sel === todayIso;
    let html = '<nav class="routine-subtabs" aria-label="Routine views"><a class="active" href="/cards">Today Stack</a><a href="/routines?view=calendar">Calendar</a><a href="/routines">Manage</a></nav>';
    html += '<div class="dyn-routine-hero card"><div><p class="dyn-eyebrow">Routines · Eastern Time</p><p class="dyn-date">' + esc(labelDate(sel, true)) + (isToday ? ' · Today' : '') + '</p><h2>Do this in order</h2><p class="dyn-sub">Tap to complete the selected day. Long-press for timing, reset, or won\'t-do. Completing late moves the next due date forward from the day you actually did it.</p></div><div class="dyn-hero-actions"><a class="btn btn-secondary btn-sm" href="/routines?view=calendar">Calendar</a><a class="btn btn-secondary btn-sm" href="/routines">Manage routines</a></div></div>';
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
  document.addEventListener('alpine:initialized', () => setTimeout(render, 0));
  window.addEventListener('load', () => setTimeout(render, 0));
  document.addEventListener('click', () => setTimeout(render, 50));
})();
