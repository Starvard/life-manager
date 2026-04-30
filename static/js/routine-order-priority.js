(function () {
  if (!location.pathname.startsWith('/cards')) return;

  const ORDER_KEY = 'lm:routine-daily-order:';
  const PRIORITY_KEY = 'lm:routine-priority:';

  function esc(s) {
    return String(s || '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function injectStyles() {
    if (document.getElementById('routine-order-priority-styles')) return;
    const style = document.createElement('style');
    style.id = 'routine-order-priority-styles';
    style.textContent = `
      .eff-flex-column .eff-task[data-priority="1"] { border-left-color: rgba(251,146,60,.62) !important; background: rgba(251,146,60,.045) !important; }
      .eff-flex-column .eff-task[data-priority="2"] { border-left-color: rgba(249,115,22,.75) !important; background: rgba(249,115,22,.065) !important; }
      .eff-flex-column .eff-task[data-priority="3"] { border-left-color: rgba(239,68,68,.84) !important; background: rgba(239,68,68,.085) !important; }
      .eff-flex-column .eff-task[data-priority="4"] { border-left-color: rgba(220,38,38,.95) !important; background: rgba(220,38,38,.115) !important; font-weight: 700; }
      .eff-flex-column .eff-task[data-priority="5"] { border-left-color: rgba(185,28,28,1) !important; background: rgba(185,28,28,.16) !important; font-weight: 800; box-shadow: inset 0 0 0 1px rgba(248,113,113,.18); }
      .eff-flex-column .eff-task[data-priority="4"] strong,
      .eff-flex-column .eff-task[data-priority="5"] strong { color: #fecaca; }
      .eff-priority-pill { display: inline-block; margin-right: .28rem; border-radius: 999px; padding: .05rem .28rem; font-size: .62rem; font-weight: 900; background: rgba(248,113,113,.16); color: #fecaca; }
      .lm-order-priority-help { margin: -.25rem 0 .25rem !important; color: var(--text-muted); font-size: .7rem !important; }
    `;
    document.head.appendChild(style);
  }

  function getTaskInfoFromButton(btn) {
    const name = (btn.querySelector('strong')?.textContent || '').trim();
    const small = (btn.querySelector('small')?.textContent || '').trim();
    const bits = small.split(' · ').map((x) => x.trim()).filter(Boolean);
    const area = bits.length ? bits[bits.length - 1] : 'default';
    const isDaily = btn.getAttribute('data-row-kind') === 'daily' || !!btn.closest('.eff-daily-column');
    return { name, area, isDaily };
  }

  function key(prefix, info) {
    return prefix + info.area + '::' + info.name;
  }

  function getOrder(info) {
    const n = Number(localStorage.getItem(key(ORDER_KEY, info)) || '');
    return Number.isFinite(n) && n > 0 ? n : 99999;
  }

  function getPriority(info) {
    const n = Number(localStorage.getItem(key(PRIORITY_KEY, info)) || '');
    return Number.isFinite(n) && n >= 1 && n <= 5 ? n : 2;
  }

  function sortDailySections() {
    document.querySelectorAll('.eff-daily-column .eff-section').forEach((section) => {
      const tasks = Array.from(section.querySelectorAll('.eff-task[data-row-kind="daily"]'));
      if (tasks.length < 2) return;
      tasks.sort((a, b) => {
        const ai = getTaskInfoFromButton(a);
        const bi = getTaskInfoFromButton(b);
        return getOrder(ai) - getOrder(bi) || ai.name.localeCompare(bi.name);
      });
      tasks.forEach((task) => section.appendChild(task));
    });
  }

  function applyRecurringPriorityColors() {
    document.querySelectorAll('.eff-flex-column .eff-task').forEach((btn) => {
      const info = getTaskInfoFromButton(btn);
      if (!info.name) return;
      const priority = getPriority(info);
      btn.setAttribute('data-priority', String(priority));
      const small = btn.querySelector('small');
      if (small && !small.querySelector('.eff-priority-pill')) {
        small.innerHTML = '<span class="eff-priority-pill">P' + priority + '</span>' + esc(small.textContent || '');
      } else if (small) {
        const pill = small.querySelector('.eff-priority-pill');
        if (pill) pill.textContent = 'P' + priority;
      }
    });
  }

  function applyOrderingAndPriority() {
    sortDailySections();
    applyRecurringPriorityColors();
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
        extra.innerHTML = '<label>Daily order number<input id="lm-daily-order" type="number" min="1" step="1" value="' + esc(current) + '" placeholder="1, 2, 3…"></label><p class="lm-order-priority-help">Lower numbers show first inside Morning / Midday / Evening. Blank falls back to alphabetical.</p>';
      } else {
        const current = getPriority(info);
        extra.innerHTML = '<label>Priority / color<select id="lm-recurring-priority"><option value="1">1 — low orange</option><option value="2">2 — orange</option><option value="3">3 — red-orange</option><option value="4">4 — red / bold</option><option value="5">5 — deepest red / boldest</option></select></label><p class="lm-order-priority-help">Priority only controls visual weight for recurring tasks. Higher = redder and bolder.</p>';
        const select = extra.querySelector('#lm-recurring-priority');
        if (select) select.value = String(current);
      }
    };

    typeSelect.addEventListener('change', () => setTimeout(redraw, 0));
    nameInput.addEventListener('input', () => setTimeout(redraw, 0));
    redraw();

    actions.addEventListener('click', (e) => {
      const action = e.target.closest('[data-action]')?.getAttribute('data-action');
      if (action !== 'save') return;
      const info = parseSheetInfo(sheet);
      if (!info.name) return;
      if (info.isDaily) {
        const value = (sheet.querySelector('#lm-daily-order')?.value || '').trim();
        if (value) localStorage.setItem(key(ORDER_KEY, info), value);
        else localStorage.removeItem(key(ORDER_KEY, info));
      } else {
        const value = sheet.querySelector('#lm-recurring-priority')?.value || '2';
        localStorage.setItem(key(PRIORITY_KEY, info), value);
      }
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
