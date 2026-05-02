(function () {
  if (!location.pathname.startsWith('/cards')) return;

  const MS_DAY = 86400000;
  const LOOKBACK_WEEKS = 60;

  function parseIso(s) { return new Date(String(s || '').slice(0, 10) + 'T00:00:00'); }
  function iso(d) { return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }
  function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
  function daysBetween(a, b) { return Math.round((parseIso(a) - parseIso(b)) / MS_DAY); }
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

  function parseDateFromSmallText(text) {
    const due = String(text || '').match(/Due\s+([A-Za-z]{3}),?\s+([A-Za-z]{3})\s+(\d{1,2})/i);
    if (!due) return null;
    const selectedYear = parseIso(selectedIso()).getFullYear();
    const parsed = new Date(due[1] + ' ' + due[2] + ' ' + due[3] + ' ' + selectedYear + ' 00:00:00');
    if (Number.isNaN(parsed.getTime())) return null;
    let out = iso(parsed);
    // If the parsed date is wildly before the selected date, it probably belongs to next year.
    if (daysBetween(out, selectedIso()) < -180) out = iso(addDays(parsed, 365));
    return out;
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

  function itemKey(item) { return item.areaKey + '::' + item.name; }

  function addHistoryFromCard(card, weekKey, hist, selectedDate) {
    const areaKey = card.area_key || '';
    if (!areaKey || !card.week_start) return;
    (card.tasks || []).forEach((task) => {
      const key = areaKey + '::' + task.name;
      (task.days || []).forEach((row, di) => {
        if (!(row || []).some(Boolean)) return;
        const doneIso = iso(addDays(parseIso(card.week_start), di));
        if (doneIso > selectedDate) return;
        if (!hist[key]) hist[key] = [];
        hist[key].push(doneIso);
      });
    });
  }

  async function fetchWeek(wk) {
    return fetch('/api/routine-cards/' + encodeURIComponent(wk))
      .then((r) => r.ok ? r.json() : { areas: {} })
      .then((data) => data.areas || {})
      .catch(() => ({}));
  }

  async function loadRecentHistory(selectedDate) {
    const weeksResp = await fetch('/api/routine-cards/weeks')
      .then((r) => r.ok ? r.json() : { weeks: [] })
      .catch(() => ({ weeks: [] }));
    const selectedWeek = weekKeyFor(parseIso(selectedDate));
    const weeks = Array.from(new Set(weeksResp.weeks || []))
      .filter((w) => String(w) <= selectedWeek)
      .sort()
      .slice(-LOOKBACK_WEEKS);

    const hist = {};
    for (let i = 0; i < weeks.length; i += 8) {
      const chunk = weeks.slice(i, i + 8);
      const areasByWeek = await Promise.all(chunk.map(fetchWeek));
      areasByWeek.forEach((areas, idx) => {
        const wk = chunk[idx];
        Object.values(areas || {}).forEach((card) => addHistoryFromCard(card, wk, hist, selectedDate));
      });
      // Yield so the phone can paint/respond between chunks.
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
    alpineCards().forEach((card) => addHistoryFromCard(card, card.week_key, hist, selectedDate));
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

  function dueFor(item, hist, selectedDate) {
    const completions = (hist[itemKey(item)] || []).filter((d) => d <= selectedDate).sort();
    if (completions.includes(selectedDate)) return null;
    const last = completions.length ? completions[completions.length - 1] : null;
    if (last) return iso(addDays(parseIso(last), intervalDays(item.freq)));
    const sched = scheduledDates(item);
    return sched.find((d) => d >= selectedDate) || iso(addDays(parseIso(selectedDate), intervalDays(item.freq)));
  }

  function distanceLabel(selectedDate, dueIso) {
    const delta = daysBetween(dueIso, selectedDate);
    if (delta === 0) return 'today';
    if (delta === 1) return 'tomorrow';
    if (delta > 1) return 'in ' + delta + ' days';
    const overdue = Math.abs(delta);
    return overdue + ' day' + (overdue === 1 ? '' : 's') + ' overdue';
  }

  function ensureComingUpSection(flexCol) {
    let section = Array.from(flexCol.querySelectorAll('.eff-section')).find((sec) => {
      return (sec.querySelector('h3 span')?.textContent || '').trim() === 'Coming Up';
    });
    if (section) return section;
    section = document.createElement('section');
    section.className = 'card eff-section';
    section.innerHTML = '<h3><span>Coming Up</span><small>0</small></h3>';
    const done = Array.from(flexCol.querySelectorAll('.eff-section')).find((sec) => (sec.querySelector('h3 span')?.textContent || '').trim() === 'Done Today');
    const add = flexCol.querySelector('.eff-add-card');
    flexCol.insertBefore(section, done || add || null);
    return section;
  }

  function findExistingButton(flexCol, item) {
    return Array.from(flexCol.querySelectorAll('.eff-task')).find((btn) => {
      const name = (btn.querySelector('strong')?.textContent || '').trim();
      const small = btn.querySelector('small')?.textContent || '';
      return name === item.name && small.includes(item.areaName);
    });
  }

  async function completeOnSelectedDay(item, selectedDate) {
    const day = Math.max(0, Math.min(6, daysBetween(selectedDate, item.card.week_start)));
    if (!item.task.days[day]) item.task.days[day] = [false];
    let dot = item.task.days[day].findIndex((v) => !v);
    if (dot < 0) dot = item.task.days[day].length;
    while (item.task.days[day].length <= dot) item.task.days[day].push(false);
    item.task.days[day][dot] = true;
    await fetch('/api/routine-cards/' + item.card.week_key + '/' + item.areaKey + '/set-dot', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: item.taskIndex, day, dot, value: true, list: 'tasks' }),
    });
    if (location.pathname === '/cards/day') location.href = '/cards/day?date=' + encodeURIComponent(selectedDate);
    else location.reload();
  }

  function appendFutureButton(section, item, dueIso, selectedDate) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'eff-task upcoming';
    btn.setAttribute('data-row-kind', 'flex');
    btn.setAttribute('data-due-iso', dueIso);
    btn.innerHTML = '<span class="eff-check">○</span><span><strong>' + esc(item.name) + '</strong><small>Due ' + esc(dateLabel(dueIso)) + ' · ' + esc(distanceLabel(selectedDate, dueIso)) + ' · tap if done on this viewed day · ' + esc(item.areaName) + '</small></span>';
    btn.addEventListener('click', () => completeOnSelectedDay(item, selectedDate));
    section.appendChild(btn);
  }

  function setDueIsoOnExistingButton(btn, dueIso) {
    btn.setAttribute('data-due-iso', dueIso);
  }

  function sortComingUp(section) {
    const tasks = Array.from(section.querySelectorAll('.eff-task'));
    tasks.forEach((btn) => {
      if (btn.getAttribute('data-due-iso')) return;
      const dueIso = parseDateFromSmallText(btn.querySelector('small')?.textContent || '');
      if (dueIso) btn.setAttribute('data-due-iso', dueIso);
    });
    tasks.sort((a, b) => {
      const ad = a.getAttribute('data-due-iso') || '9999-12-31';
      const bd = b.getAttribute('data-due-iso') || '9999-12-31';
      const an = (a.querySelector('strong')?.textContent || '').trim();
      const bn = (b.querySelector('strong')?.textContent || '').trim();
      return ad.localeCompare(bd) || an.localeCompare(bn);
    });
    tasks.forEach((task) => section.appendChild(task));
    const small = section.querySelector('h3 small');
    if (small) small.textContent = String(tasks.length);
    const summary = Array.from(document.querySelectorAll('.eff-summary span')).find((s) => /coming up/i.test(s.textContent || ''));
    if (summary) summary.textContent = tasks.length + ' coming up';
  }

  async function addFutureComingUp() {
    const app = document.getElementById('dynamic-routine-app');
    const flexCol = app?.querySelector('.eff-flex-column');
    if (!app || !flexCol || app.dataset.futureComingUpLoaded === '1') return;
    app.dataset.futureComingUpLoaded = 'loading';

    const cards = alpineCards();
    if (!cards.length) return;
    const selectedDate = selectedIso();
    const section = ensureComingUpSection(flexCol);

    // Sort immediately so the page stays responsive, then append far-future items after history loads.
    sortComingUp(section);

    const hist = await loadRecentHistory(selectedDate);
    catalogFrom(cards).forEach((item) => {
      const dueIso = dueFor(item, hist, selectedDate);
      if (!dueIso) return;
      const existing = findExistingButton(flexCol, item);
      if (existing) {
        setDueIsoOnExistingButton(existing, dueIso);
        return;
      }
      appendFutureButton(section, item, dueIso, selectedDate);
    });
    sortComingUp(section);
    app.dataset.futureComingUpLoaded = '1';
  }

  function schedule() {
    setTimeout(addFutureComingUp, 900);
    setTimeout(addFutureComingUp, 1800);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', schedule);
  else schedule();
  window.addEventListener('load', schedule);
  document.addEventListener('alpine:initialized', schedule);
})();
