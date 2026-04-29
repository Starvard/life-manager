(function () {
  const MS_DAY = 86400000;
  const FUTURE_PATCH_FLAG = 'data-all-future-coming-up-applied';

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
  function selectedIso() {
    const inp = document.querySelector('.picker-date');
    if (inp && inp.value) return inp.value;
    const p = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
    const got = Object.fromEntries(p.map((x) => [x.type, x.value]));
    return got.year + '-' + got.month + '-' + got.day;
  }
  function dateLabel(dateIso) { return parseIso(dateIso).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC' }); }
  function intervalDays(freq) { const f = Number(freq || 0); if (f <= 0) return 9999; if (f >= 7) return 1; return Math.max(1, Math.round(7 / f)); }
  function isDaily(freq) { return Number(freq || 0) >= 7; }
  function esc(s) { return String(s || '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

  function polishDashboardTiles() {
    const grid = document.querySelector('.app-grid');
    if (!grid) return;

    const editTile = grid.querySelector('[data-nav-tab="edit"]');
    if (editTile) editTile.remove();

    const calendarTile = grid.querySelector('[data-nav-tab="calendar"]');
    if (calendarTile) calendarTile.remove();

    const routinesTile = grid.querySelector('[data-nav-tab="cards"]');
    if (routinesTile) {
      const name = routinesTile.querySelector('.app-tile-name');
      const desc = routinesTile.querySelector('.app-tile-desc');
      const actions = routinesTile.querySelector('.app-tile-actions');
      if (name) name.textContent = 'Routines';
      if (desc) desc.textContent = 'Today stack, calendar view, and inline routine editing.';
      if (actions) {
        actions.innerHTML = '<a href="/cards" class="btn btn-sm btn-primary">Today</a>' +
          '<a href="/routines?view=calendar" class="btn btn-sm btn-outline">Calendar</a>';
      }
    }
  }

  function injectRoutinePolishStyles() {
    if (document.getElementById('routine-mobile-column-override')) return;
    const style = document.createElement('style');
    style.id = 'routine-mobile-column-override';
    style.textContent = `
      @media (max-width: 840px) {
        .main-content { padding-left: .42rem !important; padding-right: .42rem !important; }
        #dynamic-routine-app { margin-left: -.18rem; margin-right: -.18rem; }
        .eff-columns {
          grid-template-columns: minmax(184px, .9fr) minmax(222px, 1.18fr) !important;
          gap: .42rem !important;
          overflow-x: auto;
          overscroll-behavior-x: contain;
          -webkit-overflow-scrolling: touch;
          padding-bottom: .6rem;
          scroll-snap-type: x proximity;
        }
        .eff-column { min-width: 184px; scroll-snap-align: start; gap: .5rem !important; }
        .eff-flex-column { min-width: 222px; }
        .eff-column-title, .eff-section { padding: .56rem !important; }
        .eff-task { gap: .4rem !important; padding: .54rem .45rem !important; border-radius: .68rem !important; }
        .eff-check { flex-basis: 1.28rem !important; width: 1.28rem !important; height: 1.28rem !important; font-size: .74rem !important; }
        .eff-task strong { font-size: .78rem !important; line-height: 1.08; }
        .eff-task small { font-size: .61rem !important; line-height: 1.12; }
        .eff-hero { padding: .7rem !important; }
        .eff-summary { gap: .32rem !important; }
        .eff-summary span { padding: .26rem .46rem !important; font-size: .72rem !important; }
      }
      body.routine-edit-compact .routines-push-card,
      body.routine-edit-compact .nav-tabs-pref-card,
      body.routine-edit-compact form[action$="/routines/save"] { display:none !important; }
    `;
    document.head.appendChild(style);
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
        const freq = Number(task.freq || 0);
        if (!isDaily(freq)) out.push({ card, areaKey, areaName, task, taskIndex, name: task.name, freq });
      });
    });
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

  async function loadHistory(selIso) {
    const sel = parseIso(selIso);
    const start = addDays(mondayFor(sel), -26 * 7);
    const end = addDays(mondayFor(sel), 8 * 7);
    const weeks = new Set();
    for (let d = new Date(start); d <= end; d = addDays(d, 7)) weeks.add(weekKeyFor(d));
    const areasByWeek = await Promise.all(Array.from(weeks).map((wk) => fetch('/api/routine-cards/' + encodeURIComponent(wk)).then((r) => r.ok ? r.json() : { areas: {} }).then((d) => d.areas || {}).catch(() => ({}))));
    const hist = {};
    areasByWeek.forEach((areas) => Object.values(areas || {}).forEach((card) => addHistoryFromCard(card, hist)));
    alpineCards().forEach((card) => addHistoryFromCard(card, hist));
    Object.keys(hist).forEach((k) => hist[k] = Array.from(new Set(hist[k])).sort());
    return hist;
  }

  function dueFor(item, hist, selIso) {
    const key = item.areaKey + '::' + item.name;
    const completions = (hist[key] || []).filter((d) => d <= selIso).sort();
    if (completions.includes(selIso)) return null;
    const last = completions.length ? completions[completions.length - 1] : null;
    if (last) return iso(addDays(parseIso(last), intervalDays(item.freq)));
    const sched = [];
    const start = parseIso(item.card.week_start);
    (item.task.scheduled || []).forEach((n, di) => { if (Number(n || 0) > 0) sched.push(iso(addDays(start, di))); });
    return sched.find((d) => d >= selIso) || sched.filter((d) => d <= selIso).pop() || selIso;
  }

  function ensureComingUpSection(flexCol) {
    let sec = Array.from(flexCol.querySelectorAll('.eff-section')).find((s) => (s.querySelector('h3 span')?.textContent || '').trim() === 'Coming Up');
    if (sec) return sec;
    sec = document.createElement('section');
    sec.className = 'card eff-section';
    sec.innerHTML = '<h3><span>Coming Up</span><small>0</small></h3>';
    const addCard = flexCol.querySelector('.eff-add-card');
    flexCol.insertBefore(sec, addCard || null);
    return sec;
  }

  async function completeFuture(item, selIso) {
    const di = Math.max(0, Math.min(6, daysBetween(selIso, item.card.week_start)));
    if (!item.task.days[di]) item.task.days[di] = [false];
    let dot = item.task.days[di].findIndex((v) => !v);
    if (dot < 0) dot = item.task.days[di].length;
    while (item.task.days[di].length <= dot) item.task.days[di].push(false);
    item.task.days[di][dot] = true;
    await fetch('/api/routine-cards/' + item.card.week_key + '/' + item.areaKey + '/set-dot', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: item.taskIndex, day: di, dot, value: true, list: 'tasks' }),
    });
    location.reload();
  }

  async function showAllFutureComingUp() {
    if (!location.pathname.startsWith('/cards')) return;
    const app = document.getElementById('dynamic-routine-app');
    const flexCol = app?.querySelector('.eff-flex-column');
    if (!app || !flexCol || app.getAttribute(FUTURE_PATCH_FLAG) === '1') return;
    const cards = alpineCards();
    if (!cards.length) return;
    const selIso = selectedIso();
    const hist = await loadHistory(selIso);
    const existing = new Set(Array.from(flexCol.querySelectorAll('.eff-task')).map((b) => (b.querySelector('strong')?.textContent || '').trim()));
    const future = catalogFrom(cards).map((item) => {
      const dueIso = dueFor(item, hist, selIso);
      if (!dueIso) return null;
      const inDays = -daysBetween(selIso, dueIso);
      return { item, dueIso, inDays };
    }).filter((x) => x && x.inDays > 7 && !existing.has(x.item.name));
    if (!future.length) {
      app.setAttribute(FUTURE_PATCH_FLAG, '1');
      return;
    }
    future.sort((a, b) => a.dueIso.localeCompare(b.dueIso) || a.item.name.localeCompare(b.item.name));
    const section = ensureComingUpSection(flexCol);
    const small = section.querySelector('h3 small');
    const current = Number(small?.textContent || 0);
    future.forEach((row) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'eff-task upcoming';
      btn.innerHTML = '<span class="eff-check">○</span><span><strong>' + esc(row.item.name) + '</strong><small>Due ' + esc(dateLabel(row.dueIso)) + ' · in ' + row.inDays + ' days · tap if done today · ' + esc(row.item.areaName) + '</small></span>';
      btn.addEventListener('click', () => completeFuture(row.item, selIso));
      section.appendChild(btn);
    });
    if (small) small.textContent = String(current + future.length);
    const summarySpans = app.querySelectorAll('.eff-summary span');
    if (summarySpans.length >= 4) {
      const match = (summarySpans[3].textContent || '').match(/\d+/);
      const base = match ? Number(match[0]) : 0;
      summarySpans[3].textContent = (base + future.length) + ' coming up';
    }
    app.setAttribute(FUTURE_PATCH_FLAG, '1');
  }

  function run() {
    polishDashboardTiles();
    injectRoutinePolishStyles();
    if (location.pathname === '/routines' && !location.search.includes('view=calendar')) {
      document.body.classList.add('routine-edit-compact');
      const main = document.querySelector('.main-content');
      if (main && !document.getElementById('routine-retired-manage')) {
        const div = document.createElement('div');
        div.id = 'routine-retired-manage';
        div.className = 'card';
        div.style.padding = '1rem';
        div.innerHTML = '<h2 style="margin-top:0">Routine editing moved</h2><p class="subtitle">Edit routines by long-pressing a task on the Today Stack. Add new tasks from the Add task button there.</p><a class="btn btn-primary" href="/cards">Back to Today Stack</a>';
        main.prepend(div);
      }
    }
    setTimeout(showAllFutureComingUp, 500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
  window.addEventListener('load', run);
})();
