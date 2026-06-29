/* Today — an ADHD-friendly daily focus view.
 *
 * Design goals (from research): reward the moment not the outcome, immediate
 * visual + haptic feedback on every tap, two-taps-max, cumulative XP instead of
 * shame-based streaks, one clear focus, calm by default, respect Reduce Motion.
 *
 * Data is bootstrapped server-side in window.__TODAY__ (current week's cards +
 * past completion history), so first paint needs zero network calls. Taps update
 * the UI optimistically and PATCH the existing /set-dot API in the background.
 */
(function () {
  const BOOT = window.__TODAY__ || {};
  const SEL = BOOT.today;
  const WEEK_KEY = BOOT.week_key;
  const DAY_INDEX = Number(BOOT.day_index || 0);
  const cards = BOOT.cards || {};
  const MS_DAY = 86400000;
  const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- preferences (localStorage) ----
  const PREF_SOUND = 'lm:today:sound';
  const PREF_HAPTICS = 'lm:today:haptics';
  let soundOn = localStorage.getItem(PREF_SOUND) === '1';
  let hapticsOn = localStorage.getItem(PREF_HAPTICS) !== '0';

  // ---- gamification state (localStorage) ----
  const XP_KEY = 'lm:today:xp';
  const CELEB_KEY = 'lm:today:celebrated';
  function getXp() { return Math.max(0, parseInt(localStorage.getItem(XP_KEY) || '0', 10) || 0); }
  function setXp(v) { localStorage.setItem(XP_KEY, String(Math.max(0, v))); }

  // ---- skip (this session only) + plan-a-date (persisted) ----
  const skipped = new Set();
  const PLAN_KEY = 'lm:today:plans';
  function getPlans() {
    let p = {};
    try { p = JSON.parse(localStorage.getItem(PLAN_KEY) || '{}') || {}; } catch (e) { p = {}; }
    // Once the planned date arrives (or passes), drop it so the task returns to today.
    let changed = false;
    Object.keys(p).forEach((k) => { if (!p[k] || p[k] <= SEL) { delete p[k]; changed = true; } });
    if (changed) localStorage.setItem(PLAN_KEY, JSON.stringify(p));
    return p;
  }
  function setPlan(key, dateStr) { const p = getPlans(); if (dateStr && dateStr > SEL) p[key] = dateStr; else delete p[key]; localStorage.setItem(PLAN_KEY, JSON.stringify(p)); }
  function clearPlan(key) { const p = getPlans(); delete p[key]; localStorage.setItem(PLAN_KEY, JSON.stringify(p)); }
  function planKeyOf(r) { return r.areaKey + '::' + r.name; }

  // ---- date / freq helpers (ported from the proven routine logic) ----
  function parseIso(s) { return new Date(String(s || '').slice(0, 10) + 'T00:00:00'); }
  function iso(d) { return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }
  function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
  function daysBetween(a, b) { return Math.round((parseIso(a) - parseIso(b)) / MS_DAY); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
  function isDaily(freq) { return Number(freq || 0) >= 7; }
  function intervalDays(freq) { const f = Number(freq || 0); if (!Number.isFinite(f) || f <= 0) return 9999; if (f >= 7) return 1; return Math.max(1, Math.round(7 / f)); }
  function keyOf(areaKey, name) { return areaKey + '::' + name; }
  function dateLabel(dIso) { return parseIso(dIso).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC' }); }

  function dailyBucket(name) {
    const n = String(name || '').toLowerCase();
    if (n.includes('brush') || n.includes('floss') || n.includes('coffee') || n.includes('breakfast') || n.includes('vitamin') || n.includes('med') || n.includes('morning')) return 'Morning';
    if (n.includes('dinner') || n.includes('evening') || n.includes('bed') || n.includes('trash') || n.includes('dish') || n.includes('night')) return 'Evening';
    return 'Midday';
  }

  // ---- build the model from bootstrapped cards + history ----
  function buildHistory() {
    const hist = {};
    Object.keys(BOOT.history || {}).forEach((k) => { hist[k] = (BOOT.history[k] || []).slice(); });
    // Overlay current week completions from the live cards (kept fresh on every tap).
    Object.keys(cards).forEach((ak) => {
      const card = cards[ak];
      const ws = card.week_start;
      if (!ws) return;
      (card.tasks || []).forEach((task) => {
        const key = keyOf(card.area_key || ak, task.name || '');
        (task.days || []).forEach((row, di) => {
          if (!row || !row.some(Boolean)) return;
          const d = iso(addDays(parseIso(ws), di));
          if (d > SEL) return;
          (hist[key] = hist[key] || []).push(d);
        });
      });
    });
    Object.keys(hist).forEach((k) => { hist[k] = Array.from(new Set(hist[k])).sort(); });
    return hist;
  }

  function dailyCount(task) {
    const freqCount = Math.max(1, Math.round(Number(task.freq || 7) / 7));
    const scheduledMax = Math.max(0, ...((task.scheduled || []).map((n) => Number(n || 0))));
    const rowMax = Math.max(0, ...((task.days || []).map((r) => (Array.isArray(r) ? r.length : 0))));
    return Math.max(1, freqCount, scheduledMax, rowMax);
  }

  function recurringStatus(task, areaKey, hist) {
    const completions = (hist[keyOf(areaKey, task.name)] || []).filter((d) => d <= SEL).sort();
    const doneToday = completions.includes(SEL);
    const last = completions.length ? completions[completions.length - 1] : null;
    const interval = intervalDays(task.freq);
    let dueIso;
    if (last) dueIso = iso(addDays(parseIso(last), interval));
    else {
      const sched = [];
      const start = parseIso(cards[areaKey] ? cards[areaKey].week_start : SEL);
      (task.scheduled || []).forEach((n, di) => { if (Number(n || 0) > 0) sched.push(iso(addDays(start, di))); });
      dueIso = sched.find((d) => d >= SEL) || sched.filter((d) => d <= SEL).pop() || SEL;
    }
    if (doneToday) return { status: 'done', dueIso, label: 'Done today' };
    const delta = daysBetween(SEL, dueIso);
    if (delta > 0) return { status: 'overdue', dueIso, label: delta + (delta === 1 ? ' day' : ' days') + ' overdue' };
    if (delta === 0) return { status: 'due', dueIso, label: 'Due today' };
    if (delta >= -10) return { status: 'upcoming', dueIso, label: 'Due ' + dateLabel(dueIso) };
    return { status: 'later', dueIso, label: 'Due ' + dateLabel(dueIso) };
  }

  function buildRows() {
    const hist = buildHistory();
    const rows = [];
    Object.keys(cards).forEach((ak) => {
      const card = cards[ak];
      const areaKey = card.area_key || ak;
      const areaName = card.area_name || areaKey;
      (card.tasks || []).forEach((task, taskIndex) => {
        const id = (isDaily(task.freq) ? 'd' : 'r') + ':' + areaKey + ':' + taskIndex;
        if (isDaily(task.freq)) {
          const total = dailyCount(task);
          const row = (task.days && task.days[DAY_INDEX]) || [];
          let done = 0;
          for (let i = 0; i < total; i++) if (row[i]) done++;
          rows.push({ id, kind: 'daily', areaKey, areaName, task, taskIndex, name: task.name || '', bucket: dailyBucket(task.name), total, done, complete: done >= total });
        } else {
          const st = recurringStatus(task, areaKey, hist);
          rows.push({ id, kind: 'recurring', areaKey, areaName, task, taskIndex, name: task.name || '', status: st.status, label: st.label, dueIso: st.dueIso, complete: st.status === 'done' });
        }
      });
    });
    const plans = getPlans();
    rows.forEach((r) => { const pd = plans[planKeyOf(r)]; r.plannedDate = (pd && pd > SEL) ? pd : null; });
    return rows;
  }

  // ---- progress / goal ----
  function computeProgress(rows) {
    let total = 0, done = 0;
    rows.forEach((r) => {
      if (r.plannedDate) return; // deferred to a future day; not part of today's goal
      if (r.kind === 'daily') { total += r.total; done += r.done; }
      else if (r.status === 'overdue' || r.status === 'due' || r.status === 'done') { total += 1; if (r.complete) done += 1; }
    });
    return { total, done, pct: total ? Math.round((done / total) * 100) : 100 };
  }

  // ---- streak (forgiving: 1 completion = active day, one grace gap allowed) ----
  function computeStreak(hist) {
    const counts = {};
    Object.keys(hist).forEach((k) => (hist[k] || []).forEach((d) => { counts[d] = (counts[d] || 0) + 1; }));
    const active = (d) => (counts[d] || 0) > 0;
    const last7 = [];
    for (let i = 6; i >= 0; i--) { const d = iso(addDays(parseIso(SEL), -i)); last7.push({ d, on: active(d), today: d === SEL }); }
    let streak = 0, grace = 1;
    let cursor = active(SEL) ? 0 : 1; // if today not done yet, count from yesterday so it doesn't read 0 mid-day
    for (let i = cursor; i < 400; i++) {
      const d = iso(addDays(parseIso(SEL), -i));
      if (active(d)) streak++;
      else if (grace > 0 && streak > 0) { grace--; }
      else break;
    }
    return { streak, last7 };
  }

  // ---- feedback: haptics, sound, xp float, confetti ----
  function haptic(pattern) { if (hapticsOn && navigator.vibrate) { try { navigator.vibrate(pattern); } catch (e) {} } }
  let audioCtx = null;
  function beep(freqs) {
    if (!soundOn) return;
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      const t0 = audioCtx.currentTime;
      freqs.forEach((f, i) => {
        const o = audioCtx.createOscillator(); const g = audioCtx.createGain();
        o.type = 'sine'; o.frequency.value = f;
        const st = t0 + i * 0.09;
        g.gain.setValueAtTime(0.0001, st); g.gain.exponentialRampToValueAtTime(0.18, st + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, st + 0.18);
        o.connect(g); g.connect(audioCtx.destination); o.start(st); o.stop(st + 0.2);
      });
    } catch (e) {}
  }
  function xpFloat(x, y, text) {
    if (reduceMotion) return;
    const el = document.createElement('div'); el.className = 'xp-float'; el.textContent = text;
    el.style.left = (x - 16) + 'px'; el.style.top = (y - 24) + 'px';
    document.body.appendChild(el); setTimeout(() => el.remove(), 1000);
  }

  const confettiCanvas = document.getElementById('confetti');
  function confettiBurst(big) {
    if (reduceMotion || !confettiCanvas) return;
    const ctx = confettiCanvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    confettiCanvas.width = innerWidth * dpr; confettiCanvas.height = innerHeight * dpr; ctx.scale(dpr, dpr);
    const colors = ['#38bdf8', '#818cf8', '#4ade80', '#fbbf24', '#fb7185', '#c084fc'];
    const n = big ? 160 : 36;
    const parts = [];
    const ox = innerWidth / 2, oy = big ? innerHeight * 0.32 : innerHeight * 0.4;
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2; const sp = (big ? 5 : 3) + Math.random() * (big ? 9 : 5);
      parts.push({ x: ox, y: oy, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp - (big ? 4 : 2), c: colors[i % colors.length], s: 4 + Math.random() * 5, rot: Math.random() * 6, vr: (Math.random() - 0.5) * 0.4, life: 0 });
    }
    let raf;
    function frame() {
      ctx.clearRect(0, 0, innerWidth, innerHeight);
      let alive = false;
      parts.forEach((p) => {
        p.life++; p.vy += 0.16; p.x += p.vx; p.y += p.vy; p.rot += p.vr;
        const o = Math.max(0, 1 - p.life / (big ? 110 : 70));
        if (o > 0) { alive = true; ctx.save(); ctx.globalAlpha = o; ctx.translate(p.x, p.y); ctx.rotate(p.rot); ctx.fillStyle = p.c; ctx.fillRect(-p.s / 2, -p.s / 2, p.s, p.s * 0.6); ctx.restore(); }
      });
      if (alive) raf = requestAnimationFrame(frame); else ctx.clearRect(0, 0, innerWidth, innerHeight);
    }
    cancelAnimationFrame(raf); frame();
  }

  // ---- celebration ----
  const CELEBRATE_MSGS = [
    "Every single thing — done. Your brain earned this.",
    "Full clear. That momentum is yours to keep.",
    "You showed up and finished. That's the whole game.",
    "Done and dusted. Future-you is grateful.",
    "Nailed the day. Go enjoy the dopamine. 🧠",
  ];
  function celebrate() {
    if (localStorage.getItem(CELEB_KEY) === SEL) return;
    localStorage.setItem(CELEB_KEY, SEL);
    setXp(getXp() + 25);
    const overlay = document.getElementById('celebrate');
    document.getElementById('celebrate-msg').textContent = CELEBRATE_MSGS[Math.floor(Math.random() * CELEBRATE_MSGS.length)];
    overlay.classList.add('show');
    haptic([0, 50, 40, 80]); beep([523, 659, 784, 1047]); confettiBurst(true);
    renderHero(lastRows);
  }
  function closeCelebrate() { document.getElementById('celebrate').classList.remove('show'); }

  // ---- headlines (novelty) ----
  const HEADLINES = [
    "Let's make today count", "One tap at a time", "You've got this", "Small wins stack up",
    "Pick one thing. Start there.", "Progress over perfect", "Future-you says thanks", "Tiny steps, real momentum",
  ];
  const NICE = ["Nice.", "Boom.", "Got it.", "Yes!", "Clean.", "Done.", "Sweet.", "Crushed it."];

  // ---- rendering ----
  let lastRows = [];
  let lastUpNext = null;

  function plannedCardHtml(r) {
    return '<button type="button" class="tk planned" data-unplan="' + esc(planKeyOf(r)) + '">' +
      '<span class="tk-check">📅</span>' +
      '<span class="tk-body"><span class="tk-name">' + esc(r.name) + '</span><span class="tk-sub">Planned for ' + esc(dateLabel(r.plannedDate)) + ' · tap to bring back · ' + esc(r.areaName) + '</span></span>' +
      '</button>';
  }
  function renderHero(rows) {
    const prog = computeProgress(rows);
    const ring = document.getElementById('ring');
    const C = 2 * Math.PI * 82;
    document.getElementById('ring-fg').setAttribute('stroke-dashoffset', String(C * (1 - prog.pct / 100)));
    document.getElementById('ring-pct').textContent = prog.pct + '%';
    document.getElementById('ring-sub').textContent = prog.total ? (prog.done + ' of ' + prog.total + ' done') : 'All clear';
    ring.classList.toggle('ring-done', prog.pct >= 100);

    const xp = getXp(); const within = xp % 100; const level = Math.floor(xp / 100) + 1;
    document.getElementById('level-badge').textContent = 'Lv ' + level;
    document.getElementById('xp-fill').style.width = within + '%';
    document.getElementById('xp-label').textContent = within + ' / 100 XP';

    const { streak, last7 } = computeStreak(buildHistory());
    document.getElementById('streak-flame').textContent = '🔥 ' + streak;
    document.getElementById('streak-dots').innerHTML = last7.map((x) => '<span class="d' + (x.on ? ' on' : '') + (x.today ? ' today' : '') + '"></span>').join('');
    return prog;
  }

  function taskCardHtml(r) {
    let cls = 'tk', icon = '○', sub = '', pill = '';
    if (r.kind === 'daily') {
      cls += ' daily' + (r.complete ? ' done' : '');
      icon = r.complete ? '✓' : '○';
      sub = r.bucket + ' · ' + r.areaName;
      if (r.total > 1) pill = '<span class="tk-pill">' + r.done + '/' + r.total + '</span>';
    } else {
      cls += ' ' + (r.complete ? 'done' : r.status);
      icon = r.complete ? '✓' : (r.status === 'overdue' ? '!' : '○');
      sub = r.label + ' · ' + r.areaName;
    }
    return '<button type="button" class="' + cls + '" data-id="' + esc(r.id) + '">' +
      '<span class="tk-check">' + icon + '</span>' +
      '<span class="tk-body"><span class="tk-name">' + esc(r.name) + '</span><span class="tk-sub">' + esc(sub) + '</span></span>' +
      pill + '</button>';
  }

  function sectionHtml(title, list, extraClass) {
    if (!list.length) return '';
    return '<div class="section ' + (extraClass || '') + '"><div class="section-title"><h2>' + esc(title) + '</h2><span class="count">' + list.length + '</span></div>' +
      list.map(taskCardHtml).join('') + '</div>';
  }

  function pickUpNext(rows) {
    const order = (r) => {
      if (r.complete) return 99;
      if (r.kind === 'recurring' && r.status === 'overdue') return 0;
      if (r.kind === 'recurring' && r.status === 'due') return 1;
      if (r.kind === 'daily' && r.bucket === 'Morning') return 2;
      if (r.kind === 'daily' && r.bucket === 'Midday') return 3;
      if (r.kind === 'daily' && r.bucket === 'Evening') return 4;
      if (r.kind === 'recurring' && r.status === 'upcoming') return 6;
      return 7;
    };
    const cand = rows.filter((r) => !r.complete && !r.plannedDate && !skipped.has(r.id)).sort((a, b) => order(a) - order(b));
    return cand[0] || null;
  }

  function render(justId) {
    const rows = buildRows();
    lastRows = rows;
    const prog = renderHero(rows);

    // Up Next
    const upWrap = document.getElementById('up-next');
    const next = pickUpNext(rows);
    lastUpNext = next;
    if (!next) {
      upWrap.innerHTML = '<div class="upnext alldone"><div class="un-label">All done</div><div class="un-name">Nothing left for today 🎉</div><div class="un-sub">Everything due is checked off. Rest is productive too.</div></div>';
    } else {
      const sub = next.kind === 'daily' ? (next.bucket + ' · ' + next.areaName + (next.total > 1 ? ' · ' + next.done + '/' + next.total : '')) : (next.label + ' · ' + next.areaName);
      const planDefault = (next.dueIso && next.dueIso > SEL) ? next.dueIso : iso(addDays(parseIso(SEL), 1));
      upWrap.innerHTML = '<div class="upnext"><div class="un-label">Up next</div><div class="un-name">' + esc(next.name) + '</div><div class="un-sub">' + esc(sub) + '</div>' +
        '<button type="button" class="un-btn" data-id="' + esc(next.id) + '">Do it ✓</button>' +
        '<div class="un-actions"><button type="button" data-act="skip">Skip for now</button><button type="button" data-act="plan">📅 Plan a date</button></div>' +
        '<input type="date" class="un-plan-input" data-plan-input min="' + esc(iso(addDays(parseIso(SEL), 1))) + '" value="' + esc(planDefault) + '">' +
        '<div class="un-plan-hint">Pick the day you\'ll actually do it — it\'ll wait in “Planned” until then.</div></div>';
    }

    // Sections
    const daily = rows.filter((r) => r.kind === 'daily');
    const rec = rows.filter((r) => r.kind === 'recurring');
    const buckets = ['Morning', 'Midday', 'Evening'];
    let html = '';
    const dailyOpen = daily.filter((r) => !r.complete && !r.plannedDate);
    buckets.forEach((b) => { html += sectionHtml(b, dailyOpen.filter((r) => r.bucket === b)); });
    const due = rec.filter((r) => (r.status === 'overdue' || r.status === 'due') && !r.plannedDate);
    html += sectionHtml('Due', due.sort((a, b) => (a.status === 'overdue' ? 0 : 1) - (b.status === 'overdue' ? 0 : 1)));

    const planned = rows.filter((r) => r.plannedDate).sort((a, b) => (a.plannedDate || '').localeCompare(b.plannedDate || ''));
    if (planned.length) {
      html += '<div class="section"><div class="section-title"><h2>Planned</h2><span class="count">' + planned.length + '</span></div>' +
        planned.map(plannedCardHtml).join('') + '</div>';
    }

    const coming = rec.filter((r) => (r.status === 'upcoming' || r.status === 'later') && !r.plannedDate).sort((a, b) => (a.dueIso || '').localeCompare(b.dueIso || ''));
    if (coming.length) {
      html += '<div class="section"><div class="section-title"><h2>Coming up</h2><span class="count">' + coming.length + '</span></div>' +
        '<div id="coming-list" style="display:none">' + coming.map(taskCardHtml).join('') + '</div>' +
        '<button type="button" class="show-more" id="show-coming">Show ' + coming.length + ' upcoming</button></div>';
    }

    const done = rows.filter((r) => r.complete);
    if (done.length) html += sectionHtml('Done today', done, 'done-section');

    if (!rows.length) html += '<div class="empty">No routines set up yet. Add some in the <a href="/cards">classic view</a>.</div>';
    document.getElementById('sections').innerHTML = html;

    if (justId) {
      const el = document.querySelector('[data-id="' + (window.CSS && CSS.escape ? CSS.escape(justId) : justId) + '"].tk');
      if (el && !reduceMotion) { el.classList.add('pop'); setTimeout(() => el.classList.remove('pop'), 450); }
    }

    if (prog.total > 0 && prog.done >= prog.total) celebrate();
  }

  // ---- tap handling (optimistic) ----
  function findRow(id) { return lastRows.find((r) => r.id === id); }

  function applyToggle(r) {
    // Decide which dot to flip for the selected day, and the new value.
    const card = cards[r.areaKey];
    if (!card) return null;
    const task = card.tasks[r.taskIndex];
    if (!task) return null;
    task.days = task.days || [];
    if (!Array.isArray(task.days[DAY_INDEX])) task.days[DAY_INDEX] = [false];
    const row = task.days[DAY_INDEX];
    const count = r.kind === 'daily' ? dailyCount(task) : 1;
    while (row.length < count) row.push(false);
    let doneCount = 0; for (let i = 0; i < count; i++) if (row[i]) doneCount++;
    let dot, value;
    if (doneCount < count) { dot = row.findIndex((v, i) => i < count && !v); if (dot < 0) dot = doneCount; value = true; }
    else { for (let i = count - 1; i >= 0; i--) { if (row[i]) { dot = i; break; } } value = false; }
    row[dot] = value;
    return { dot, value };
  }

  function onActivate(id, x, y) {
    const r = findRow(id);
    if (!r) return;
    const res = applyToggle(r);
    if (!res) return;

    if (res.value) {
      setXp(getXp() + 10);
      haptic(15); beep([660, 880]);
      if (typeof x === 'number') xpFloat(x, y, '+10');
    } else {
      setXp(getXp() - 10);
      haptic(8);
    }

    render(id);

    // Persist in the background; revert on hard failure.
    fetch('/api/routine-cards/' + encodeURIComponent(WEEK_KEY) + '/' + encodeURIComponent(r.areaKey) + '/set-dot', {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: r.taskIndex, day: DAY_INDEX, dot: res.dot, value: res.value, list: 'tasks' }),
    }).then((resp) => { if (!resp.ok) throw new Error('save failed'); }).catch(() => {
      // revert
      const card = cards[r.areaKey];
      if (card && card.tasks[r.taskIndex] && card.tasks[r.taskIndex].days[DAY_INDEX]) {
        card.tasks[r.taskIndex].days[DAY_INDEX][res.dot] = !res.value;
        setXp(getXp() + (res.value ? -10 : 10));
        render();
      }
    });
  }

  // ---- wire up ----
  function setHeadline() {
    const idx = Math.abs(parseIso(SEL).getTime() / MS_DAY | 0) % HEADLINES.length;
    document.getElementById('headline').textContent = BOOT.is_today ? HEADLINES[idx] : 'Catching up on ' + dateLabel(SEL);
    document.getElementById('hero-date').textContent = parseIso(SEL).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', timeZone: 'UTC' });
  }

  function refreshPrefButtons() {
    const sb = document.getElementById('toggle-sound');
    const hb = document.getElementById('toggle-haptics');
    sb.textContent = soundOn ? '🔊 Sound on' : '🔈 Sound off'; sb.classList.toggle('on', soundOn);
    hb.textContent = hapticsOn ? '📳 Haptics on' : '📴 Haptics off'; hb.classList.toggle('on', hapticsOn);
  }

  function init() {
    setHeadline();
    refreshPrefButtons();
    render();

    function handler(e) {
      const btn = e.target.closest('[data-id]');
      if (!btn) return;
      onActivate(btn.getAttribute('data-id'), e.clientX, e.clientY);
    }
    document.getElementById('sections').addEventListener('click', handler);
    document.getElementById('up-next').addEventListener('click', handler);
    document.getElementById('sections').addEventListener('click', (e) => {
      if (e.target.id === 'show-coming') { const l = document.getElementById('coming-list'); if (l) l.style.display = 'block'; e.target.style.display = 'none'; return; }
      const un = e.target.closest('[data-unplan]');
      if (un) { clearPlan(un.getAttribute('data-unplan')); render(); }
    });

    // Up next: Skip (surface a different task this session) / Plan a date (defer).
    document.getElementById('up-next').addEventListener('click', (e) => {
      const act = e.target.closest('[data-act]');
      if (!act || !lastUpNext) return;
      const a = act.getAttribute('data-act');
      if (a === 'skip') { skipped.add(lastUpNext.id); render(); }
      else if (a === 'plan') {
        const up = act.closest('.upnext');
        const inp = up && up.querySelector('[data-plan-input]');
        if (up) up.classList.add('planning');
        if (inp) { inp.focus(); if (inp.showPicker) { try { inp.showPicker(); } catch (err) {} } }
      }
    });
    document.getElementById('up-next').addEventListener('change', (e) => {
      const inp = e.target.closest('[data-plan-input]');
      if (!inp || !lastUpNext) return;
      if (inp.value) { setPlan(planKeyOf(lastUpNext), inp.value); haptic(10); render(); }
    });

    document.getElementById('celebrate-close').addEventListener('click', closeCelebrate);
    document.getElementById('celebrate').addEventListener('click', (e) => { if (e.target.id === 'celebrate') closeCelebrate(); });

    document.getElementById('toggle-sound').addEventListener('click', () => { soundOn = !soundOn; localStorage.setItem(PREF_SOUND, soundOn ? '1' : '0'); refreshPrefButtons(); if (soundOn) beep([660, 880]); });
    document.getElementById('toggle-haptics').addEventListener('click', () => { hapticsOn = !hapticsOn; localStorage.setItem(PREF_HAPTICS, hapticsOn ? '1' : '0'); refreshPrefButtons(); if (hapticsOn) haptic(15); });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
