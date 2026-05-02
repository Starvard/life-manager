(function () {
  if (!location.pathname.startsWith('/cards')) return;

  function parseDateFromSmallText(text) {
    const due = String(text || '').match(/Due\s+([A-Za-z]{3}),?\s+([A-Za-z]{3})\s+(\d{1,2})/i);
    if (!due) return null;
    const selectedYear = new Date().getFullYear();
    const parsed = new Date(due[1] + ' ' + due[2] + ' ' + due[3] + ' ' + selectedYear + ' 00:00:00');
    if (Number.isNaN(parsed.getTime())) return null;
    return parsed.getFullYear() + '-' + String(parsed.getMonth() + 1).padStart(2, '0') + '-' + String(parsed.getDate()).padStart(2, '0');
  }

  function sortComingUpOnly() {
    const app = document.getElementById('dynamic-routine-app');
    const flexCol = app?.querySelector('.eff-flex-column');
    if (!app || !flexCol) return;

    const section = Array.from(flexCol.querySelectorAll('.eff-section')).find((sec) => {
      return (sec.querySelector('h3 span')?.textContent || '').trim() === 'Coming Up';
    });
    if (!section || section.dataset.fastComingUpSorted === '1') return;

    const tasks = Array.from(section.querySelectorAll('.eff-task'));
    tasks.forEach((btn) => {
      if (btn.getAttribute('data-due-iso')) return;
      const text = btn.querySelector('small')?.textContent || '';
      const dueIso = parseDateFromSmallText(text);
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
    section.dataset.fastComingUpSorted = '1';
  }

  function schedule() {
    setTimeout(sortComingUpOnly, 300);
    setTimeout(sortComingUpOnly, 800);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', schedule);
  else schedule();
  window.addEventListener('load', schedule);
  document.addEventListener('alpine:initialized', schedule);
})();
