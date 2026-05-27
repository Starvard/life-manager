(() => {
  const STORE_KEY = 'life-manager:routines-v2';
  const DAY = 86400000;
  const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const $ = id => document.getElementById(id);
  const app = $('app');
  const msg = $('message');
  const form = $('formWrap');
  const editId = $('editId');
  const nameInput = $('nameInput');
  const areaInput = $('areaInput');
  const typeInput = $('typeInput');
  const valueInput = $('valueInput');
  const daysInput = $('daysInput');
  const notesInput = $('notesInput');
  const valueLabel = $('valueLabel');
  const daysLabel = $('daysLabel');
  const deleteBtn = $('deleteBtn');

  const esc = s => String(s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const pad = n => String(n).padStart(2, '0');
  const todayIso = () => {
    const d = new Date();
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
  };
  const nowIso = () => new Date().toISOString();
  const parseDate = s => new Date(String(s || '').slice(0, 10) + 'T00:00:00');
  const isoDate = d => `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
  const addDays = (s, n) => { const d = parseDate(s); d.setDate(d.getDate() + n); return isoDate(d); };
  const addMonths = (s, n) => { const d = parseDate(s); d.setMonth(d.getMonth() + n); return isoDate(d); };
  const diffDays = (a, b) => Math.round((parseDate(a) - parseDate(b)) / DAY);
  const weekStart = s => { const d = parseDate(s); const day = (d.getDay() + 6) % 7; d.setDate(d.getDate() - day); return isoDate(d); };
  const niceDate = s => parseDate(s).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  const id = prefix => `${prefix}_${Math.random().toString(36).slice(2)}_${Date.now().toString(36)}`;

  function blankState() {
    return { version: 1, routines: [], completions: [] };
  }

  function loadState() {
    try {
      const raw = JSON.parse(localStorage.getItem(STORE_KEY) || 'null');
      if (!raw || !Array.isArray(raw.routines) || !Array.isArray(raw.completions)) return blankState();
      return { version: 1, routines: raw.routines, completions: raw.completions };
    } catch {
      return blankState();
    }
  }

  function saveState(state) {
    localStorage.setItem(STORE_KEY, JSON.stringify(state));
  }

  function completionsFor(state, routineId) {
    return state.completions
      .filter(c => c.routine_id === routineId && !c.deleted)
      .sort((a, b) => String(a.completed_at).localeCompare(String(b.completed_at)));
  }

  function latestCompletion(state, routineId) {
    const rows = completionsFor(state, routineId);
    return rows.length ? rows[rows.length - 1] : null;
  }

  function completionsOnDate(state, routineId, date) {
    return completionsFor(state, routineId).filter(c => c.completed_date === date);
  }

  function completionsThisWeek(state, routineId, today) {
    const start = weekStart(today);
    const end = addDays(start, 6);
    return completionsFor(state, routineId).filter(c => c.completed_date >= start && c.completed_date <= end);
  }

  function normalizeValue(type, value) {
    if (type === 'daily') return null;
    const n = Math.max(1, Math.round(Number(value || 1)));
    return n;
  }

  function parseWeekdays(raw) {
    const map = { mon:0, monday:0, tue:1, tues:1, tuesday:1, wed:2, weds:2, wednesday:2, thu:3, thur:3, thurs:3, thursday:3, fri:4, friday:4, sat:5, saturday:5, sun:6, sunday:6 };
    const out = [];
    String(raw || '').split(/[,\s]+/).forEach(part => {
      const p = part.trim().toLowerCase();
      if (!p) return;
      if (/^[0-6]$/.test(p)) out.push(Number(p));
      else if (map[p] !== undefined) out.push(map[p]);
    });
    return [...new Set(out)].sort((a, b) => a - b);
  }

  function repeatLabel(r) {
    const v = Number(r.repeat_value || 1);
    switch (r.repeat_type) {
      case 'daily': return 'Daily';
      case 'times_per_day': return `${v}/day`;
      case 'every_n_days': return v === 1 ? 'Daily' : `Every ${v} days`;
      case 'times_per_week': return `${v}/week`;
      case 'weekdays': return (r.days_of_week || []).map(d => weekdays[d]).join(', ') || 'Weekdays';
      case 'every_n_months': return v === 1 ? 'Monthly' : `Every ${v} months`;
      default: return 'Routine';
    }
  }

  function nextWeekdayDue(days, today, afterToday = false) {
    const selected = (days || []).length ? days : [0];
    for (let offset = afterToday ? 1 : 0; offset <= 14; offset++) {
      const d = addDays(today, offset);
      const idx = (parseDate(d).getDay() + 6) % 7;
      if (selected.includes(idx)) return d;
    }
    return today;
  }

  function lastScheduledWeekdayBefore(days, today) {
    const selected = (days || []).length ? days : [0];
    for (let offset = 0; offset <= 14; offset++) {
      const d = addDays(today, -offset);
      const idx = (parseDate(d).getDay() + 6) % 7;
      if (selected.includes(idx)) return d;
    }
    return today;
  }

  function statusLabel(today, due) {
    const delta = diffDays(today, due);
    if (delta === 0) return 'Today';
    if (delta === 1) return '1 day overdue';
    if (delta > 1) return `${delta} days overdue`;
    if (delta === -1) return 'Tomorrow';
    if (delta > -31) return `In ${-delta} days`;
    return niceDate(due);
  }

  function computeRoutine(state, routine, today) {
    const todayComps = completionsOnDate(state, routine.id, today);
    const last = latestCompletion(state, routine.id);
    const lastDate = last ? last.completed_date : '';
    let due = today;
    let bucket = 'due';
    let rank = 1;
    let status = 'Today';
    let progress = '';

    switch (routine.repeat_type) {
      case 'daily': {
        if (todayComps.length) { bucket = 'done'; rank = 90; status = 'Done today'; due = addDays(today, 1); }
        else { bucket = 'today'; rank = 10; status = 'Today'; }
        break;
      }
      case 'times_per_day': {
        const target = Math.max(1, Number(routine.repeat_value || 1));
        progress = `${Math.min(todayComps.length, target)}/${target}`;
        if (todayComps.length >= target) { bucket = 'done'; rank = 90; status = `Done today · ${progress}`; due = addDays(today, 1); }
        else { bucket = 'today'; rank = 10; status = progress; }
        break;
      }
      case 'times_per_week': {
        const target = Math.max(1, Number(routine.repeat_value || 1));
        const count = completionsThisWeek(state, routine.id, today).length;
        progress = `${Math.min(count, target)}/${target} this week`;
        const start = weekStart(today);
        due = start;
        if (todayComps.length && count >= target) { bucket = 'done'; rank = 90; status = `Done today · ${progress}`; due = addDays(start, 7); }
        else if (count >= target) { bucket = 'upcoming'; rank = 40; status = 'Next week'; due = addDays(start, 7); }
        else { bucket = 'today'; rank = 12; status = progress; }
        break;
      }
      case 'weekdays': {
        const scheduled = lastScheduledWeekdayBefore(routine.days_of_week, today);
        const next = nextWeekdayDue(routine.days_of_week, today, false);
        const doneSinceScheduled = lastDate && diffDays(lastDate, scheduled) >= 0;
        if (todayComps.length) { bucket = 'done'; rank = 90; status = 'Done today'; due = nextWeekdayDue(routine.days_of_week, today, true); }
        else if (!doneSinceScheduled && diffDays(today, scheduled) >= 0) { due = scheduled; bucket = diffDays(today, due) > 0 ? 'overdue' : 'due'; rank = diffDays(today, due) > 0 ? 0 : 1; status = statusLabel(today, due); }
        else { due = next; const delta = diffDays(today, due); bucket = delta === 0 ? 'due' : (delta <= -31 ? 'future' : 'upcoming'); rank = delta === 0 ? 1 : (bucket === 'upcoming' ? 40 : 60); status = statusLabel(today, due); }
        break;
      }
      case 'every_n_months': {
        due = lastDate ? addMonths(lastDate, Math.max(1, Number(routine.repeat_value || 1))) : today;
        const delta = diffDays(today, due);
        if (todayComps.length) { bucket = 'done'; rank = 90; status = 'Done today'; }
        else if (delta > 0) { bucket = 'overdue'; rank = 0; status = statusLabel(today, due); }
        else if (delta === 0) { bucket = 'due'; rank = 1; status = 'Today'; }
        else if (delta >= -30) { bucket = 'upcoming'; rank = 40; status = statusLabel(today, due); }
        else { bucket = 'future'; rank = 60; status = statusLabel(today, due); }
        break;
      }
      case 'every_n_days':
      default: {
        due = lastDate ? addDays(lastDate, Math.max(1, Number(routine.repeat_value || 1))) : today;
        const delta = diffDays(today, due);
        if (todayComps.length) { bucket = 'done'; rank = 90; status = 'Done today'; }
        else if (delta > 0) { bucket = 'overdue'; rank = 0; status = statusLabel(today, due); }
        else if (delta === 0) { bucket = 'due'; rank = 1; status = 'Today'; }
        else if (delta >= -30) { bucket = 'upcoming'; rank = 40; status = statusLabel(today, due); }
        else { bucket = 'future'; rank = 60; status = statusLabel(today, due); }
        break;
      }
    }

    return { routine, bucket, rank, status, due, lastDate, progress, repeat: repeatLabel(routine) };
  }

  function sortItems(items) {
    return [...items].sort((a, b) => a.rank - b.rank || String(a.due || '').localeCompare(String(b.due || '')) || String(a.routine.area || '').localeCompare(String(b.routine.area || '')) || String(a.routine.name || '').localeCompare(String(b.routine.name || '')));
  }

  function card(item, mode = '') {
    const r = item.routine;
    const cls = mode === 'all' ? 'all' : item.bucket;
    const action = item.bucket === 'done' ? 'Undo' : 'Done';
    const sub = `${r.area || 'General'} · ${item.repeat}`;
    return `<div class="v2-card ${cls}" data-id="${esc(r.id)}" data-mode="${esc(mode)}"><span class="v2-main"><strong>${esc(r.name)}</strong><small>${esc(item.status)} · ${esc(sub)}</small></span><button class="v2-btn ${item.bucket === 'done' ? '' : 'primary'}" data-action="${item.bucket === 'done' ? 'undo' : 'done'}">${action}</button></div>`;
  }

  function section(title, items, mode = '') {
    if (!items.length) return '';
    return `<section class="v2-section card"><h2>${esc(title)}<small>${items.length}</small></h2>${items.map(x => card(x, mode)).join('')}</section>`;
  }

  function render() {
    const state = loadState();
    const today = todayIso();
    const active = state.routines.filter(r => r.active !== false && !r.deleted);
    const items = sortItems(active.map(r => computeRoutine(state, r, today)));
    const groups = {
      due: items.filter(x => x.bucket === 'overdue' || x.bucket === 'due'),
      today: items.filter(x => x.bucket === 'today'),
      upcoming: items.filter(x => x.bucket === 'upcoming'),
      future: items.filter(x => x.bucket === 'future'),
      done: items.filter(x => x.bucket === 'done'),
      all: items
    };
    app.innerHTML = `<div>${section('Due / Overdue', groups.due)}${section('Today', groups.today)}${section('Done Today', groups.done)}</div><div>${section('Coming Up', groups.upcoming)}${section('Far Future', groups.future)}${section('All Routines', groups.all, 'all')}</div>${items.length ? '' : '<div class="v2-empty card">No routines yet. Add one to start.</div>'}`;
    bindCards(items);
  }

  function bindCards(items) {
    const byId = Object.fromEntries(items.map(x => [x.routine.id, x]));
    app.querySelectorAll('.v2-card').forEach(el => {
      const rid = el.dataset.id;
      const item = byId[rid];
      el.addEventListener('click', e => {
        if (e.target.closest('button')) return;
        openForm(item.routine);
      });
      el.querySelector('button')?.addEventListener('click', e => {
        e.stopPropagation();
        if (e.currentTarget.dataset.action === 'undo') undoToday(rid);
        else complete(rid);
      });
    });
  }

  function showMessage(text, bad = false) {
    msg.className = bad ? 'v2-error' : 'v2-muted';
    msg.textContent = text || '';
    if (text) setTimeout(() => { msg.textContent = ''; msg.className = ''; }, 3000);
  }

  function complete(routineId) {
    const state = loadState();
    state.completions.push({ id: id('completion'), routine_id: routineId, completed_at: nowIso(), completed_date: todayIso() });
    saveState(state);
    render();
  }

  function undoToday(routineId) {
    const state = loadState();
    const today = todayIso();
    const idx = state.completions.map((c, i) => ({ c, i })).filter(x => x.c.routine_id === routineId && x.c.completed_date === today && !x.c.deleted).pop()?.i;
    if (idx !== undefined) state.completions.splice(idx, 1);
    saveState(state);
    render();
  }

  function openForm(routine = null) {
    form.classList.add('open');
    editId.value = routine ? routine.id : '';
    $('formTitle').textContent = routine ? 'Edit routine' : 'Add routine';
    nameInput.value = routine?.name || '';
    areaInput.value = routine?.area || '';
    typeInput.value = routine?.repeat_type || 'every_n_days';
    valueInput.value = routine?.repeat_value || 1;
    daysInput.value = (routine?.days_of_week || []).map(d => weekdays[d]).join(', ');
    notesInput.value = routine?.notes || '';
    deleteBtn.style.display = routine ? '' : 'none';
    syncForm();
    nameInput.focus();
  }

  function closeForm() { form.classList.remove('open'); editId.value = ''; }

  function syncForm() {
    const type = typeInput.value;
    valueLabel.style.display = type === 'daily' || type === 'weekdays' ? 'none' : '';
    daysLabel.style.display = type === 'weekdays' ? '' : 'none';
  }

  function saveForm() {
    const name = nameInput.value.trim();
    if (!name) { showMessage('Name is required.', true); return; }
    const type = typeInput.value;
    const state = loadState();
    const existingId = editId.value;
    const next = {
      id: existingId || id('routine'),
      name,
      area: areaInput.value.trim() || 'General',
      repeat_type: type,
      repeat_value: normalizeValue(type, valueInput.value),
      days_of_week: type === 'weekdays' ? parseWeekdays(daysInput.value) : [],
      notes: notesInput.value.trim(),
      active: true,
      created_at: nowIso(),
      updated_at: nowIso()
    };
    if (type === 'weekdays' && next.days_of_week.length === 0) { showMessage('Add at least one weekday.', true); return; }
    const idx = state.routines.findIndex(r => r.id === existingId);
    if (idx >= 0) state.routines[idx] = { ...state.routines[idx], ...next, created_at: state.routines[idx].created_at || next.created_at };
    else state.routines.push(next);
    saveState(state);
    closeForm();
    render();
  }

  function deleteCurrent() {
    const rid = editId.value;
    if (!rid) return;
    const state = loadState();
    const r = state.routines.find(x => x.id === rid);
    if (r) { r.active = false; r.deleted = true; r.updated_at = nowIso(); }
    saveState(state);
    closeForm();
    render();
  }

  function exportState() {
    const data = JSON.stringify(loadState(), null, 2);
    navigator.clipboard?.writeText(data).then(() => showMessage('Copied routines v2 JSON.')).catch(() => {
      const w = window.open('', '_blank');
      if (w) w.document.write(`<pre>${esc(data)}</pre>`);
    });
  }

  $('addBtn').addEventListener('click', () => openForm());
  $('cancelBtn').addEventListener('click', closeForm);
  $('saveBtn').addEventListener('click', saveForm);
  $('deleteBtn').addEventListener('click', deleteCurrent);
  $('exportBtn').addEventListener('click', exportState);
  typeInput.addEventListener('change', syncForm);
  render();
})();
