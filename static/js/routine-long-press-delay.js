(function () {
  if (!location.pathname.startsWith('/cards')) return;

  const LONG_PRESS_MS = 2000;
  let timer = null;
  let activeTask = null;
  let openedTask = null;
  let allowSyntheticContextMenuFor = null;

  function taskFromEvent(e) {
    return e.target && e.target.closest ? e.target.closest('.eff-task') : null;
  }

  function clearTimer() {
    if (timer) clearTimeout(timer);
    timer = null;
    activeTask = null;
  }

  document.addEventListener('pointerdown', (e) => {
    const task = taskFromEvent(e);
    if (!task) return;

    // Block the older 650ms task-level long-press listener from seeing this pointerdown.
    // Normal tap/click still works because we do not block the later click event.
    e.stopImmediatePropagation();

    clearTimer();
    activeTask = task;
    timer = setTimeout(() => {
      if (!activeTask || !document.body.contains(activeTask)) return;
      openedTask = activeTask;
      allowSyntheticContextMenuFor = activeTask;
      activeTask.dispatchEvent(new MouseEvent('contextmenu', {
        bubbles: true,
        cancelable: true,
        view: window,
      }));
      clearTimer();
    }, LONG_PRESS_MS);
  }, true);

  ['pointerup', 'pointercancel', 'pointerleave', 'scroll'].forEach((eventName) => {
    document.addEventListener(eventName, clearTimer, true);
  });

  document.addEventListener('contextmenu', (e) => {
    const task = taskFromEvent(e);
    if (!task) return;

    if (allowSyntheticContextMenuFor === task) {
      allowSyntheticContextMenuFor = null;
      return;
    }

    // Prevent the browser/mobile default context menu from opening the editor early.
    e.preventDefault();
    e.stopImmediatePropagation();
  }, true);

  document.addEventListener('click', (e) => {
    const task = taskFromEvent(e);
    if (!task || task !== openedTask) return;
    openedTask = null;
    e.preventDefault();
    e.stopImmediatePropagation();
  }, true);
})();
