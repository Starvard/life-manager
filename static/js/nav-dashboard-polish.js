(function () {
  const SECTION_KEY = 'lm:routine-section:';
  const DUE_KEY = 'lm:routine-next-due:';

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
      body.routine-edit-compact .routines-push-card { display:none !important; }
      body.routine-edit-compact .task-row-head .task-col-h:nth-child(5),
      body.routine-edit-compact .task-row > input[type="time"],
      body.routine-edit-compact .add-task-row > input[type="time"] { display:none !important; }
      .lm-sheet-backdrop { position: fixed; inset: 0; z-index: 10000; background: rgba(0,0,0,.48); display: flex; align-items: flex-end; justify-content: center; padding: .75rem; }
      .lm-edit-sheet { width: min(460px, 100%); border: 1px solid rgba(148,163,184,.25); border-radius: 1.05rem; background: rgb(15,23,42); box-shadow: 0 28px 90px rgba(0,0,0,.48); padding: .95rem; }
      .lm-edit-sheet h3 { margin: 0 0 .25rem; font-size: 1rem; }
      .lm-edit-sheet p { margin: 0 0 .75rem; color: var(--text-muted); font-size: .8rem; line-height: 1.35; }
      .lm-edit-grid { display: grid; gap: .55rem; }
      .lm-edit-grid label { display: grid; gap: .22rem; font-size: .76rem; color: var(--text-muted); font-weight: 700; }
      .lm-edit-grid input, .lm-edit-grid select { width: 100%; border: 1px solid var(--border); border-radius: .65rem; padding: .62rem .65rem; background: rgba(255,255,255,.055); color: var(--text); }
      .lm-edit-actions { display: flex; gap: .45rem; justify-content: flex-end; margin-top: .85rem; }
    `;
    document.head.appendChild(style);
  }

  function taskInfo(btn) {
    const name = (btn.querySelector('strong')?.textContent || '').trim();
    const small = (btn.querySelector('small')?.textContent || '').trim();
    const bits = small.split(' · ').map((x) => x.trim()).filter(Boolean);
    const area = bits.length ? bits[bits.length - 1] : 'default';
    const isDaily = btn.getAttribute('data-row-kind') === 'daily' || !!btn.closest('.eff-daily-column');
    const section = btn.closest('.eff-section')?.querySelector('h3 span')?.textContent?.trim() || '';
    return { name, area, isDaily, section };
  }

  function storageKey(prefix, info) {
    return prefix + info.area + '::' + info.name;
  }

  function sectionContainer(sectionName) {
    const dailyCol = document.querySelector('.eff-daily-column');
    if (!dailyCol) return null;
    return Array.from(dailyCol.querySelectorAll('.eff-section')).find((sec) => {
      return (sec.querySelector('h3 span')?.textContent || '').trim() === sectionName;
    }) || null;
  }

  function updateSectionCount(sec) {
    const count = sec?.querySelectorAll('.eff-task').length || 0;
    const small = sec?.querySelector('h3 small');
    if (small) small.textContent = String(count);
  }

  function applyRoutineOverrides() {
    document.querySelectorAll('.eff-task').forEach((btn) => {
      const info = taskInfo(btn);
      if (!info.name) return;
      if (info.isDaily) {
        const saved = localStorage.getItem(storageKey(SECTION_KEY, info));
        if (saved && saved !== info.section) {
          const target = sectionContainer(saved);
          const old = btn.closest('.eff-section');
          if (target) {
            target.appendChild(btn);
            updateSectionCount(old);
            updateSectionCount(target);
          }
        }
      } else {
        const due = localStorage.getItem(storageKey(DUE_KEY, info));
        if (due) {
          const small = btn.querySelector('small');
          if (small && !small.dataset.originalText) small.dataset.originalText = small.textContent || '';
          if (small) small.textContent = 'Manual next due ' + due + ' · ' + info.area;
        }
      }
    });
  }

  function closeSheet() {
    document.querySelector('.lm-sheet-backdrop')?.remove();
  }

  function openEditSheet(btn) {
    const info = taskInfo(btn);
    if (!info.name) return;
    closeSheet();
    const currentSection = localStorage.getItem(storageKey(SECTION_KEY, info)) || info.section || 'Midday';
    const currentDue = localStorage.getItem(storageKey(DUE_KEY, info)) || '';
    const body = document.createElement('div');
    body.className = 'lm-sheet-backdrop';
    body.innerHTML = '<div class="lm-edit-sheet" role="dialog" aria-modal="true">' +
      '<h3>Edit routine</h3>' +
      '<p>' + info.name + ' · ' + info.area + '</p>' +
      '<div class="lm-edit-grid">' +
        (info.isDaily
          ? '<label>Daily section<select id="lm-edit-section"><option>Morning</option><option>Midday</option><option>Evening</option></select></label>'
          : '<label>Manual next due date<input id="lm-edit-due" type="date" value="' + currentDue + '"></label><p style="margin:0;color:var(--text-muted);font-size:.72rem;">Use this to nudge a recurring item without opening the old manage page.</p>') +
      '</div>' +
      '<div class="lm-edit-actions"><button type="button" class="btn btn-secondary btn-sm" data-action="clear">Clear</button><button type="button" class="btn btn-secondary btn-sm" data-action="cancel">Cancel</button><button type="button" class="btn btn-primary btn-sm" data-action="save">Save</button></div>' +
      '</div>';
    body.addEventListener('click', (e) => {
      if (e.target === body) closeSheet();
      const action = e.target.closest('[data-action]')?.getAttribute('data-action');
      if (!action) return;
      if (action === 'cancel') { closeSheet(); return; }
      if (info.isDaily) {
        const key = storageKey(SECTION_KEY, info);
        if (action === 'clear') localStorage.removeItem(key);
        if (action === 'save') localStorage.setItem(key, document.getElementById('lm-edit-section')?.value || 'Midday');
      } else {
        const key = storageKey(DUE_KEY, info);
        if (action === 'clear') localStorage.removeItem(key);
        if (action === 'save') {
          const val = document.getElementById('lm-edit-due')?.value || '';
          if (val) localStorage.setItem(key, val); else localStorage.removeItem(key);
        }
      }
      closeSheet();
      applyRoutineOverrides();
    });
    document.body.appendChild(body);
    const sectionSelect = document.getElementById('lm-edit-section');
    if (sectionSelect) sectionSelect.value = currentSection;
  }

  function bindLongPressEdit() {
    document.querySelectorAll('.eff-task').forEach((btn) => {
      if (btn.dataset.longPressEditBound === '1') return;
      btn.dataset.longPressEditBound = '1';
      let timer = null;
      let fired = false;
      btn.addEventListener('pointerdown', () => {
        fired = false;
        clearTimeout(timer);
        timer = setTimeout(() => { fired = true; openEditSheet(btn); }, 650);
      });
      ['pointerup', 'pointercancel', 'pointerleave'].forEach((ev) => btn.addEventListener(ev, () => clearTimeout(timer)));
      btn.addEventListener('click', (e) => {
        if (fired) {
          e.preventDefault();
          e.stopPropagation();
          fired = false;
        }
      }, true);
      btn.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        openEditSheet(btn);
      });
    });
  }

  function polishRoutinePage() {
    if (location.pathname === '/routines') document.body.classList.add('routine-edit-compact');
    applyRoutineOverrides();
    bindLongPressEdit();
  }

  function run() {
    polishDashboardTiles();
    injectRoutinePolishStyles();
    polishRoutinePage();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
  window.addEventListener('load', run);
  const observer = new MutationObserver(() => {
    window.requestAnimationFrame(polishRoutinePage);
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
