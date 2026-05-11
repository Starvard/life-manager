(function () {
  if (!location.pathname.startsWith('/cards')) return;

  const ORDER_KEY = 'lm:routine-daily-order:';
  let applying = false;

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

  function isDaily(task) {
    return Number(task && task.freq || 0) >= 7;
  }

  function buttonInfo(btn) {
    const name = (btn.querySelector('strong')?.textContent || '').trim();
    const small = (btn.querySelector('small')?.textContent || '').trim();
    const clean = small.replace(/^P\d+\s*/, '').replace(/^\d+% overdue\s*/, '');
    const bits = clean.split(' · ').map((x) => x.trim()).filter(Boolean);
    const area = bits.length ? bits[bits.length - 1] : 'default';
    return { name, area };
  }

  function storageKey(info) {
    return ORDER_KEY + info.area + '::' + info.name;
  }

  function explicitOrder(info) {
    const raw = localStorage.getItem(storageKey(info));
    const n = Number(raw || '');
    return Number.isFinite(n) && n > 0 ? n : null;
  }

  function configuredOrderMap() {
    const order = new Map();
    let i = 0;
    alpineCards().forEach((card) => {
      const areaName = card.area_name || card.area_key || 'default';
      (card.tasks || []).forEach((task) => {
        if (!isDaily(task)) return;
        const key = areaName + '::' + task.name;
        if (!order.has(key)) order.set(key, i++);
      });
    });
    return order;
  }

  function restoreDailyOrder() {
    if (applying) return;
    const order = configuredOrderMap();
    if (!order.size) return;

    applying = true;
    document.querySelectorAll('.eff-daily-column .eff-section').forEach((section) => {
      const tasks = Array.from(section.querySelectorAll('.eff-task[data-row-kind="daily"]'));
      if (tasks.length < 2) return;

      const decorated = tasks.map((btn, domIndex) => {
        const info = buttonInfo(btn);
        const manual = explicitOrder(info);
        const configured = order.get(info.area + '::' + info.name);
        return {
          btn,
          domIndex,
          manual,
          configured: Number.isFinite(configured) ? configured : 100000 + domIndex,
        };
      });

      decorated.sort((a, b) => {
        const am = a.manual !== null;
        const bm = b.manual !== null;
        if (am && bm) return a.manual - b.manual || a.configured - b.configured || a.domIndex - b.domIndex;
        if (am) return -1;
        if (bm) return 1;
        return a.configured - b.configured || a.domIndex - b.domIndex;
      });

      decorated.forEach((row) => section.appendChild(row.btn));
    });
    applying = false;
  }

  function schedule() {
    [250, 700, 1300, 2200, 3600, 5500, 8500].forEach((ms) => setTimeout(restoreDailyOrder, ms));
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', schedule);
  else schedule();
  window.addEventListener('load', schedule);
  document.addEventListener('alpine:initialized', schedule);
  document.addEventListener('lm:routine-daily-guard-applied', schedule);
})();
