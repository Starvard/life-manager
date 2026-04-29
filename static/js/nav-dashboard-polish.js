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
      if (desc) desc.textContent = 'Today stack, calendar view, and inline routine editing.';
      if (actions) {
        actions.innerHTML = '<a href="/cards" class="btn btn-sm btn-primary">Today</a>' +
          '<a href="/routines?view=calendar" class="btn btn-sm btn-outline">Calendar</a>';
      }
    }
  }

  function injectRoutinePolishStyles() {
    if (document.getElementById('routine-mobile-column-override')) return;
    const style = document.createElement('style');
    style.id = 'routine-mobile-column-override';
    style.textContent = `
      @media (max-width: 840px) {
        .main-content { padding-left: .42rem !important; padding-right: .42rem !important; }
        #dynamic-routine-app { margin-left: -.18rem; margin-right: -.18rem; }
        .eff-columns {
          grid-template-columns: minmax(184px, .9fr) minmax(222px, 1.18fr) !important;
          gap: .42rem !important;
          overflow-x: auto;
          overscroll-behavior-x: contain;
          -webkit-overflow-scrolling: touch;
          padding-bottom: .6rem;
          scroll-snap-type: x proximity;
        }
        .eff-column { min-width: 184px; scroll-snap-align: start; gap: .5rem !important; }
        .eff-flex-column { min-width: 222px; }
        .eff-column-title, .eff-section { padding: .56rem !important; }
        .eff-task { gap: .4rem !important; padding: .54rem .45rem !important; border-radius: .68rem !important; }
        .eff-check { flex-basis: 1.28rem !important; width: 1.28rem !important; height: 1.28rem !important; font-size: .74rem !important; }
        .eff-task strong { font-size: .78rem !important; line-height: 1.08; }
        .eff-task small { font-size: .61rem !important; line-height: 1.12; }
        .eff-hero { padding: .7rem !important; }
        .eff-summary { gap: .32rem !important; }
        .eff-summary span { padding: .26rem .46rem !important; font-size: .72rem !important; }
      }
      body.routine-edit-compact .routines-push-card,
      body.routine-edit-compact .nav-tabs-pref-card,
      body.routine-edit-compact form[action$="/routines/save"] { display:none !important; }
    `;
    document.head.appendChild(style);
  }

  function run() {
    polishDashboardTiles();
    injectRoutinePolishStyles();
    if (location.pathname === '/routines' && !location.search.includes('view=calendar')) {
      document.body.classList.add('routine-edit-compact');
      const main = document.querySelector('.main-content');
      if (main && !document.getElementById('routine-retired-manage')) {
        const div = document.createElement('div');
        div.id = 'routine-retired-manage';
        div.className = 'card';
        div.style.padding = '1rem';
        div.innerHTML = '<h2 style="margin-top:0">Routine editing moved</h2><p class="subtitle">Edit routines by long-pressing a task on the Today Stack. Add new tasks from the Add task button there.</p><a class="btn btn-primary" href="/cards">Back to Today Stack</a>';
        main.prepend(div);
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
  window.addEventListener('load', run);
})();
