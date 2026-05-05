(function () {
  if (!location.pathname.startsWith('/cards')) return;

  const MS_DAY = 86400000;
  const TZ = 'America/New_York';
  const SECTION_KEY = 'lm:routine-section:';
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

  function taskKey(areaName, taskName) {
    return String(areaName || '') + '::' + String(taskName || '');
  }

  function existingDailyCounts() {
    const counts = new Map();
    document.querySelectorAll('#dynamic-routine-app [data-row-kind="daily"]').forEach((btn) => {
      const name = (btn.querySelector('strong')?.textContent || '').trim();
      const small = (btn.querySelector('small')?.textContent || '').trim();
      const area = small.split(' · ').pop()?.trim() || '';
      const key = taskKey(area, name);
      counts.set(key, (counts.get(key) || 0) + 1);
    });
    return counts;
  }

  function dailyColumn() {
    return document.querySelector('#dynamic-routine-app .eff-daily-column')
      || document.querySelector('#dynamic-routine-app .eff-column');
  }

  function ensureSection(title) {
    const column = dailyColumn();
    if (!column) return null;
    let section = Array.from(column.querySelectorAll('.eff-section')).find((sec) => {
      return (sec.querySelector('h3 span')?.textContent || '').trim() === title;
    });
    if (section) return section;
    section = document.createElement('section');
    section.className = 'card eff-section';
    section.innerHTML = '<h3><span>' + esc(title) + '</span><small>0</small></h3>';
    const order = ['Morning', 'Midday', 'Evening'];
    const nextTitle = order.slice(order.indexOf(title) + 1).find((name) => {
      return Array.from(column.querySelectorAll('.eff-section')).some((sec) => (sec.querySelector('h3 span')?.textContent || '').trim() === name);
    });
    const before = nextTitle
      ? Array.from(column.querySelectorAll('.eff-section')).find((sec) => (sec.querySelector('h3 span')?.textContent || '').trim() === nextTitle)
      : null;
    column.insertBefore(section, before || null);
    return section;
  }

  function updateSectionCount(section) {
    const count = section.querySelectorAll('.eff-task[data-row-kind="daily"]').length;
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

  function makeButton(card, areaKey, areaName, task, taskIndex, day, dot, bucket) {
    const done = !!((task.days || [])[day] || [])[dot];
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'eff-task ' + (done ? 'done' : 'daily');
    btn.setAttribute('data-row-kind', 'daily');
    btn.setAttribute('data-daily-guard', '1');
    btn.innerHTML = '<span class="eff-check">' + (done ? '✓' : '○') + '</span><span><strong>' + esc(task.name) + '</strong><small>' + esc((done ? 'Done today' : 'Due today') + ' · ' + areaName) + '</small></span>';
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
    const counts = existingDailyCounts();
    let added = 0;

    cards.forEach((card) => {
      const areaKey = card.area_key || '';
      const areaName = card.area_name || areaKey;
      (card.tasks || []).forEach((task, taskIndex) => {
        if (!isDaily(task.freq)) return;
        const day = dayIndex(selected, card.week_start);
        const row = (task.days || [])[day] || [];
        const scheduled = Number((task.scheduled || [])[day] || 0);
        const needed = Math.max(1, scheduled, row.length);
        const key = taskKey(areaName, task.name);
        const have = counts.get(key) || 0;
        for (let dot = have; dot < needed; dot++) {
          const bucket = dailyBucket(task.name, dot, needed, areaKey);
          makeButton(card, areaKey, areaName, task, taskIndex, day, dot, bucket);
          counts.set(key, (counts.get(key) || 0) + 1);
          added += 1;
        }
      });
    });

    document.querySelectorAll('#dynamic-routine-app .eff-section').forEach(updateSectionCount);
    updateDailySummary();
    applying = false;

    if (added > 0) {
      document.dispatchEvent(new CustomEvent('lm:routine-daily-guard-applied', { detail: { added } }));
    }
  }

  function schedule() {
    // Do bounded reconciliation passes only. This is cheap and allows the main
    // dynamic stack to finish any late render without a heavy MutationObserver.
    [150, 450, 900, 1600, 2600, 4200, 6500].forEach((ms) => setTimeout(ensureDailyRows, ms));
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', schedule);
  else schedule();
  window.addEventListener('load', schedule);
  document.addEventListener('alpine:initialized', schedule);
})();
