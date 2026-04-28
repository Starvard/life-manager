(function () {
  function polishDashboardTiles() {
    const grid = document.querySelector('.app-grid');
    if (!grid) return;

    const editTile = grid.querySelector('[data-nav-tab="edit"]');
    if (editTile) editTile.remove();

    const routinesTile = grid.querySelector('[data-nav-tab="cards"]');
    if (routinesTile) {
      const name = routinesTile.querySelector('.app-tile-name');
      const desc = routinesTile.querySelector('.app-tile-desc');
      const secondary = routinesTile.querySelector('.btn-outline');
      if (name) name.textContent = 'Routines';
      if (desc) desc.textContent = 'Today stack, overdue items, done list, and routine management.';
      if (secondary) {
        secondary.href = '/routines';
        secondary.textContent = 'Manage';
      }
    }

    if (!grid.querySelector('[data-nav-tab="calendar"]')) {
      const tile = document.createElement('div');
      tile.className = 'app-tile';
      tile.setAttribute('data-nav-tab', 'calendar');
      tile.innerHTML = '<div class="app-tile-head"><span class="app-tile-name">Calendar</span></div>' +
        '<p class="app-tile-desc">Live month view of routine due dates and completed tasks.</p>' +
        '<div class="app-tile-actions"><a href="/routines?view=calendar" class="btn btn-sm btn-primary">Open</a></div>';
      if (routinesTile && routinesTile.nextSibling) grid.insertBefore(tile, routinesTile.nextSibling);
      else grid.appendChild(tile);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', polishDashboardTiles);
  } else {
    polishDashboardTiles();
  }
})();
