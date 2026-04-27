(function () {
  const TZ = 'America/New_York';
  let applying = false;

  function parseDate(s) { return new Date(String(s || '').slice(0, 10) + 'T00:00:00'); }
  function iso(d) { const y = d.getFullYear(); const m = String(d.getMonth() + 1).padStart(2, '0'); const day = String(d.getDate()).padStart(2, '0'); return y + '-' + m + '-' + day; }
  function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
  function daysBetween(a, b) { return Math.round((parseDate(a) - parseDate(b)) / 86400000); }
  function intervalDays(freq) { const f = Number(freq || 0); if (f <= 0) return 9999; if (f >= 7) return 1; return Math.max(1, Math.round(7 / f)); }
  function labelDate(s) { return parseDate(s).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC' }); }
  function esc(s) { return String(s || '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function easternParts(d) {
    const parts = new Intl.DateTimeFormat('en-US', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(d);
    const got = Object.fromEntries(parts.map((p) => [p.type, p.value]));
    return { year: got.year, month: got.month, day: got.day };
  }
  function easternTodayIso() { const p = easternParts(new Date()); return p.year + '-' + p.month + '-' + p.day; }
  function selectedDate() { const inp = document.querySelector('.picker-date'); if (inp && inp.value) return inp.value; return easternTodayIso(); }
  function dayIdxFor(dateStr, weekStart) { return Math.max(0, Math.min(6, daysBetween(dateStr, weekStart))); }
  function taskKey(areaKey, taskName) { return areaKey + '::' + taskName; }

  function getCards() {
    const cards = [];
    if (!window.Alpine) return cards;
    document.querySelectorAll('.notecard[x-data]').forEach((el) => {
      let data;
      try { data = window.Alpine.$data(el); } catch (_) { return; }
      if (!data || !data.card || !Array.isArray(data.card.tasks)) return;
      cards.push({ card: data.card, areaKey: data.card.area_key || '' });
    });
    return cards;
  }

  function scanCompletions(cards, selIso) {
    const hist = {};
    cards.forEach(({ card }) => {
      const weekStart = card.week_start;
      const areaKey = card.area_key || '';
      (card.tasks || []).forEach((task) => {
        const key = taskKey(areaKey, task.name);
        (task.days || []).forEach((row, di) => {
          const d = iso(addDays(parseDate(weekStart), di));
          if (d > selIso) return;
          if ((row || []).some(Boolean)) {
            if (!hist[key]) hist[key] = [];
            hist[key].push(d);
          }
        });
      });
    });
    Object.keys(hist).forEach((k) => hist[k].sort());
    return hist;
  }

  function scheduledDates(task, weekStart) {
    const out = [];
    (task.scheduled || []).forEach((count, di) => {
      if (Number(count || 0) > 0) out.push(iso(addDays(parseDate(weekStart), di)));
    });
    return out.sort();
  }

  function isActiveSection(node) {
    const section = node.closest('.dyn-section');
    const title = section && section.querySelector('h3 span');
    const name = title ? title.textContent.trim() : '';
    return !['Done Today', "Won't Do", 'Coming Up', 'Overdue'].includes(name);
  }

  function collectTruth(cards, selIso) {
    const hist = scanCompletions(cards, selIso);
    const truth = new Map();
    const missingDue = [];

    cards.forEach(({ card, areaKey }) => {
      const weekStart = card.week_start;
      const selectedDayIdx = dayIdxFor(selIso, weekStart);
      (card.tasks || []).forEach((task, taskIndex) => {
        const freq = Number(task.freq || 0);
        if (freq >= 7) return;
        const rowToday = (task.days || [])[selectedDayIdx] || [];
        const completedToday = rowToday.some(Boolean);
        const interval = intervalDays(task.freq);
        const name = task.name || '';
        const key = taskKey(areaKey, name);
        const completions = (hist[key] || []).filter((d) => d <= selIso);
        const lastDone = completions.length ? completions[completions.length - 1] : null;
        const nextByCompletion = lastDone ? iso(addDays(parseDate(lastDone), interval)) : null;
        const sched = scheduledDates(task, weekStart);
        const pastSched = sched.filter((d) => d <= selIso);
        const futureSched = sched.filter((d) => d > selIso);

        let dueDate = null;
        if (nextByCompletion && nextByCompletion <= selIso && !completedToday) {
          dueDate = nextByCompletion;
        }

        pastSched.forEach((d) => {
          if (completedToday) return;
          if (lastDone && d <= lastDone) return;
          if (nextByCompletion && d < nextByCompletion) return;
          if (!dueDate || d < dueDate) dueDate = d;
        });

        if (!dueDate && !lastDone && pastSched.length && !completedToday) dueDate = pastSched[0];

        const upcomingDate = !dueDate && !completedToday ? (nextByCompletion || futureSched[0] || null) : null;
        const due = Boolean(dueDate && dueDate <= selIso && !completedToday);
        const domKey = areaKey + '|' + name + '|1';
        truth.set(domKey, { due, dueDate, upcomingDate, lastDone, completedToday });

        if (due) {
          missingDue.push({
            card, areaKey, areaName: card.area_name || areaKey, task, taskIndex,
            name, domKey, dueDate, interval
          });
        }
      });
    });

    return { truth, missingDue };
  }

  async function completeOnSelectedDay(it, selIso) {
    const day = dayIdxFor(selIso, it.card.week_start);
    const dot = 0;
    if (!it.task.days[day]) it.task.days[day] = [false];
    while (it.task.days[day].length <= dot) it.task.days[day].push(false);
    it.task.days[day][dot] = true;
    await fetch('/api/routine-cards/' + it.card.week_key + '/' + it.areaKey + '/toggle', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: it.taskIndex, day, dot, list: 'tasks' })
    });
    document.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    setTimeout(apply, 150);
  }

  function removeStaleDueButtons(truth) {
    document.querySelectorAll('#dynamic-routine-app .dyn-task[data-key]').forEach((node) => {
      const key = node.getAttribute('data-key');
      const info = truth.get(key);
      if (!info || info.due || info.completedToday || !isActiveSection(node)) return;
      node.remove();
    });
  }

  function renderMissingDue(items, selIso) {
    const app = document.querySelector('#dynamic-routine-app');
    const list = app && app.querySelector('.dyn-list');
    if (!list) return;
    const existing = list.querySelector('.dyn-schedule-fix-section');
    if (existing) existing.remove();

    const already = new Set(Array.from(list.querySelectorAll('.dyn-task[data-key]')).map((n) => n.getAttribute('data-key')));
    const missing = items.filter((it) => !already.has(it.domKey));
    if (!missing.length) return;

    const section = document.createElement('section');
    section.className = 'card dyn-section dyn-schedule-fix-section';
    section.innerHTML = '<h3><span>Overdue</span><small>' + missing.length + '</small></h3>' + missing.map((it, idx) => {
      const overdueText = daysBetween(selIso, it.dueDate) === 0 ? 'Due today' : 'Due ' + labelDate(it.dueDate);
      const nextText = 'tap done → next due ' + labelDate(iso(addDays(parseDate(selIso), it.interval)));
      return '<button type="button" class="dyn-task overdue" data-schedule-fix-index="' + idx + '"><span class="dyn-check">○</span><span><strong>' + esc(it.name) + '</strong><small>' + esc(overdueText + ' · ' + nextText + ' · every ' + it.interval + 'd · ' + it.areaName) + '</small></span></button>';
    }).join('');
    list.insertBefore(section, list.firstChild);
    section.querySelectorAll('[data-schedule-fix-index]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const item = missing[Number(btn.getAttribute('data-schedule-fix-index'))];
        if (item) completeOnSelectedDay(item, selIso);
      });
    });
  }

  function cleanupEmptyActiveSections() {
    document.querySelectorAll('#dynamic-routine-app .dyn-section').forEach((section) => {
      const title = section.querySelector('h3 span');
      const name = title ? title.textContent.trim() : '';
      if (['Done Today', "Won't Do", 'Coming Up', 'Overdue'].includes(name)) return;
      if (!section.querySelector('.dyn-task')) section.remove();
      const count = section.querySelector('h3 small');
      if (count) count.textContent = String(section.querySelectorAll('.dyn-task').length);
    });
  }

  function apply() {
    if (applying || !location.pathname.startsWith('/cards')) return;
    const app = document.querySelector('#dynamic-routine-app');
    const cards = getCards();
    if (!app || !cards.length) return;
    applying = true;
    try {
      const selIso = selectedDate();
      const { truth, missingDue } = collectTruth(cards, selIso);
      removeStaleDueButtons(truth);
      renderMissingDue(missingDue, selIso);
      cleanupEmptyActiveSections();
    } finally {
      applying = false;
    }
  }

  document.addEventListener('alpine:initialized', () => setTimeout(apply, 100));
  window.addEventListener('load', () => setTimeout(apply, 100));
  document.addEventListener('click', () => setTimeout(apply, 180));
  new MutationObserver(() => setTimeout(apply, 0)).observe(document.documentElement, { childList: true, subtree: true });
})();
