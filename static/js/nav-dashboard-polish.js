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

  function keepRoutineColumnsSideBySideOnMobile() {
    if (document.getElementById('routine-mobile-column-override')) return;
    const style = document.createElement('style');
    style.id = 'routine-mobile-column-override';
    style.textContent = `
      @media (max-width: 840px) {
        .eff-columns {
          grid-template-columns: minmax(210px, .95fr) minmax(245px, 1.35fr) !important;
          overflow-x: auto;
          overscroll-behavior-x: contain;
          -webkit-overflow-scrolling: touch;
          padding-bottom: .6rem;
          scroll-snap-type: x proximity;
        }
        .eff-column {
          min-width: 210px;
          scroll-snap-align: start;
        }
        .eff-flex-column {
          min-width: 245px;
        }
        .eff-task strong {
          font-size: .88rem;
        }
        .eff-task small {
          font-size: .72rem;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function run() {
    polishDashboardTiles();
    keepRoutineColumnsSideBySideOnMobile();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
