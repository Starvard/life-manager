 /* Today — timed daily plan + flex slots + bonus + waterfall timers.
 *
 * Day plan = timed tasks for today (sorted by time) plus flex slots that
 * each pull one due non-daily from the right pool. Bonus holds remaining
 * non-dailies and does not count toward the progress ring.
 *
 * Timers cascade: each step's duration is the gap to the next timeline
 * anchor; completing or swipe-skipping starts the next step from "now".
 */
(function () {
  const BOOT = window.__TODAY__ || {};
  const SEL = BOOT.today;
  const WEEK_KEY = BOOT.week_key;
  const DAY_INDEX = Number(BOOT.day_index || 0);
  const cards = BOOT.cards || {};
  const FLEX_SLOTS = Array.isArray(BOOT.daily_flex_slots) ? BOOT.daily_flex_slots : [];
  let timeline = BOOT.timeline || { items: [], resolved: {}, now: null };
  const MS_DAY = 86400000;
  const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const PREF_SOUND = 'lm:today:sound';
  const PREF_HAPTICS = 'lm:today:haptics';
  let soundOn = localStorage.getItem(PREF_SOUND) === '1';
  let hapticsOn = localStorage.getItem(PREF_HAPTICS) !== '0';

  const XP_KEY = 'lm:today:xp';
  const CELEB_KEY = 'lm:today:celebrated';
  function getXp() { return Math.max(0, parseInt(localStorage.getItem(XP_KEY) || '0', 10) || 0); }
  function setXp(v) { localStorage.setItem(XP_KEY, String(Math.max(0, v))); }

  // Session-only skip for Bonus recurrings. Day-plan skips persist via API.
  const sessionSkipped = new Set();
  const PLAN_KEY = 'lm:today:plans';
  function getPlans() {
    let p = {};
    try { p = JSON.parse(localStorage.getItem(PLAN_KEY) || '{}') || {}; } catch (e) { p = {}; }
    let changed = false;
    Object.keys(p).forEach((k) => { if (!p[k] || p[k] <= SEL) { delete p[k]; changed = true; } });
    if (changed) localStorage.setItem(PLAN_KEY, JSON.stringify(p));
    return p;
  }
  function setPlan(key, dateStr) { const p = getPlans(); if (dateStr && dateStr > SEL) p[key] = dateStr; else delete p[key]; localStorage.setItem(PLAN_KEY, JSON.stringify(p)); }
  function clearPlan(key) { const p = getPlans(); delete p[key]; localStorage.setItem(PLAN_KEY, JSON.stringify(p)); }
  function planKeyOf(r) { return r.areaKey + '::' + r.name; }

  function parseIso(s) { return new Date(String(s || '').slice(0, 10) + 'T00:00:00'); }
  function iso(d) { return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }
  function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
  function daysBetween(a, b) { return Math.round((parseIso(a) - parseIso(b)) / MS_DAY); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
  function isDaily(freq) { return Number(freq || 0) >= 7; }
  function intervalDays(freq) { const f = Number(freq || 0); if (!Number.isFinite(f) || f <= 0) return 9999; if (f >= 7) return 1; return Math.max(1, Math.round(7 / f)); }
  function keyOf(areaKey, name) { return areaKey + '::' + name; }
  function stateKeyOf(r) { return (r.areaKey || '') + '::' + (r.listKey || 'tasks') + '::' + (r.name || ''); }
  function dateLabel(dIso) { return parseIso(dIso).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC' }); }
  function normTime(t) {
    if (!t) return null;
    const s = String(t).trim();
    const m = s.match(/^(\d{1,2}):(\d{2})/);
    if (!m) return null;
    return String(Math.max(0, Math.min(23, parseInt(m[1], 10)))).padStart(2, '0') + ':' + String(Math.max(0, Math.min(59, parseInt(m[2], 10)))).padStart(2, '0');
  }
  function formatTime(hhmm) {
    const t = normTime(hhmm);
    if (!t) return '';
    let h = parseInt(t.slice(0, 2), 10);
    const m = t.slice(3);
    const ap = h >= 12 ? 'pm' : 'am';
    h = h % 12; if (h === 0) h = 12;
    return h + ':' + m + ap;
  }
  function parseDt(s) {
    if (!s) return null;
    const d = new Date(s);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  function formatCountdown(ms) {
    const abs = Math.abs(ms);
    const totalSec = Math.floor(abs / 1000);
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    if (m >= 60) {
      const h = Math.floor(m / 60);
      const rm = m % 60;
      return h + 'h ' + rm + 'm';
    }
    return m + ':' + String(s).padStart(2, '0');
  }
  function timelineByKey() {
    const map = {};
    (timeline.items || []).forEach((it) => {
      if (it && it.key) map[it.key] = it;
    });
    return map;
  }
  function isPersistedSkipped(r) {
    const entry = (timeline.resolved || {})[stateKeyOf(r)];
    return !!(entry && entry.status === 'skipped');
  }
  function flexSkipKeys(flexKey) {
    if (!flexKey) return new Set();
    const bucket = (timeline.flex_skips || {})[flexKey] || {};
    return new Set(Object.keys(bucket));
  }
  function applyTimeline(tl) {
    if (!tl) return;
    timeline = tl;
    BOOT.timeline = tl;
  }

  function buildHistory() {
    const hist = {};
    Object.keys(BOOT.history || {}).forEach((k) => { hist[k] = (BOOT.history[k] || []).slice(); });
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

  function scheduledToday(task) {
    const sched = task.scheduled || [];
    return Number(sched[DAY_INDEX] || 0) > 0;
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
        const time = normTime(task.time);
        const atWork = !!task.at_work;
        const schedToday = scheduledToday(task);
        // Timed + scheduled today (incl. weekday work via freq 5 + on_days):
        // treat like a daily slot so completion is today's dots, not history.
        if (isDaily(task.freq) || (time && schedToday)) {
          const total = isDaily(task.freq) ? dailyCount(task) : Math.max(1, Number((task.scheduled || [])[DAY_INDEX] || 1));
          const row = (task.days && task.days[DAY_INDEX]) || [];
          let done = 0;
          for (let i = 0; i < total; i++) if (row[i]) done++;
          rows.push({
            id, kind: 'daily', areaKey, areaName, task, taskIndex, listKey: 'tasks',
            name: task.name || '', time, atWork, total, done,
            complete: done >= total,
            onPlan: !!time && (isDaily(task.freq) || schedToday),
          });
        } else {
          const st = recurringStatus(task, areaKey, hist);
          // Weekday-only timed tasks (work Mon–Fri, trash Tue) only belong on
          // the day plan when scheduled today — not as weekend overdue clutter.
          const onTimeline = !!time && schedToday;
          rows.push({
            id, kind: 'recurring', areaKey, areaName, task, taskIndex, listKey: 'tasks',
            name: task.name || '', time, atWork,
            status: st.status, label: st.label, dueIso: st.dueIso,
            complete: st.status === 'done',
            onPlan: onTimeline,
          });
        }
      });
    });
    const plans = getPlans();
    rows.forEach((r) => { const pd = plans[planKeyOf(r)]; r.plannedDate = (pd && pd > SEL) ? pd : null; });
    return rows;
  }

  function flexPriority(r) {
    if (r.complete || r.plannedDate) return 99;
    if (r.kind !== 'recurring') return 99;
    if (r.status === 'overdue') return 0;
    if (r.status === 'due') return 1;
    if (r.status === 'upcoming') return 2;
    return 3;
  }

  function pinnedToOtherWeekday(task) {
    // Tasks with on_days (e.g. Trash on Tuesday) keep scheduled[] dots only on
    // those weekdays. Do not pull them into a flex slot on other days — they
    // belong in Bonus (or on the timed timeline when overdue + timed).
    const sched = task.scheduled || [];
    const today = Number(sched[DAY_INDEX] || 0) > 0;
    if (today) return false;
    return sched.some((n) => Number(n || 0) > 0);
  }

  function pickFlex(rows, pool, usedIds, flexKey) {
    const slotSkipped = flexSkipKeys(flexKey);
    const cand = rows.filter((r) => {
      if (usedIds.has(r.id) || r.complete || r.plannedDate || sessionSkipped.has(r.id) || isPersistedSkipped(r)) return false;
      if (slotSkipped.has(stateKeyOf(r))) return false; // skipped in THIS flex only
      if (r.kind !== 'recurring') return false;
      if (r.time) return false; // timed rows stay on the clock timeline, never flex
      if (pinnedToOtherWeekday(r.task)) return false;
      if (pool === 'at_work') return !!r.atWork;
      return !r.atWork; // home pool
    }).sort((a, b) => flexPriority(a) - flexPriority(b) || (a.dueIso || '').localeCompare(b.dueIso || ''));
    return cand[0] || null;
  }

  function buildDayPlan(rows) {
    const used = new Set();
    const items = [];
    const tmap = timelineByKey();

    rows.forEach((r) => {
      // Completed / day-skipped timed steps leave the day plan (Done / Skipped).
      if (!r.onPlan || !r.time || r.plannedDate || r.complete || sessionSkipped.has(r.id) || isPersistedSkipped(r)) return;
      const tl = tmap[stateKeyOf(r)];
      items.push({
        sortTime: r.time,
        displayTime: tl && tl.effective_start ? tl.effective_start : r.time,
        row: r,
        flex: null,
        timeline: tl || null,
      });
      used.add(r.id);
    });

    FLEX_SLOTS.forEach((slot) => {
      const t = normTime(slot.time);
      if (!t) return;
      const days = Array.isArray(slot.on_days) ? slot.on_days.map(Number) : null;
      if (days && days.length && days.indexOf(DAY_INDEX) < 0) return; // e.g. work flex Mon–Fri only
      const pick = pickFlex(rows, slot.pool || 'home', used, slot.key);
      if (!pick) {
        items.push({
          sortTime: t,
          row: null,
          flex: { key: slot.key, label: slot.label || 'Flex', empty: true, pool: slot.pool },
        });
        return;
      }
      used.add(pick.id);
      const tl = tmap[stateKeyOf(pick)];
      items.push({
        sortTime: t,
        displayTime: tl && tl.effective_start ? tl.effective_start : t,
        row: pick,
        flex: { key: slot.key, label: slot.label || 'Flex', empty: false, pool: slot.pool },
        timeline: tl || null,
      });
    });

    items.sort((a, b) => a.sortTime.localeCompare(b.sortTime));
    return { items, usedIds: used };
  }

  function computeProgress(dayItems, rows) {
    let total = 0, done = 0;
    dayItems.forEach((it) => {
      if (it.flex && it.flex.empty) return; // empty flex does not inflate the goal
      const r = it.row;
      if (!r || r.plannedDate) return;
      if (r.kind === 'daily') { total += r.total; done += r.done; }
      else { total += 1; if (r.complete) done += 1; }
    });
    // Completed timed steps (moved to Done) and day-skips still count for the ring.
    (rows || []).forEach((r) => {
      if (!r.onPlan || r.plannedDate) return;
      if (r.complete) {
        if (r.kind === 'daily') { total += r.total; done += r.total; }
        else { total += 1; done += 1; }
        return;
      }
      if (!isPersistedSkipped(r)) return;
      if (r.kind === 'daily') { total += r.total; done += r.total; }
      else { total += 1; done += 1; }
    });
    return { total, done, pct: total ? Math.round((done / total) * 100) : 100 };
  }

  function computeStreak(hist) {
    const counts = {};
    Object.keys(hist).forEach((k) => (hist[k] || []).forEach((d) => { counts[d] = (counts[d] || 0) + 1; }));
    const active = (d) => (counts[d] || 0) > 0;
    const last7 = [];
    for (let i = 6; i >= 0; i--) { const d = iso(addDays(parseIso(SEL), -i)); last7.push({ d, on: active(d), today: d === SEL }); }
    let streak = 0, grace = 1;
    let cursor = active(SEL) ? 0 : 1;
    for (let i = cursor; i < 400; i++) {
      const d = iso(addDays(parseIso(SEL), -i));
      if (active(d)) streak++;
      else if (grace > 0 && streak > 0) { grace--; }
      else break;
    }
    return { streak, last7 };
  }

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

  const CELEBRATE_MSGS = [
    "Every single thing — done. Your brain earned this.",
    "Full clear. That momentum is yours to keep.",
    "You showed up and finished. That's the whole game.",
    "Done and dusted. Future-you is grateful.",
    "Nailed the day. Go enjoy the dopamine.",
  ];
  function celebrate() {
    if (localStorage.getItem(CELEB_KEY) === SEL) return;
    localStorage.setItem(CELEB_KEY, SEL);
    setXp(getXp() + 25);
    const overlay = document.getElementById('celebrate');
    document.getElementById('celebrate-msg').textContent = CELEBRATE_MSGS[Math.floor(Math.random() * CELEBRATE_MSGS.length)];
    overlay.classList.add('show');
    haptic([0, 50, 40, 80]); beep([523, 659, 784, 1047]); confettiBurst(true);
    renderHero(lastDayItems);
  }
  function closeCelebrate() { document.getElementById('celebrate').classList.remove('show'); }

  const HEADLINES = [
    "Let's make today count", "One tap at a time", "You've got this", "Small wins stack up",
    "Pick one thing. Start there.", "Progress over perfect", "Future-you says thanks", "Tiny steps, real momentum",
  ];

  let lastRows = [];
  let lastDayItems = [];

  function timerBits(tl) {
    if (!tl || tl.resolved) return null;
    const now = new Date();
    const start = parseDt(tl.effective_start);
    const due = parseDt(tl.effective_due);
    if (!start || !due) {
      return { cls: 'wait', text: 'queued', sub: 'Waiting on earlier step' };
    }
    if (now < start) {
      return { cls: 'wait', text: formatCountdown(start - now), sub: 'Starts in' };
    }
    if (now < due) {
      return { cls: '', text: formatCountdown(due - now), sub: (tl.duration_min || '?') + ' min · left' };
    }
    return { cls: 'over', text: formatCountdown(now - due), sub: 'Overdue' };
  }

  function effectiveTimeLabel(it) {
    const tl = it.timeline;
    if (tl && tl.effective_start) {
      const d = parseDt(tl.effective_start);
      if (d) {
        const hh = String(d.getHours()).padStart(2, '0');
        const mm = String(d.getMinutes()).padStart(2, '0');
        return formatTime(hh + ':' + mm);
      }
    }
    return formatTime(it.sortTime);
  }

  function renderHero(dayItems) {
    const prog = computeProgress(dayItems, lastRows);
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

  function taskCardHtml(r, opts) {
    opts = opts || {};
    let cls = 'tk', icon = '○', sub = '', pill = '', timerHtml = '';
    const skippedDay = !!opts.skipped || isPersistedSkipped(r);
    const tl = opts.timeline || timelineByKey()[stateKeyOf(r)] || null;
    const onDayPlan = !!r.onPlan || !!opts.onDayPlan;
    // Day-plan steps (incl. dailies) and bonus recurrings can swipe-skip.
    const swipeable = !r.complete && !skippedDay && (onDayPlan || r.kind === 'recurring');
    if (skippedDay) {
      cls += ' skipped';
      icon = '–';
      sub = 'Skipped today · tap to undo · ' + r.areaName;
    } else if (r.kind === 'daily') {
      cls += ' daily' + (r.complete ? ' done' : '');
      icon = r.complete ? '✓' : '○';
      sub = r.areaName;
      if (r.total > 1) pill = '<span class="tk-pill">' + r.done + '/' + r.total + '</span>';
    } else {
      cls += ' ' + (r.complete ? 'done' : r.status);
      icon = r.complete ? '✓' : (r.status === 'overdue' ? '!' : '○');
      sub = (r.label || '') + ' · ' + r.areaName;
    }
    if (swipeable) {
      cls += ' swipeable';
      sub += onDayPlan ? ' · swipe to skip today' : ' · swipe to skip';
    }
    if (tl && tl.current && !r.complete && !skippedDay) cls += ' current';
    if (tl && tl.locked && !r.complete && !skippedDay) cls += ' locked';
    const bits = (!r.complete && !skippedDay) ? timerBits(tl) : null;
    if (bits) {
      if (bits.cls === 'over') cls += ' timer-overdue';
      timerHtml = '<span class="tk-timer ' + bits.cls + '" data-timer-key="' + esc(stateKeyOf(r)) + '">' + esc(bits.text) + '</span>';
      if (bits.sub) sub = bits.sub + (sub ? ' · ' + sub : '');
    } else if (tl && !r.complete && !skippedDay && tl.duration_min) {
      sub = tl.duration_min + ' min step' + (sub ? ' · ' + sub : '');
    }
    if (r.atWork) cls += ' at-work';
    if (opts.flexLabel) cls += ' flex-slot';
    const timeBit = opts.timeLabel
      ? '<span class="tk-time">' + esc(opts.timeLabel) + '</span>'
      : (r.time ? '<span class="tk-time">' + esc(formatTime(r.time)) + '</span>' : '');
    const flexBit = opts.flexLabel
      ? '<span class="tk-flex-tag">' + esc(opts.flexLabel) + '</span>'
      : '';
    const flexKey = opts.flexKey || (opts.flexLabel && opts.timeline && opts.timeline.flex_key) || '';
    return '<button type="button" class="' + cls + '" data-id="' + esc(r.id) + '"' +
      (swipeable ? ' data-swipe-skip="1"' : '') +
      (flexKey ? ' data-flex-key="' + esc(flexKey) + '"' : '') +
      (skippedDay ? ' data-unskip="1"' : '') + '>' +
      timeBit +
      '<span class="tk-check">' + icon + '</span>' +
      '<span class="tk-body"><span class="tk-name">' + esc(r.name) + flexBit + '</span><span class="tk-sub">' + esc(sub) + '</span></span>' +
      timerHtml + pill + '</button>';
  }

  function emptyFlexHtml(it) {
    return '<div class="tk flex-slot flex-empty">' +
      '<span class="tk-time">' + esc(formatTime(it.sortTime)) + '</span>' +
      '<span class="tk-check">·</span>' +
      '<span class="tk-body"><span class="tk-name">' + esc(it.flex.label) + '</span>' +
      '<span class="tk-sub">Nothing due in this pool — enjoy the buffer</span></span></div>';
  }

  function plannedCardHtml(r) {
    return '<button type="button" class="tk planned" data-unplan="' + esc(planKeyOf(r)) + '">' +
      '<span class="tk-check">📅</span>' +
      '<span class="tk-body"><span class="tk-name">' + esc(r.name) + '</span><span class="tk-sub">Planned for ' + esc(dateLabel(r.plannedDate)) + ' · tap to bring back · ' + esc(r.areaName) + '</span></span>' +
      '</button>';
  }

  function render(justId) {
    const rows = buildRows();
    lastRows = rows;
    const { items, usedIds } = buildDayPlan(rows);
    lastDayItems = items;
    const prog = renderHero(items);

    let html = '<div class="section"><div class="section-title"><h2>Day plan</h2><span class="count">' +
      items.filter((it) => !(it.flex && it.flex.empty)).length + '</span></div>';
    items.forEach((it) => {
      if (it.flex && it.flex.empty) { html += emptyFlexHtml(it); return; }
      html += taskCardHtml(it.row, {
        timeLabel: effectiveTimeLabel(it),
        flexLabel: it.flex ? it.flex.label : null,
        flexKey: it.flex ? it.flex.key : '',
        timeline: it.timeline,
        onDayPlan: true,
      });
    });
    html += '</div>';

    const bonus = rows.filter((r) =>
      !r.complete && !r.plannedDate && r.kind === 'recurring' && !usedIds.has(r.id) &&
      !sessionSkipped.has(r.id) && !isPersistedSkipped(r) &&
      !pinnedToOtherWeekday(r.task) &&
      (r.status === 'overdue' || r.status === 'due' || r.status === 'upcoming')
    ).sort((a, b) => flexPriority(a) - flexPriority(b) || (a.dueIso || '').localeCompare(b.dueIso || ''));
    if (bonus.length) {
      html += '<div class="section"><div class="section-title"><h2>Bonus</h2><span class="count">' + bonus.length + '</span></div>' +
        '<div id="bonus-list" style="display:none">' + bonus.map((r) => taskCardHtml(r)).join('') + '</div>' +
        '<button type="button" class="show-more" id="show-bonus">Show ' + bonus.length + ' bonus</button></div>';
    }

    const planned = rows.filter((r) => r.plannedDate).sort((a, b) => (a.plannedDate || '').localeCompare(b.plannedDate || ''));
    if (planned.length) {
      html += '<div class="section"><div class="section-title"><h2>Planned</h2><span class="count">' + planned.length + '</span></div>' +
        planned.map(plannedCardHtml).join('') + '</div>';
    }

    const skippedRows = rows.filter((r) => isPersistedSkipped(r) && !r.complete);
    if (skippedRows.length) {
      html += '<div class="section"><div class="section-title"><h2>Skipped today</h2><span class="count">' + skippedRows.length + '</span></div>' +
        skippedRows.map((r) => taskCardHtml(r, { skipped: true })).join('') + '</div>';
    }

    const done = rows.filter((r) => r.complete);
    if (done.length) {
      html += '<div class="section done-section"><div class="section-title"><h2>Done today</h2><span class="count">' + done.length + '</span></div>' +
        done.map((r) => taskCardHtml(r)).join('') + '</div>';
    }

    if (!rows.length) html += '<div class="empty">No routines set up yet. Add some in the <a href="/cards">classic view</a>.</div>';
    document.getElementById('sections').innerHTML = html;

    if (justId) {
      const el = document.querySelector('[data-id="' + (window.CSS && CSS.escape ? CSS.escape(justId) : justId) + '"].tk');
      if (el && !reduceMotion) { el.classList.add('pop'); setTimeout(() => el.classList.remove('pop'), 450); }
    }

    if (prog.total > 0 && prog.done >= prog.total) celebrate();
    refreshTimerLabels();
  }

  function refreshTimerLabels() {
    const map = timelineByKey();
    document.querySelectorAll('[data-timer-key]').forEach((el) => {
      const tl = map[el.getAttribute('data-timer-key')];
      const bits = timerBits(tl);
      if (!bits) return;
      el.textContent = bits.text;
      el.classList.toggle('over', bits.cls === 'over');
      el.classList.toggle('wait', bits.cls === 'wait');
    });
  }

  function refreshTimeline() {
    return fetch('/api/routine-day/' + encodeURIComponent(SEL) + '/timeline')
      .then((r) => r.json())
      .then((data) => {
        if (data && data.ok && data.timeline) applyTimeline(data.timeline);
      })
      .catch(() => {});
  }

  function findRow(id) { return lastRows.find((r) => r.id === id); }

  function applyToggle(r) {
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
    if (isPersistedSkipped(r)) {
      unskipDay(r);
      return;
    }
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

    const finishing = !!res.value && (r.onPlan || !!document.querySelector('[data-id="' + (window.CSS && CSS.escape ? CSS.escape(id) : id) + '"]'));
    const el = finishing
      ? document.querySelector('[data-id="' + (window.CSS && CSS.escape ? CSS.escape(id) : id) + '"].tk')
      : null;
    const paint = () => {
      render(finishing ? null : id);
    };
    if (el && finishing && !reduceMotion) {
      el.classList.add('swipe-out');
      setTimeout(paint, 180);
    } else {
      paint();
    }

    fetch('/api/routine-cards/' + encodeURIComponent(WEEK_KEY) + '/' + encodeURIComponent(r.areaKey) + '/set-dot', {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: r.taskIndex, day: DAY_INDEX, dot: res.dot, value: res.value, list: r.listKey || 'tasks' }),
    }).then((resp) => {
      if (!resp.ok) throw new Error('save failed');
      return refreshTimeline().then(() => render(finishing ? null : id));
    }).catch(() => {
      const card = cards[r.areaKey];
      if (card && card.tasks[r.taskIndex] && card.tasks[r.taskIndex].days[DAY_INDEX]) {
        card.tasks[r.taskIndex].days[DAY_INDEX][res.dot] = !res.value;
        setXp(getXp() + (res.value ? -10 : 10));
        render();
      }
    });
  }

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

  function skipForNow(id, flexKey) {
    const r = findRow(id);
    if (!r || r.complete || isPersistedSkipped(r)) return;
    haptic(12);
    const onDayPlan = !!r.onPlan || !!(flexKey) ||
      (timelineByKey()[stateKeyOf(r)] && timelineByKey()[stateKeyOf(r)].kind === 'task');
    if (onDayPlan) {
      const body = {
        area_key: r.areaKey,
        task_name: r.name,
        list: r.listKey || 'tasks',
      };
      // Flex picks skip only that slot; timed routines skip the whole day.
      if (flexKey) body.flex_key = flexKey;
      fetch('/api/routine-day/' + encodeURIComponent(SEL) + '/skip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }).then((resp) => resp.json()).then((data) => {
        if (data && data.ok && data.timeline) applyTimeline(data.timeline);
        else if (data && data.ok) {
          if (flexKey) {
            timeline.flex_skips = timeline.flex_skips || {};
            timeline.flex_skips[flexKey] = timeline.flex_skips[flexKey] || {};
            timeline.flex_skips[flexKey][stateKeyOf(r)] = { at: new Date().toISOString() };
          } else {
            timeline.resolved = timeline.resolved || {};
            timeline.resolved[stateKeyOf(r)] = { status: 'skipped', at: new Date().toISOString() };
          }
        }
        render();
      }).catch(() => {
        sessionSkipped.add(id);
        render();
      });
      return;
    }
    sessionSkipped.add(id);
    render();
  }

  function unskipDay(r) {
    if (!r) return;
    haptic(10);
    fetch('/api/routine-day/' + encodeURIComponent(SEL) + '/skip', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        area_key: r.areaKey,
        task_name: r.name,
        list: r.listKey || 'tasks',
      }),
    }).then((resp) => resp.json()).then((data) => {
      if (data && data.ok && data.timeline) applyTimeline(data.timeline);
      else if (timeline.resolved) delete timeline.resolved[stateKeyOf(r)];
      render();
    }).catch(() => {});
  }

  function bindSwipeSkip(root) {
    // Swipe left = skip. Day-plan steps persist for the day (waterfall);
    // Bonus recurrings stay session-only. Vertical scrolls stay normal.
    let startX = 0, startY = 0, tracking = null, moved = false, lastDx = 0, blockedClick = false;
    const THRESH = 72;

    root.addEventListener('touchstart', (e) => {
      const btn = e.target.closest('[data-swipe-skip]');
      if (!btn || !e.touches || !e.touches[0]) return;
      tracking = btn;
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      moved = false;
      lastDx = 0;
      btn.classList.add('swiping');
    }, { passive: true });

    root.addEventListener('touchmove', (e) => {
      if (!tracking || !e.touches || !e.touches[0]) return;
      const dx = e.touches[0].clientX - startX;
      const dy = e.touches[0].clientY - startY;
      if (!moved && Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > 10) {
        tracking.style.transform = '';
        tracking.classList.remove('swiping', 'swipe-ready');
        tracking = null;
        lastDx = 0;
        return;
      }
      if (Math.abs(dx) > 8) moved = true;
      lastDx = dx;
      if (dx < 0) {
        const x = Math.max(dx, -140);
        tracking.style.transform = 'translateX(' + x + 'px)';
        tracking.classList.toggle('swipe-ready', x <= -THRESH);
      } else {
        tracking.style.transform = '';
        tracking.classList.remove('swipe-ready');
      }
    }, { passive: true });

    function endSwipe() {
      if (!tracking) return;
      const btn = tracking;
      const id = btn.getAttribute('data-id');
      const flexKey = btn.getAttribute('data-flex-key') || '';
      const dx = lastDx;
      tracking = null;
      lastDx = 0;
      if (moved && dx <= -THRESH) {
        blockedClick = true;
        btn.classList.add('swipe-out');
        setTimeout(() => skipForNow(id, flexKey), reduceMotion ? 0 : 180);
      } else {
        btn.style.transform = '';
        btn.classList.remove('swiping', 'swipe-ready');
      }
    }
    root.addEventListener('touchend', endSwipe, { passive: true });
    root.addEventListener('touchcancel', endSwipe, { passive: true });
    root.addEventListener('click', (e) => {
      if (!blockedClick) return;
      blockedClick = false;
      e.preventDefault();
      e.stopPropagation();
    }, true);
  }

  function init() {
    setHeadline();
    refreshPrefButtons();
    render();
    // Keep countdown labels live; re-fetch waterfall every minute so
    // effective times stay aligned after completions on other devices.
    setInterval(refreshTimerLabels, 1000);
    setInterval(() => { refreshTimeline().then(() => render()); }, 60000);

    function handler(e) {
      const btn = e.target.closest('[data-id]');
      if (!btn) return;
      onActivate(btn.getAttribute('data-id'), e.clientX, e.clientY);
    }
    document.getElementById('sections').addEventListener('click', handler);
    document.getElementById('sections').addEventListener('click', (e) => {
      if (e.target.id === 'show-bonus') { const l = document.getElementById('bonus-list'); if (l) l.style.display = 'block'; e.target.style.display = 'none'; return; }
      const un = e.target.closest('[data-unplan]');
      if (un) { clearPlan(un.getAttribute('data-unplan')); render(); }
    });
    bindSwipeSkip(document.getElementById('sections'));

    document.getElementById('celebrate-close').addEventListener('click', closeCelebrate);
    document.getElementById('celebrate').addEventListener('click', (e) => { if (e.target.id === 'celebrate') closeCelebrate(); });

    document.getElementById('toggle-sound').addEventListener('click', () => { soundOn = !soundOn; localStorage.setItem(PREF_SOUND, soundOn ? '1' : '0'); refreshPrefButtons(); if (soundOn) beep([660, 880]); });
    document.getElementById('toggle-haptics').addEventListener('click', () => { hapticsOn = !hapticsOn; localStorage.setItem(PREF_HAPTICS, hapticsOn ? '1' : '0'); refreshPrefButtons(); if (hapticsOn) haptic(15); });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
