(function () {
  if (new URLSearchParams(location.search).get('legacy') === '1') return;

  function overdueDays(task) {
    const small = task.querySelector('small');
    const text = small ? small.textContent || '' : '';
    const match = text.match(/(\d+)\s+days?\s+overdue/i);
    if (match) return Number(match[1]) || 0;
    if (/yesterday/i.test(text)) return 1;
    return 0;
  }

  function sectionTitle(section) {
    const span = section.querySelector('h3 span');
    return span ? span.textContent.trim() : '';
  }

  function cleanupEmptySections(list) {
    list.querySelectorAll('.dyn-section').forEach((section) => {
      if (sectionTitle(section) === 'Overdue') return;
      if (!section.querySelector('.dyn-task')) section.remove();
    });
  }

  function organizeOverdue() {
    const app = document.querySelector('#dynamic-routine-app');
    const list = app && app.querySelector('.dyn-list');
    if (!list) return;

    const existing = Array.from(list.querySelectorAll('.dyn-section')).find((section) => sectionTitle(section) === 'Overdue');
    const overdueTasks = Array.from(list.querySelectorAll('.dyn-task.overdue')).filter((task) => !task.closest('.dyn-section') || sectionTitle(task.closest('.dyn-section')) !== 'Overdue');

    if (!overdueTasks.length) {
      if (existing && !existing.querySelector('.dyn-task.overdue')) existing.remove();
      cleanupEmptySections(list);
      return;
    }

    let section = existing;
    if (!section) {
      section = document.createElement('section');
      section.className = 'card dyn-section dyn-overdue-section';
      section.innerHTML = '<h3><span>Overdue</span><small>0</small></h3>';
      list.insertBefore(section, list.firstChild);
    }

    const allOverdue = Array.from(section.querySelectorAll('.dyn-task.overdue')).concat(overdueTasks);
    allOverdue.sort((a, b) => overdueDays(b) - overdueDays(a));
    allOverdue.forEach((task) => section.appendChild(task));

    const count = section.querySelector('h3 small');
    if (count) count.textContent = String(allOverdue.length);
    cleanupEmptySections(list);
  }

  let timer = null;
  function schedule() {
    clearTimeout(timer);
    timer = setTimeout(organizeOverdue, 0);
  }

  document.addEventListener('alpine:initialized', schedule);
  window.addEventListener('load', schedule);
  document.addEventListener('click', schedule);

  const observer = new MutationObserver(schedule);
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();
