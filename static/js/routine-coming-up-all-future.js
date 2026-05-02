(function () {
  if (!location.pathname.startsWith('/cards')) return;

  const MS_DAY = 86400000;
  let runId = 0;

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
    const p = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
    const got = Object.fromEntries(p.map((x) => [x.type, x.value]));
    return got.year + '-' + got.month + '-' + got.day;
  }
  function selectedIso() {
    const urlDate = new URLSearchParams(location.search).get('date');
    if (/^\d{4}-\d{2}-\d{2}$/.test(urlDate || '')) return urlDate;
    const inp = document.querySelector('.picker-date');
    return inp && inp.value ? inp.value : todayIso();
  }
  function intervalDays(freq) {
    const f = Number(freq || 0);
    if (f <= 0) return 9999;
    if (f >= 7) return 1;
    return Math.max(1, Math.round(7 / f));
  }
  function isDaily(freq) { return Number(freq || 0) >= 7; }
  function esc(s) { return String(s || '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function dateLabel(dateIso) { return parseIso(dateIso).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC' }); }

  function injectStyles() {
    if (document.getElementById('routine-coming-up-all-future-styles')) return;
    const style = document.createElement('style');
    style.id = 'routine-coming-up-all-future-styles';
    style.textContent = `
      .eff-task[data-due-iso] small .eff-due-distance {
        opacity: .9;
      }
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
        if (!isDaily(freq)) {
          out.push({ card, areaKey, areaName, task, taskIndex, name: task.name, freq });
        }
      });
    });
    return out;
  }

  function itemKey(item) { return item.areaKey + '::' + item.name; }

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

  async function fetchWeek(wk) {
    return fetch('/api/routine-cards/' + encodeURIComponent(wk))
      .then((r) => r.ok ? r.json() : { areas: {} })
      .then((data) => data.areas || {})
      .catch(() => ({}));
  }

  async function loadLongHistory(selIso) {
    const sel = parseIso(selIso);
    const start = addDays(mondayFor(sel), -156 * 7); // 3 years back for annual/semiannual tasks
    const end = addDays(mondayFor(sel), 156 * 7);   // 3 years ahead for generated future cards if present
    const weeks = [];
    for (let d = new Date(start); d <= end; d = addDays(d, 7)) weeks.push(weekKeyFor(d));

    const hist = {};
    const chunkSize = 20;
    for (let i = 0; i < weeks.length; i += chunkSize) {
      const chunk = weeks.slice(i, i + chunkSize);
      const areasByWeek = await Promise.all(chunk.map(fetchWeek));
      areasByWeek.forEach((areas) => Object.values(areas || {}).forEach((card) => addHistoryFromCard(card, hist)));
    }
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

  function dueFor(item, hist, selIso) {
    const key = itemKey(item);
    const completions = (hist[key] || []).filter((d) => d <= selIso).sort();
    if (completions.includes(selIso)) return null;
    const last = completions.length ? completions[completions.length - 1] : null;
    if (last) return iso(addDays(parseIso(last), intervalDays(item.freq)));
    const sched = scheduledDates(item);
    return sched.find((d) => d >= selIso) || sched.filter((d) => d <= selIso).pop() || selIso;
  }

  function ensureComingUpSection(flexCol) {
    let section = Array.from(flexCol.querySelectorAll('.eff-section')).find((sec) => {
      return (sec.querySelector('h3 span')?.textContent || '').trim() === 'Coming Up';
    });
    if (section) return section;

    section = document.createElement('section');
    section.className = 'card eff-section';
    section.innerHTML = '<h3><span>Coming Up</span><small>0</small></h3>';
    const done = Array.from(flexCol.querySelectorAll('.eff-section')).find((sec) => {
      return (sec.querySelector('h3 span')?.textContent || '').trim() === 'Done Today';
    });
    const add = flexCol.querySelector('.eff-add-card');
    flexCol.insertBefore(section, done || add || null);
    return section;
  }

  function visibleTaskNames(flexCol) {
    return new Set(Array.from(flexCol.querySelectorAll('.eff-task strong')).map((el) => (el.textContent || '').trim()).filter(Boolean));
  }

  function findExistingButton(flexCol, item) {
    return Array.from(flexCol.querySelectorAll('.eff-task')).find((btn) => {
      const name = (btn.querySelector('strong')?.textContent || '').trim();
      const small = (btn.querySelector('small')?.textContent || '').trim();
      return name === item.name && small.includes(item.areaName);
    });
  }

  function distanceLabel(selIso, dueIso) {
    const delta = daysBetween(dueIso, selIso);
    if (delta === 0) return 'today';
    if (delta === 1) return 'tomorrow';
    if (delta > 1) return 'in ' + delta + ' days';
    const overdue = Math.abs(delta);
    return overdue + ' day' + (overdue === 1 ? '' : 's') + ' overdue';
  }

  async function completeOnSelectedDay(item, selIso) {
    const wk = weekKeyFor(parseIso(selIso));
    const areas = await fetchWeek(wk);
    let card = areas[item.areaKey];
    if (!card) card = Object.values(areas).find((c) => (c.area_name || c.area_key || '') === item.areaName) || item.card;
    const taskIndex = (card.tasks || []).findIndex((t) => t.name === item.name);
    const task = taskIndex >= 0 ? card.tasks[taskIndex] : item.task;
    const areaKey = card.area_key || item.areaKey;
    const day = Math.max(0, Math.min(6, daysBetween(selIso, card.week_start)));
    if (!task.days[day]) task.days[day] = [false];
    let dot = task.days[day].findIndex((v) => !v);
    if (dot < 0) dot = task.days[day].length;
    while (task.days[day].length <= dot) task.days[day].push(false);
    task.days[day][dot] = true;
    await fetch('/api/routine-cards/' + card.week_key + '/' + areaKey + '/set-dot', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: taskIndex >= 0 ? taskIndex : item.taskIndex, day, dot, value: true, list: 'tasks' }),
    });
    if (location.pathname === '/cards/day') location.href = '/cards/day?date=' + encodeURIComponent(selIso);
    else location.reload();
  }

  function appendFutureButton(section, item, dueIso, selIso) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'eff-task upcoming';
    btn.setAttribute('data-row-kind', 'flex');
    btn.setAttribute('data-due-iso', dueIso);
    btn.innerHTML = '<span class="eff-check">○</span><span><strong>' + esc(item.name) + '</strong><small>Due ' + esc(dateLabel(dueIso)) + ' · <span class="eff-due-distance">' + esc(distanceLabel(selIso, dueIso)) + '</span> · tap if done on this viewed day · ' + esc(item.areaName) + '</small></span>';
    btn.addEventListener('click', () => completeOnSelectedDay(item, selIso));
    section.appendChild(btn);
  }

  function setDueIsoOnExistingButton(btn, dueIso, selIso) {
    btn.setAttribute('data-due-iso', dueIso);
    const small = btn.querySelector('small');
    if (!small) return;
    if (small.querySelector('.eff-due-distance')) return;
    // Leave existing text alone, but add a machine-readable/sortable due date and clearer distance.
    if (btn.classList.contains('upcoming')) {
      small.innerHTML = esc(small.textContent || '') + ' · <span class="eff-due-distance">' + esc(distanceLabel(selIso, dueIso)) + '</span>';
    }
  }

  function sortComingUp(section) {
    const tasks = Array.from(section.querySelectorAll('.eff-task'));
    tasks.sort((a, b) => {
      const ad = a.getAttribute('data-due-iso') || '9999-12-31';
      const bd = b.getAttribute('data-due-iso') || '9999-12-31';
      const an = (a.querySelector('strong')?.textContent || '').trim();
      const bn = (b.querySelector('strong')?.textContent || '').trim();
      return ad.localeCompare(bd) || an.localeCompare(bn);
    });
    tasks.forEach((task) => section.appendChild(task));
  }

  function updateCounts(flexCol, section) {
    const count = section.querySelectorAll('.eff-task').length;
    const small = section.querySelector('h3 small');
    if (small) small.textContent = String(count);

    const summary = document.querySelectorAll('.eff-summary span');
    const upcomingSpan = Array.from(summary).find((s) => /coming up/i.test(s.textContent || ''));
    if (upcomingSpan) upcomingSpan.textContent = count + ' coming up';
  }

  async function applyAllFutureComingUp() {
    const id = ++runId;
    injectStyles();
    const app = document.getElementById('dynamic-routine-app');
    const flexCol = app?.querySelector('.eff-flex-column');
    if (!app || !flexCol || app.dataset.allFutureComingUpCore === '1') return;

    const cards = alpineCards();
    if (!cards.length) return;
    const selIso = selectedIso();
    const hist = await loadLongHistory(selIso);
    if (id !== runId) return;

    const section = ensureComingUpSection(flexCol);
    const seen = visibleTaskNames(flexCol);

    catalogFrom(cards).forEach((item) => {
      const dueIso = dueFor(item, hist, selIso);
      if (!dueIso) return;
      const existing = findExistingButton(flexCol, item);
      if (existing) {
        setDueIsoOnExistingButton(existing, dueIso, selIso);
        return;
      }
      if (seen.has(item.name)) return;
      // Anything not currently visible belongs in Coming Up, no matter how far out.
      appendFutureButton(section, item, dueIso, selIso);
      seen.add(item.name);
    });

    sortComingUp(section);
    updateCounts(flexCol, section);
    app.dataset.allFutureComingUpCore = '1';
  }

  function schedule() {
    setTimeout(applyAllFutureComingUp, 650);
    setTimeout(applyAllFutureComingUp, 1200);
    setTimeout(applyAllFutureComingUp, 2200);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', schedule);
  else schedule();
  window.addEventListener('load', schedule);
  document.addEventListener('alpine:initialized', schedule);
})();
