(function () {
  if (!location.pathname.startsWith('/cards')) return;

  const ORDER_KEY = 'lm:routine-daily-order:';

  function esc(s) {
    return String(s || '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function intervalDays(freq) {
    const f = Number(freq || 0);
    if (f <= 0) return 9999;
    if (f >= 7) return 1;
    return Math.max(1, Math.round(7 / f));
  }

  function injectStyles() {
    if (document.getElementById('routine-order-priority-styles')) return;
    const style = document.createElement('style');
    style.id = 'routine-order-priority-styles';
    style.textContent = `
      .eff-flex-column .eff-task[data-overdue-pct] {
        border-left-color: var(--overdue-rail, rgba(251,146,60,.8)) !important;
        background: var(--overdue-bg, rgba(251,146,60,.06)) !important;
        box-shadow: var(--overdue-shadow, none) !important;
      }
      .eff-flex-column .eff-task[data-overdue-pct] strong { color: var(--overdue-text, inherit); }
      .eff-flex-column .eff-task[data-overdue-pct] .eff-check {
        background: var(--overdue-check-bg, rgba(251,146,60,.16)) !important;
        color: var(--overdue-check-text, #fed7aa) !important;
      }
      .eff-overdue-pill {
        display: inline-block;
        margin-right: .28rem;
        border-radius: 999px;
        padding: .05rem .32rem;
        font-size: .62rem;
        font-weight: 900;
        background: var(--overdue-pill-bg, rgba(251,146,60,.16));
        color: var(--overdue-pill-text, #fed7aa);
      }
      .lm-order-priority-help { margin: -.25rem 0 .25rem !important; color: var(--text-muted); font-size: .7rem !important; }
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
        out.push({ card, areaKey, areaName, task, taskIndex, name: task.name, freq: Number(task.freq || 0) });
      });
    });
    return out;
  }

  function catalog() { return catalogFrom(alpineCards()); }

  function getTaskInfoFromButton(btn) {
    const name = (btn.querySelector('strong')?.textContent || '').trim();
    const small = (btn.querySelector('small')?.textContent || '').trim();
    const clean = small.replace(/^P\d+\s*/, '').replace(/^\d+% overdue\s*/, '');
    const bits = clean.split(' · ').map((x) => x.trim()).filter(Boolean);
    const area = bits.length ? bits[bits.length - 1] : 'default';
    const isDailyTask = btn.getAttribute('data-row-kind') === 'daily' || !!btn.closest('.eff-daily-column');
    return { name, area, isDaily: isDailyTask };
  }

  function key(prefix, info) { return prefix + info.area + '::' + info.name; }

  function getExplicitOrder(info) {
    const n = Number(localStorage.getItem(key(ORDER_KEY, info)) || '');
    return Number.isFinite(n) && n > 0 ? n : null;
  }

  function findCatalogItem(info) {
    const nameWithoutTrailingNumber = info.name.replace(/\s+\d+$/, '');
    const list = catalog();
    return list.find((it) => it.name === info.name && it.areaName === info.area)
      || list.find((it) => it.name === nameWithoutTrailingNumber && it.areaName === info.area)
      || list.find((it) => it.name === info.name)
      || list.find((it) => it.name === nameWithoutTrailingNumber)
      || null;
  }

  function parseOverdueDays(btn) {
    if (!btn.classList.contains('overdue')) return 0;
    const text = btn.querySelector('small')?.textContent || '';
    const match = text.match(/(\d+(?:\.\d+)?)\s+day(?:s)?\s+overdue/i);
    return match ? Number(match[1]) : 0;
  }

  function normalizedOverdue(btn) {
    const info = getTaskInfoFromButton(btn);
    const item = findCatalogItem(info);
    const overdueDays = parseOverdueDays(btn);
    const interval = item ? intervalDays(item.freq) : 7;
    const pct = overdueDays > 0 ? (overdueDays / Math.max(1, interval)) * 100 : 0;
    return { pct, overdueDays, interval };
  }

  function colorForPct(pct) {
    const t = Math.max(0, Math.min(1, 1 - Math.exp(-pct / 95)));
    const hue = Math.round(30 * (1 - t));
    const sat = Math.round(86 + 10 * t);
    const light = Math.round(57 - 16 * t);
    const bgAlpha = (0.055 + 0.19 * t).toFixed(3);
    const borderAlpha = (0.62 + 0.38 * t).toFixed(3);
    return {
      rail: `hsla(${hue}, ${sat}%, ${light}%, ${borderAlpha})`,
      bg: `hsla(${hue}, ${sat}%, ${light}%, ${bgAlpha})`,
      text: pct >= 75 ? '#fecaca' : 'inherit',
      checkBg: `hsla(${hue}, ${sat}%, ${light}%, ${Math.min(0.34, Number(bgAlpha) + 0.12)})`,
      checkText: pct >= 75 ? '#fecaca' : '#fed7aa',
      pillBg: `hsla(${hue}, ${sat}%, ${light}%, ${Math.min(0.32, Number(bgAlpha) + 0.10)})`,
      pillText: pct >= 75 ? '#fecaca' : '#fed7aa',
      shadow: pct >= 150 ? 'inset 0 0 0 1px rgba(248,113,113,.22)' : 'none',
      fontWeight: pct >= 100 ? 800 : pct >= 50 ? 700 : 600,
    };
  }

  function removeOldPriorityPill(btn) {
    const small = btn.querySelector('small');
    small?.querySelector('.eff-priority-pill')?.remove();
  }

  function applyOverdueOmbre() {
    document.querySelectorAll('.eff-flex-column .eff-task').forEach((btn) => {
      removeOldPriorityPill(btn);
      btn.removeAttribute('data-priority');
      const small = btn.querySelector('small');
      small?.querySelector('.eff-overdue-pill')?.remove();

      const { pct, overdueDays, interval } = normalizedOverdue(btn);
      btn.setAttribute('data-overdue-pct', String(Math.round(pct)));
      btn.style.removeProperty('--overdue-rail');
      btn.style.removeProperty('--overdue-bg');
      btn.style.removeProperty('--overdue-text');
      btn.style.removeProperty('--overdue-check-bg');
      btn.style.removeProperty('--overdue-check-text');
      btn.style.removeProperty('--overdue-pill-bg');
      btn.style.removeProperty('--overdue-pill-text');
      btn.style.removeProperty('--overdue-shadow');
      btn.style.fontWeight = '';

      if (!btn.classList.contains('overdue') || overdueDays <= 0) {
        if (btn.classList.contains('due')) {
          const color = colorForPct(0);
          btn.style.setProperty('--overdue-rail', color.rail);
          btn.style.setProperty('--overdue-bg', color.bg);
          btn.style.setProperty('--overdue-check-bg', color.checkBg);
          btn.style.setProperty('--overdue-check-text', color.checkText);
        } else {
          btn.removeAttribute('data-overdue-pct');
        }
        return;
      }

      const color = colorForPct(pct);
      btn.style.setProperty('--overdue-rail', color.rail);
      btn.style.setProperty('--overdue-bg', color.bg);
      btn.style.setProperty('--overdue-text', color.text);
      btn.style.setProperty('--overdue-check-bg', color.checkBg);
      btn.style.setProperty('--overdue-check-text', color.checkText);
      btn.style.setProperty('--overdue-pill-bg', color.pillBg);
      btn.style.setProperty('--overdue-pill-text', color.pillText);
      btn.style.setProperty('--overdue-shadow', color.shadow);
      btn.style.fontWeight = String(color.fontWeight);
      btn.dataset.normalizedOverdue = String(pct);
      btn.dataset.overdueInterval = String(interval);

      if (small) {
        const pill = document.createElement('span');
        pill.className = 'eff-overdue-pill';
        pill.textContent = Math.round(pct) + '% overdue';
        small.prepend(pill);
      }
    });
  }

  function sortDailySections() {
    document.querySelectorAll('.eff-daily-column .eff-section').forEach((section) => {
      const tasks = Array.from(section.querySelectorAll('.eff-task[data-row-kind="daily"]'));
      if (tasks.length < 2) return;

      const rows = tasks.map((btn, index) => ({ btn, index, info: getTaskInfoFromButton(btn) }));
      const hasManualOrder = rows.some((row) => getExplicitOrder(row.info) !== null);
      if (!hasManualOrder) return; // Blank order means preserve configured/guard order, not alphabetical.

      rows.sort((a, b) => {
        const ao = getExplicitOrder(a.info);
        const bo = getExplicitOrder(b.info);
        if (ao !== null && bo !== null) return ao - bo || a.index - b.index;
        if (ao !== null) return -1;
        if (bo !== null) return 1;
        return a.index - b.index;
      });
      rows.forEach((row) => section.appendChild(row.btn));
    });
  }

  function sortRecurringByNormalizedOverdue() {
    document.querySelectorAll('.eff-flex-column .eff-section').forEach((section) => {
      const title = (section.querySelector('h3 span')?.textContent || '').trim();
      const tasks = Array.from(section.querySelectorAll('.eff-task'));
      if (tasks.length < 2 || title !== 'Overdue') return;
      tasks.sort((a, b) => {
        const ao = normalizedOverdue(a);
        const bo = normalizedOverdue(b);
        const an = Number(a.dataset.normalizedOverdue || ao.pct || 0);
        const bn = Number(b.dataset.normalizedOverdue || bo.pct || 0);
        return bn - an || bo.overdueDays - ao.overdueDays || getTaskInfoFromButton(a).name.localeCompare(getTaskInfoFromButton(b).name);
      });
      tasks.forEach((task) => section.appendChild(task));
    });
  }

  function applyOrderingAndPriority() {
    sortDailySections();
    applyOverdueOmbre();
    sortRecurringByNormalizedOverdue();
  }

  function parseSheetInfo(sheet) {
    const name = (sheet.querySelector('#lm-edit-name')?.value || '').trim();
    const p = (sheet.querySelector('p')?.textContent || '').trim();
    const area = (p.split(' · ')[0] || 'default').trim();
    const type = sheet.querySelector('#lm-edit-type')?.value || '';
    return { name, area, isDaily: type === 'daily' };
  }

  function enhanceEditSheet(sheet) {
    if (!sheet || sheet.dataset.orderPriorityEnhanced === '1') return;
    const grid = sheet.querySelector('.lm-edit-grid');
    const actions = sheet.querySelector('.lm-edit-actions');
    const typeSelect = sheet.querySelector('#lm-edit-type');
    const nameInput = sheet.querySelector('#lm-edit-name');
    if (!grid || !actions || !typeSelect || !nameInput) return;

    sheet.dataset.orderPriorityEnhanced = '1';
    const extra = document.createElement('div');
    extra.id = 'lm-order-priority-fields';
    extra.className = 'lm-edit-grid';
    extra.style.marginTop = '.55rem';
    grid.insertAdjacentElement('afterend', extra);

    const redraw = () => {
      const info = parseSheetInfo(sheet);
      if (!info.name) return;
      if (info.isDaily) {
        const current = localStorage.getItem(key(ORDER_KEY, info)) || '';
        extra.innerHTML = '<label>Daily order number<input id="lm-daily-order" type="number" min="1" step="1" value="' + esc(current) + '" placeholder="1, 2, 3…"></label><p class="lm-order-priority-help">Lower numbers show first inside Morning / Midday / Evening. Blank keeps the configured routine order.</p>';
      } else {
        extra.innerHTML = '<p class="lm-order-priority-help">Recurring color is automatic: overdue days ÷ task interval. Short-cadence tasks turn red faster; yearly tasks warm up slowly.</p>';
      }
    };

    typeSelect.addEventListener('change', () => setTimeout(redraw, 0));
    nameInput.addEventListener('input', () => setTimeout(redraw, 0));
    redraw();

    actions.addEventListener('click', (e) => {
      const action = e.target.closest('[data-action]')?.getAttribute('data-action');
      if (action !== 'save') return;
      const info = parseSheetInfo(sheet);
      if (!info.name || !info.isDaily) return;
      const value = (sheet.querySelector('#lm-daily-order')?.value || '').trim();
      if (value) localStorage.setItem(key(ORDER_KEY, info), value);
      else localStorage.removeItem(key(ORDER_KEY, info));
      setTimeout(applyOrderingAndPriority, 50);
    }, true);
  }

  function observeEditSheets() {
    const apply = () => {
      document.querySelectorAll('.lm-edit-sheet').forEach(enhanceEditSheet);
      applyOrderingAndPriority();
    };
    apply();
    const obs = new MutationObserver(() => window.requestAnimationFrame(apply));
    obs.observe(document.body, { childList: true, subtree: true });
  }

  injectStyles();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', observeEditSheets);
  } else {
    observeEditSheets();
  }
  window.addEventListener('load', () => setTimeout(applyOrderingAndPriority, 300));
})();
