(function () {
  if (!location.pathname.startsWith('/cards')) return;

  const MS_DAY = 86400000;
  const TZ = 'America/New_York';
  const SECTION_KEY = 'lm:routine-section:';
  let applying = false;

  function parseIso(s) { return new Date(String(s || '').slice(0, 10) + 'T00:00:00'); }
  function daysBetween(a, b) { return Math.round((parseIso(a) - parseIso(b)) / MS_DAY); }
  function todayIso() {
    const p = new Intl.DateTimeFormat('en-US', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
    const got = Object.fromEntries(p.map((x) => [x.type, x.value]));
    return got.year + '-' + got.month + '-' + got.day;
  }
  function selectedIso() {
    const urlDate = new URLSearchParams(location.search).get('date');
    if (/^\d{4}-\d{2}-\d{2}$/.test(urlDate || '')) return urlDate;
    const input = document.querySelector('.picker-date');
    return input && input.value ? input.value : todayIso();
  }
  function dayIndex(dateIso, weekStartIso) { return Math.max(0, Math.min(6, daysBetween(dateIso, weekStartIso))); }
  function esc(s) { return String(s || '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
  function isDaily(task) { return Number(task && task.freq || 0) >= 7; }
  function expectedDailyDots(task) { return Math.max(1, Math.round(Number(task && task.freq || 0) / 7)); }

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

  function dailyBucket(name, dot, total, areaKey) {
    const override = localStorage.getItem(SECTION_KEY + areaKey + '::' + name);
    if (override) return override;
    const n = String(name || '').toLowerCase();
    if (n.includes('brush') || n.includes('floss')) return dot === 0 ? 'Morning' : 'Evening';
    if (n.includes('water')) {
      if (dot === 0) return 'Morning';
      if (dot >= Math.max(1, total - 2)) return 'Evening';
      return 'Midday';
    }
    if (n.includes('coffee') || n.includes('breakfast') || n.includes('vitamin') || n.includes('med') || n.includes('morning')) return 'Morning';
    if (n.includes('dinner') || n.includes('evening') || n.includes('bed') || n.includes('trash') || n.includes('dish')) return 'Evening';
    return 'Midday';
  }

  function dailyColumn() {
    return document.querySelector('#dynamic-routine-app .eff-daily-column') || document.querySelector('#dynamic-routine-app .eff-column');
  }

  function ensureSection(title) {
    const column = dailyColumn();
    if (!column) return null;
    let section = Array.from(column.querySelectorAll('.eff-section')).find((sec) => (sec.querySelector('h3 span')?.textContent || '').trim() === title);
    if (section) return section;
    section = document.createElement('section');
    section.className = 'card eff-section';
    section.innerHTML = '<h3><span>' + esc(title) + '</span><small>0</small></h3>';
    const order = ['Morning', 'Midday', 'Evening'];
    const nextTitle = order.slice(order.indexOf(title) + 1).find((name) => Array.from(column.querySelectorAll('.eff-section')).some((sec) => (sec.querySelector('h3 span')?.textContent || '').trim() === name));
    const before = nextTitle ? Array.from(column.querySelectorAll('.eff-section')).find((sec) => (sec.querySelector('h3 span')?.textContent || '').trim() === nextTitle) : null;
    column.insertBefore(section, before || null);
    return section;
  }

  function taskKey(areaName, taskName) { return String(areaName || '') + '::' + String(taskName || ''); }
  function keyFromButton(btn) {
    const name = (btn.querySelector('strong')?.textContent || '').trim();
    const small = (btn.querySelector('small')?.textContent || '').trim();
    const clean = small.replace(/^\d+% overdue\s*/, '').replace(/^P\d+\s*/, '');
    const bits = clean.split(' · ').map((x) => x.trim()).filter(Boolean);
    return taskKey(bits.length ? bits[bits.length - 1] : '', name);
  }

  function expectedRows() {
    const selected = selectedIso();
    const rows = [];
    alpineCards().forEach((card) => {
      const areaKey = card.area_key || '';
      const areaName = card.area_name || areaKey;
      (card.tasks || []).forEach((task, taskIndex) => {
        if (!isDaily(task)) return;
        const day = dayIndex(selected, card.week_start);
        const row = ((task.days || [])[day] || []);
        const total = expectedDailyDots(task);
        for (let dot = 0; dot < total; dot++) {
          rows.push({ card, areaKey, areaName, task, taskIndex, day, dot, total, done: !!row[dot], bucket: dailyBucket(task.name, dot, total, areaKey), key: taskKey(areaName, task.name) });
        }
      });
    });
    return rows;
  }

  function setButtonState(btn, row) {
    btn.classList.toggle('done', row.done);
    btn.classList.toggle('daily', !row.done);
    btn.setAttribute('data-row-kind', 'daily');
    btn.setAttribute('data-stable-daily-row', '1');
    btn.setAttribute('data-stable-daily-dot', String(row.dot));
    const check = btn.querySelector('.eff-check');
    const small = btn.querySelector('small');
    if (check) check.textContent = row.done ? '✓' : '○';
    if (small) small.textContent = (row.done ? 'Done today' : 'Due today') + ' · ' + row.areaName;
  }

  async function saveDot(row, btn) {
    if (!row.task.days[row.day]) row.task.days[row.day] = [];
    while (row.task.days[row.day].length <= row.dot) row.task.days[row.day].push(false);
    const next = !row.task.days[row.day][row.dot];
    row.task.days[row.day][row.dot] = next;
    row.done = next;
    setButtonState(btn, row);
    updateDailySummary();
    await fetch('/api/routine-cards/' + encodeURIComponent(row.card.week_key) + '/' + encodeURIComponent(row.areaKey) + '/set-dot', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: row.taskIndex, day: row.day, dot: row.dot, value: next, list: 'tasks' }),
    });
    setTimeout(reconcileDailyRows, 250);
  }

  function makeButton(row) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'eff-task daily';
    btn.innerHTML = '<span class="eff-check">○</span><span><strong>' + esc(row.task.name) + '</strong><small>Due today · ' + esc(row.areaName) + '</small></span>';
    btn.addEventListener('click', () => saveDot(row, btn));
    btn.addEventListener('contextmenu', (e) => e.preventDefault());
    setButtonState(btn, row);
    return btn;
  }

  function updateSectionCount(section) {
    const small = section.querySelector('h3 small');
    if (small) small.textContent = String(section.querySelectorAll('.eff-task[data-row-kind="daily"]').length);
  }

  function updateDailySummary() {
    const allDaily = document.querySelectorAll('#dynamic-routine-app .eff-task[data-row-kind="daily"]');
    const doneDaily = document.querySelectorAll('#dynamic-routine-app .eff-task[data-row-kind="daily"].done');
    const summaryDone = document.querySelector('[data-daily-done-count]');
    if (summaryDone) summaryDone.textContent = doneDaily.length + '/' + allDaily.length + ' daily done';
  }

  function reconcileDailyRows() {
    if (applying) return;
    if (!document.getElementById('dynamic-routine-app')) return;
    const rows = expectedRows();
    if (!rows.length) return;
    applying = true;

    const existing = new Map();
    document.querySelectorAll('#dynamic-routine-app .eff-task[data-row-kind="daily"]').forEach((btn) => {
      const k = keyFromButton(btn);
      if (!existing.has(k)) existing.set(k, []);
      existing.get(k).push(btn);
    });

    const expectedKeys = new Set(rows.map((row) => row.key));
    rows.forEach((row) => {
      const group = existing.get(row.key) || [];
      let btn = group.shift();
      if (!btn) btn = makeButton(row);
      else setButtonState(btn, row);
      const section = ensureSection(row.bucket);
      if (section) section.appendChild(btn);
    });

    existing.forEach((leftovers, key) => {
      if (!expectedKeys.has(key)) return;
      leftovers.forEach((btn) => btn.remove());
    });

    document.querySelectorAll('#dynamic-routine-app .eff-section').forEach(updateSectionCount);
    updateDailySummary();
    applying = false;
    document.dispatchEvent(new CustomEvent('lm:routine-stable-daily-applied'));
  }

  function schedule() { [150, 450, 900, 1600, 2600, 4200, 6500, 9000].forEach((ms) => setTimeout(reconcileDailyRows, ms)); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', schedule);
  else schedule();
  window.addEventListener('load', schedule);
  document.addEventListener('alpine:initialized', schedule);
  document.addEventListener('lm:routine-daily-guard-applied', schedule);
})();
