(function () {
  const TZ = 'America/New_York';
  let applying = false;

  function parseDate(s) { return new Date(String(s || '').slice(0, 10) + 'T00:00:00'); }
  function iso(d) { const y = d.getFullYear(); const m = String(d.getMonth() + 1).padStart(2, '0'); const day = String(d.getDate()).padStart(2, '0'); return y + '-' + m + '-' + day; }
  function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
  function daysBetween(a, b) { return Math.round((parseDate(a) - parseDate(b)) / 86400000); }
  function intervalDays(freq) { const f = Number(freq || 0); if (f <= 0) return 9999; if (f >= 7) return 1; return Math.max(1, Math.round(7 / f)); }
  function scheduledCount(task, di) { const n = Number((task.scheduled || [])[di] || 0); return Number.isFinite(n) ? Math.max(0, Math.floor(n)) : 0; }
  function easternParts(d) {
    const parts = new Intl.DateTimeFormat('en-US', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(d);
    const got = Object.fromEntries(parts.map((p) => [p.type, p.value]));
    return { year: got.year, month: got.month, day: got.day };
  }
  function easternTodayIso() { const p = easternParts(new Date()); return p.year + '-' + p.month + '-' + p.day; }
  function selectedDate() { const inp = document.querySelector('.picker-date'); if (inp && inp.value) return inp.value; return easternTodayIso(); }
  function dayIdxFor(dateStr, weekStart) { return Math.max(0, Math.min(6, daysBetween(dateStr, weekStart))); }
  function labelDate(s) { return parseDate(s).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC' }); }
  function esc(s) { return String(s || '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function taskKey(areaKey, taskName) { return areaKey + '::' + taskName; }

  function getCards() {
    const cards = [];
    if (!window.Alpine) return cards;
    document.querySelectorAll('.notecard[x-data]').forEach((el) => {
      let data;
      try { data = window.Alpine.$data(el); } catch (_) { return; }
      if (!data || !data.card || !Array.isArray(data.card.tasks)) return;
      cards.push({ data, card: data.card, areaKey: data.card.area_key || '' });
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

  function collectRoutineState(cards, selIso) {
    const hist = scanCompletions(cards);
    const upcoming = [];
    const completed = [];

    cards.forEach(({ card, areaKey }) => {
      const weekStart = card.week_start;
      const selectedDayIdx = dayIdxFor(selIso, weekStart);
      (card.tasks || []).forEach((task, taskIndex) => {
        const name = task.name;
        const areaName = card.area_name || areaKey;
        const interval = intervalDays(task.freq);
        const rowToday = (task.days || [])[selectedDayIdx] || [];
        const completedToday = rowToday.some(Boolean);
        const todaySlots = Math.max(scheduledCount(task, selectedDayIdx), rowToday.length > 1 ? rowToday.length : 0);

        if (todaySlots > 1 || Number(task.freq || 0) >= 7) {
          if (completedToday) {
            completed.push({ card, areaKey, areaName, task, taskIndex, name, nextDue: iso(addDays(parseDate(selIso), 1)), interval, dotIndex: 0 });
          }
          return;
        }

        const key = taskKey(areaKey, name);
        const completions = (hist[key] || []).filter((d) => d <= selIso);
        const lastDone = completions.length ? completions[completions.length - 1] : null;
        const isDoneToday = completions.includes(selIso);
        let nextDue = lastDone ? iso(addDays(parseDate(lastDone), interval)) : null;
        const scheduled = [];
        (task.scheduled || []).forEach((count, di) => { if (Number(count || 0) > 0) scheduled.push(iso(addDays(parseDate(weekStart), di))); });
        const pastSched = scheduled.filter((d) => d <= selIso).sort();
        const futureSched = scheduled.filter((d) => d > selIso).sort();
        if (!nextDue) nextDue = pastSched[0] || futureSched[0] || selIso;

        if (isDoneToday) {
          completed.push({ card, areaKey, areaName, task, taskIndex, name, nextDue, interval, dotIndex: 0 });
        } else if (nextDue > selIso) {
          upcoming.push({ card, areaKey, areaName, task, taskIndex, name, nextDue, interval, dotIndex: 0 });
        }
      });
    });

    upcoming.sort((a, b) => daysBetween(a.nextDue, b.nextDue) || a.areaName.localeCompare(b.areaName) || a.name.localeCompare(b.name));
    return { upcoming, completed };
  }

  async function toggleEarly(it, selIso) {
    const day = dayIdxFor(selIso, it.card.week_start);
    const dot = Math.max(0, it.dotIndex || 0);
    if (!it.task.days[day]) it.task.days[day] = [false];
    while (it.task.days[day].length <= dot) it.task.days[day].push(false);
    it.task.days[day][dot] = true;
    await fetch('/api/routine-cards/' + it.card.week_key + '/' + it.areaKey + '/toggle', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: it.taskIndex, day, dot, list: 'tasks' })
    });
    document.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    setTimeout(apply, 120);
  }

  function renderUpcoming(list, selIso) {
    const app = document.querySelector('#dynamic-routine-app');
    const dynList = app && app.querySelector('.dyn-list');
    if (!dynList) return;
    const old = dynList.querySelector('.dyn-upcoming');
    if (old) old.remove();
    if (!list.length) return;

    const section = document.createElement('section');
    section.className = 'card dyn-section dyn-upcoming dyn-upcoming-full';
    section.innerHTML = '<h3><span>Coming Up</span><small>' + list.length + '</small></h3>' + list.map((it, idx) => {
      const dueText = 'Due ' + labelDate(it.nextDue);
      const upToDate = 'tap early → next due ' + labelDate(iso(addDays(parseDate(selIso), it.interval)));
      return '<button type="button" class="dyn-task upcoming" data-upcoming-index="' + idx + '"><span class="dyn-check">○</span><span><strong>' + esc(it.name) + '</strong><small>' + esc(dueText + ' · ' + upToDate + ' · every ' + it.interval + 'd · ' + it.areaName) + '</small></span></button>';
    }).join('');
    dynList.appendChild(section);
    section.querySelectorAll('[data-upcoming-index]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const item = list[Number(btn.getAttribute('data-upcoming-index'))];
        if (item) toggleEarly(item, selIso);
      });
    });
  }

  function enhanceDone(done) {
    const doneSection = Array.from(document.querySelectorAll('.dyn-section')).find((section) => {
      const title = section.querySelector('h3 span');
      return title && title.textContent.trim() === 'Done Today';
    });
    if (!doneSection) return;
    const byNameArea = new Map(done.map((it) => [it.name + '|' + it.areaName, it]));
    doneSection.querySelectorAll('.dyn-task.done').forEach((node) => {
      const name = (node.querySelector('strong') || {}).textContent || '';
      const small = node.querySelector('small');
      if (!small) return;
      const area = small.textContent.trim();
      const it = byNameArea.get(name + '|' + area);
      if (!it || !it.nextDue) return;
      small.textContent = 'Done · next due ' + labelDate(it.nextDue) + ' · up to date until then · ' + area;
    });
  }

  function apply() {
    if (applying || !location.pathname.startsWith('/cards')) return;
    const cards = getCards();
    const app = document.querySelector('#dynamic-routine-app');
    if (!cards.length || !app) return;
    applying = true;
    try {
      const selIso = selectedDate();
      const state = collectRoutineState(cards, selIso);
      renderUpcoming(state.upcoming, selIso);
      enhanceDone(state.completed);
    } finally {
      applying = false;
    }
  }

  document.addEventListener('alpine:initialized', () => setTimeout(apply, 50));
  window.addEventListener('load', () => setTimeout(apply, 50));
  document.addEventListener('click', () => setTimeout(apply, 150));
  new MutationObserver(() => setTimeout(apply, 0)).observe(document.documentElement, { childList: true, subtree: true });
})();
