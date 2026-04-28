(function () {
  function polishDashboardTiles() {
    const grid = document.querySelector('.app-grid');
    if (!grid) return;

    const editTile = grid.querySelector('[data-nav-tab="edit"]');
    if (editTile) editTile.remove();

    const calendarTile = grid.querySelector('[data-nav-tab="calendar"]');
    if (calendarTile) calendarTile.remove();

    const routinesTile = grid.querySelector('[data-nav-tab="cards"]');
    if (routinesTile) {
      const name = routinesTile.querySelector('.app-tile-name');
      const desc = routinesTile.querySelector('.app-tile-desc');
      const actions = routinesTile.querySelector('.app-tile-actions');
      if (name) name.textContent = 'Routines';
      if (desc) desc.textContent = 'Today stack, calendar view, and routine management.';
      if (actions) {
        actions.innerHTML = '<a href="/cards" class="btn btn-sm btn-primary">Today</a>' +
          '<a href="/routines?view=calendar" class="btn btn-sm btn-outline">Calendar</a>' +
          '<a href="/routines" class="btn btn-sm btn-outline">Manage</a>';
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', polishDashboardTiles);
  } else {
    polishDashboardTiles();
  }
})();
