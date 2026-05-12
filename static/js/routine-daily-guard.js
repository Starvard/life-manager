(function () {
  if (!location.pathname.startsWith('/cards')) return;

  const MS_DAY = 86400000;
  const TZ = 'America/New_York';
  const SECTION_KEY = 'lm:routine-section:';
  const DAILY_SECTION_TITLES = new Set(['Morning', 'Midday', 'Evening']);
  let applying = false;

  function parseIso(s) {
    return new Date(String(s || '').slice(0, 10) + 'T00:00:00');
  }

  function daysBetween(a, b) {
    return Math.round((parseIso(a) - parseIso(b)) / MS_DAY);
  }

  function todayIso() {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: TZ,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).formatToParts(new Date());
    const got = Object.fromEntries(parts.map((x) => [x.type, x.value]));
    return got.year + '-' + got.month + '-' + got.day;
  }

  function selectedIso() {
    const urlDate = new URLSearchParams(location.search).get('date');
    if (/^\d{4}-\d{2}-\d{2}$/.test(urlDate || '')) return urlDate;
    const input = document.querySelector('.picker-date');
    return input && input.value ? input.value : todayIso();
  }

  function isDaily(freq) {
    return Number(freq || 0) >= 7;
  }

  function dayIndex(dateIso, weekStartIso) {
    return Math.max(0, Math.min(6, daysBetween(dateIso, weekStartIso)));
  }

  function esc(s) {
    return String(s || '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    }[c]));
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

  function dailyBucket(name, dot, total, areaKey) {
    const sectionOverride = localStorage.getItem(SECTION_KEY + areaKey + '::' + name);
    if (sectionOverride) return sectionOverride;
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

  function dailyCount(task) {
    // The visible daily stack must not depend on the selected day's saved dot
    // array. That array only stores completion state. The count comes from the
    // configured routine and the most complete generated week shape.
    const freqCount = Math.max(1, Math.round(Number(task.freq || 7) / 7));
    const scheduledMax = Math.max(0, ...(task.scheduled || []).map((n) => Number(n || 0)));
    const rowMax = Math.max(0, ...(task.days || []).map((row) => Array.isArray(row) ? row.length : 0));
    return Math.max(1, freqCount, scheduledMax, rowMax);
  }

  function displayName(baseName, dot, total) {
    return total > 1 ? String(baseName || '') + ' ' + String(dot + 1) : String(baseName || '');
  }

  function displayNameForBase(name, base, total) {
    if (name === base) return true;
    for (let i = 1; i <= total; i++) {
      if (name === displayName(base, i - 1, total)) return true;
    }
    return false;
  }

  function dailyColumn() {
    const app = document.getElementById('dynamic-routine-app');
    if (!app) return null;

    const existing = app.querySelector('.eff-daily-column');
    if (existing) return existing;

    const columns = app.querySelector('.eff-columns');
    if (columns) {
      const column = document.createElement('div');
      column.className = 'eff-column eff-daily-column';
      const flexColumn = columns.querySelector('.eff-flex-column');
      columns.insertBefore(column, flexColumn || columns.firstElementChild || null);
      return column;
    }

    const list = app.querySelector('.eff-list');
    if (list) {
      const column = document.createElement('div');
      column.className = 'eff-column eff-daily-column';
      list.insertBefore(column, list.firstElementChild || null);
      return column;
    }

    const fallback = app.querySelector('.eff-column');
    if (fallback) {
      fallback.classList.add('eff-daily-column');
      return fallback;
    }

    const column = document.createElement('div');
    column.className = 'eff-column eff-daily-column';
    app.appendChild(column);
    return column;
  }

  function sectionTitle(section) {
    return (section.querySelector('h3 span')?.textContent || '').trim();
  }

  function cleanupEmptyDailySections() {
    document.querySelectorAll('#dynamic-routine-app .eff-section').forEach((section) => {
      const title = sectionTitle(section);
      if (!DAILY_SECTION_TITLES.has(title)) return;
      if (!section.querySelector('.eff-task')) section.remove();
    });
  }

  function ensureSection(title) {
    const column = dailyColumn();
    if (!column) return null;
    let section = Array.from(column.querySelectorAll(':scope > .eff-section')).find((sec) => sectionTitle(sec) === title);
    if (section) return section;
    section = document.createElement('section');
    section.className = 'card eff-section';
    section.innerHTML = '<h3><span>' + esc(title) + '</span><small>0</small></h3>';
    const order = ['Morning', 'Midday', 'Evening'];
    const nextTitle = order.slice(order.indexOf(title) + 1).find((name) => {
      return Array.from(column.querySelectorAll(':scope > .eff-section')).some((sec) => sectionTitle(sec) === name);
    });
    const before = nextTitle
      ? Array.from(column.querySelectorAll(':scope > .eff-section')).find((sec) => sectionTitle(sec) === nextTitle)
      : null;
    column.insertBefore(section, before || null);
    return section;
  }

  function buttonInfo(btn) {
    const name = (btn.querySelector('strong')?.textContent || '').trim();
    const small = (btn.querySelector('small')?.textContent || '').trim();
    const area = small.split(' · ').pop()?.trim() || '';
    return { name, area };
  }

  function configuredDailyTasks(cards) {
    const rows = [];
    cards.forEach((card) => {
      const areaKey = card.area_key || '';
      const areaName = card.area_name || areaKey;
      (card.tasks || []).forEach((task, taskIndex) => {
        if (!isDaily(task.freq)) return;
        rows.push({ card, areaKey, areaName, task, taskIndex, total: dailyCount(task) });
      });
    });
    return rows;
  }

  function removeExistingDailyRows(configured) {
    const byArea = new Map();
    configured.forEach((row) => {
      if (!byArea.has(row.areaName)) byArea.set(row.areaName, []);
      byArea.get(row.areaName).push(row);
    });

    document.querySelectorAll('#dynamic-routine-app [data-row-kind="daily"]').forEach((btn) => {
      const info = buttonInfo(btn);
      const candidates = byArea.get(info.area) || [];
      const match = candidates.some((row) => displayNameForBase(info.name, row.task.name, row.total));
      if (match) btn.remove();
    });
  }

  function updateSectionCount(section) {
    const count = section.querySelectorAll('.eff-task').length;
    const small = section.querySelector('h3 small');
    if (small && small.textContent !== String(count)) small.textContent = String(count);
  }

  function updateDailySummary() {
    const allDaily = document.querySelectorAll('#dynamic-routine-app [data-row-kind="daily"]');
    const doneDaily = document.querySelectorAll('#dynamic-routine-app [data-row-kind="daily"].done');
    const summaryDone = document.querySelector('[data-daily-done-count]');
    const text = doneDaily.length + '/' + allDaily.length + ' daily done';
    if (summaryDone && summaryDone.textContent !== text) summaryDone.textContent = text;
  }

  async function saveDot(card, areaKey, task, taskIndex, day, dot, btn, areaName) {
    if (!task.days[day]) task.days[day] = [];
    while (task.days[day].length <= dot) task.days[day].push(false);
    const next = !task.days[day][dot];
    task.days[day][dot] = next;

    btn.classList.toggle('done', next);
    btn.classList.toggle('daily', !next);
    const check = btn.querySelector('.eff-check');
    const small = btn.querySelector('small');
    if (check) check.textContent = next ? '✓' : '○';
    if (small) small.textContent = (next ? 'Done today' : 'Due today') + ' · ' + areaName;
    updateDailySummary();

    await fetch('/api/routine-cards/' + encodeURIComponent(card.week_key) + '/' + encodeURIComponent(areaKey) + '/set-dot', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: taskIndex, day, dot, value: next, list: 'tasks' }),
    });
  }

  function makeButton(card, areaKey, areaName, task, taskIndex, day, dot, total, bucket) {
    const done = !!((task.days || [])[day] || [])[dot];
    const name = displayName(task.name, dot, total);
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'eff-task ' + (done ? 'done' : 'daily');
    btn.setAttribute('data-row-kind', 'daily');
    btn.setAttribute('data-daily-guard', '1');
    btn.setAttribute('data-daily-base-name', task.name || '');
    btn.setAttribute('data-daily-dot', String(dot));
    btn.innerHTML = '<span class="eff-check">' + (done ? '✓' : '○') + '</span><span><strong>' + esc(name) + '</strong><small>' + esc((done ? 'Done today' : 'Due today') + ' · ' + areaName) + '</small></span>';
    btn.addEventListener('click', () => saveDot(card, areaKey, task, taskIndex, day, dot, btn, areaName));
    btn.addEventListener('contextmenu', (e) => e.preventDefault());
    const section = ensureSection(bucket);
    if (section) {
      section.appendChild(btn);
      updateSectionCount(section);
    }
  }

  function ensureDailyRows() {
    if (applying) return;
    const app = document.getElementById('dynamic-routine-app');
    if (!app) return;
    const cards = alpineCards();
    if (!cards.length) return;

    applying = true;
    const selected = selectedIso();
    const configured = configuredDailyTasks(cards);

    // Rebuild only the configured daily rows. Flexible/recurring rows are left
    // alone so overdue/coming-up logic keeps working.
    removeExistingDailyRows(configured);
    cleanupEmptyDailySections();
    dailyColumn();

    configured.forEach(({ card, areaKey, areaName, task, taskIndex, total }) => {
      const day = dayIndex(selected, card.week_start);
      for (let dot = 0; dot < total; dot++) {
        const bucket = dailyBucket(task.name, dot, total, areaKey);
        makeButton(card, areaKey, areaName, task, taskIndex, day, dot, total, bucket);
      }
    });

    cleanupEmptyDailySections();
    document.querySelectorAll('#dynamic-routine-app .eff-section').forEach(updateSectionCount);
    updateDailySummary();
    applying = false;
    document.dispatchEvent(new CustomEvent('lm:routine-daily-guard-applied', { detail: { rebuilt: configured.length } }));
  }

  function schedule() {
    // Bounded reconciliation passes allow the main dynamic stack to finish its
    // late render, then replace only daily rows with a stable named set.
    [150, 450, 900, 1600, 2600, 4200, 6500, 9000].forEach((ms) => setTimeout(ensureDailyRows, ms));
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', schedule);
  else schedule();
  window.addEventListener('load', schedule);
  document.addEventListener('alpine:initialized', schedule);
})();
