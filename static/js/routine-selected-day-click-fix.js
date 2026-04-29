(function () {
  if (!location.pathname.startsWith('/cards')) return;

  const MS_DAY = 86400000;
  const TZ = 'America/New_York';

  function parseIso(s) { return new Date(String(s || '').slice(0, 10) + 'T00:00:00'); }
  function daysBetween(a, b) { return Math.round((parseIso(a) - parseIso(b)) / MS_DAY); }
  function selectedIso() {
    const urlDate = new URLSearchParams(location.search).get('date');
    if (/^\d{4}-\d{2}-\d{2}$/.test(urlDate || '')) return urlDate;
    const inp = document.querySelector('.picker-date');
    if (inp && inp.value) return inp.value;
    const parts = new Intl.DateTimeFormat('en-US', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
    const got = Object.fromEntries(parts.map((p) => [p.type, p.value]));
    return got.year + '-' + got.month + '-' + got.day;
  }
  function weekKeyFor(d) {
    const x = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    const day = x.getUTCDay() || 7;
    x.setUTCDate(x.getUTCDate() + 4 - day);
    const yearStart = new Date(Date.UTC(x.getUTCFullYear(), 0, 1));
    const week = Math.ceil((((x - yearStart) / MS_DAY) + 1) / 7);
    return x.getUTCFullYear() + '-W' + String(week).padStart(2, '0');
  }
  function isDaily(freq) { return Number(freq || 0) >= 7; }
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
        if (!isDaily(task.freq)) out.push({ card, areaKey, areaName, task, taskIndex, name: task.name });
      });
    });
    return out;
  }
  function itemFromButton(btn) {
    const name = (btn.querySelector('strong')?.textContent || '').trim();
    const small = (btn.querySelector('small')?.textContent || '').trim();
    const bits = small.split(' · ').map((x) => x.trim()).filter(Boolean);
    const areaName = bits.length ? bits[bits.length - 1] : '';
    const catalog = catalogFrom(alpineCards());
    return catalog.find((it) => it.name === name && it.areaName === areaName) || catalog.find((it) => it.name === name) || null;
  }
  async function selectedWeekTarget(item, dateIso) {
    const wk = weekKeyFor(parseIso(dateIso));
    const areas = await fetch('/api/routine-cards/' + encodeURIComponent(wk))
      .then((r) => r.ok ? r.json() : { areas: {} })
      .then((data) => data.areas || {})
      .catch(() => ({}));
    let card = areas[item.areaKey];
    if (!card) card = Object.values(areas).find((c) => (c.area_name || c.area_key || '') === item.areaName) || null;
    if (!card) return item;
    const taskIndex = (card.tasks || []).findIndex((t) => t.name === item.name);
    if (taskIndex < 0) return item;
    return { card, areaKey: card.area_key || item.areaKey, task: card.tasks[taskIndex], taskIndex, name: item.name };
  }
  function reloadSameViewedDay(dateIso) {
    if (location.pathname === '/cards/day') {
      location.href = '/cards/day?date=' + encodeURIComponent(dateIso);
    } else {
      location.reload();
    }
  }
  async function writeCompletionForViewedDay(item, dateIso, value) {
    const target = await selectedWeekTarget(item, dateIso);
    const day = Math.max(0, Math.min(6, daysBetween(dateIso, target.card.week_start)));
    if (!target.task.days[day]) target.task.days[day] = [false];
    let dot = value === false ? target.task.days[day].findIndex(Boolean) : target.task.days[day].findIndex((v) => !v);
    if (dot < 0) dot = value === false ? 0 : target.task.days[day].length;
    while (target.task.days[day].length <= dot) target.task.days[day].push(false);
    target.task.days[day][dot] = value !== false;
    await fetch('/api/routine-cards/' + target.card.week_key + '/' + target.areaKey + '/set-dot', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: target.taskIndex, day, dot, value: value !== false, list: 'tasks' }),
    });
    reloadSameViewedDay(dateIso);
  }
  function bind() {
    document.querySelectorAll('.eff-flex-column .eff-task').forEach((btn) => {
      if (btn.dataset.viewedDayFixBound === '1') return;
      btn.dataset.viewedDayFixBound = '1';
      let downAt = 0;
      btn.addEventListener('pointerdown', () => { downAt = Date.now(); }, true);
      btn.addEventListener('click', async (e) => {
        if (Date.now() - downAt > 600) return;
        const item = itemFromButton(btn);
        if (!item) return;
        e.preventDefault();
        e.stopImmediatePropagation();
        await writeCompletionForViewedDay(item, selectedIso(), !btn.classList.contains('done'));
      }, true);
    });
  }
  function schedule() {
    setTimeout(bind, 250);
    setTimeout(bind, 700);
    setTimeout(bind, 1200);
  }
  window.addEventListener('load', schedule);
  document.addEventListener('alpine:initialized', schedule);
  schedule();
})();
