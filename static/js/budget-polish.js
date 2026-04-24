// Budget page polish layer: consolidated KPIs + calmer budget severity.
(function () {
  const INCOME_HINTS = ['dyndrite', 'income', 'jenna sales', 'from savings'];
  const CARD_HINT = 'credit card';
  const STATIC_CASH_HINTS = [
    'mortgage', 'electricity', 'water', 'natural gas', 'internet', 'phone',
    'youtube', 'netflix', 'google one', 'chat gpt', 'swim', 'reoccuring', 'recurring',
    'med', 'dog', 'massage'
  ];

  function money(n) {
    const v = Number(n || 0);
    const abs = Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return (v < 0 ? '-$' : '$') + abs;
  }

  function signedMoney(n) {
    const v = Number(n || 0);
    if (Math.abs(v) < 0.005) return '$0.00';
    return (v > 0 ? '+' : '-') + money(Math.abs(v));
  }

  function val(obj, path, fallback) {
    try {
      const got = path.split('.').reduce((a, k) => (a == null ? undefined : a[k]), obj);
      return got == null ? fallback : got;
    } catch (_) {
      return fallback;
    }
  }

  function budgetData() {
    const root = document.querySelector('[x-data^="budgetPage"]');
    if (!root || !window.Alpine) return null;
    try { return window.Alpine.$data(root); } catch (_) { return null; }
  }

  function lower(s) { return String(s || '').toLowerCase(); }
  function isIncomeCat(cat) { const c = lower(cat); return INCOME_HINTS.some((h) => c.includes(h)); }
  function isCardCat(cat) { return lower(cat).includes(CARD_HINT); }
  function isStaticCashCat(cat) { const c = lower(cat); return STATIC_CASH_HINTS.some((h) => c.includes(h)); }

  function limits(data) { return data && data.budgetLimits && typeof data.budgetLimits === 'object' ? data.budgetLimits : {}; }

  function sumLimits(data, pred) {
    return Object.entries(limits(data)).reduce((sum, pair) => {
      const cat = pair[0];
      const raw = Number(pair[1] || 0);
      if (!(raw > 0) || !pred(cat)) return sum;
      return sum + raw;
    }, 0);
  }

  function projectedIncome(data) {
    const fromLimits = sumLimits(data, isIncomeCat);
    const fromReport = Number(val(data.report, 'projected.income', 0) || 0);
    return fromLimits > 0 ? fromLimits : fromReport;
  }

  function projectedSpend(data) {
    const fromLimits = sumLimits(data, (cat) => !isIncomeCat(cat) && !isCardCat(cat));
    const fromReport = Number(val(data.report, 'projected.expenses', 0) || 0);
    return fromLimits > 0 ? fromLimits : fromReport;
  }

  function actualForCategory(data, pred) {
    const rows = Array.isArray(data.report && data.report.category_status) ? data.report.category_status : [];
    return rows.reduce((sum, row) => {
      if (!pred(row.category)) return sum;
      return sum + Number(row.spent || 0);
    }, 0);
  }

  function metricCard(label, projectedLabel, projectedValue, actualLabel, actualValue, sub, tone, actualClass) {
    const el = document.createElement('div');
    el.className = 'budget-polish-card budget-polish-kpi ' + (tone || '');
    el.innerHTML = [
      '<p class="budget-polish-label"></p>',
      '<div class="budget-polish-pair">',
      '  <div><span class="budget-polish-mini"></span><strong class="budget-polish-value"></strong></div>',
      '  <div><span class="budget-polish-mini"></span><strong class="budget-polish-value"></strong></div>',
      '</div>',
      '<p class="budget-polish-sub"></p>'
    ].join('');
    el.querySelector('.budget-polish-label').textContent = label;
    const minis = el.querySelectorAll('.budget-polish-mini');
    const vals = el.querySelectorAll('.budget-polish-value');
    minis[0].textContent = projectedLabel;
    minis[1].textContent = actualLabel;
    vals[0].textContent = projectedValue;
    vals[1].textContent = actualValue;
    if (actualClass) vals[1].classList.add(actualClass);
    el.querySelector('.budget-polish-sub').textContent = sub || '';
    return el;
  }

  function singleCard(label, value, sub, tone) {
    const el = document.createElement('div');
    el.className = 'budget-polish-card ' + (tone || '');
    el.innerHTML = '<p class="budget-polish-label"></p><p class="budget-polish-value"></p><p class="budget-polish-sub"></p>';
    el.children[0].textContent = label;
    el.children[1].textContent = value;
    el.children[2].textContent = sub || '';
    return el;
  }

  function buildDashboard(data) {
    const old = document.querySelector('.budget-polish-dashboard');
    if (old) old.remove();
    const anchor = document.querySelector('.budget-at-a-glance');
    if (!anchor || !data) return;

    const pIncome = projectedIncome(data);
    const aIncome = Number(data.lifestyleIncome ? data.lifestyleIncome() : val(data.report, 'income_salary_actual', 0));
    const pSpend = projectedSpend(data);
    const aSpend = Number(data.lifestyleSpentAbs ? data.lifestyleSpentAbs() : Math.abs(val(data.report, 'lifestyle_expenses', 0)));
    const pSavings = pIncome - pSpend;
    const aSavings = aIncome - aSpend;
    const lastIncome = Number(data.priorMonthSalaryIncome ? data.priorMonthSalaryIncome() : val(data.report, 'card_compare.prior_salary_income', 0));
    const cardPayoffs = Number(data.cardPayoffTotal ? data.cardPayoffTotal() : val(data.report, 'card_payoff_total', 0));
    const staticCashBudget = sumLimits(data, (cat) => isStaticCashCat(cat) && !isCardCat(cat) && !isIncomeCat(cat));
    const staticCashActual = actualForCategory(data, (cat) => isStaticCashCat(cat) && !isCardCat(cat) && !isIncomeCat(cat));
    const cashPressureProjected = cardPayoffs + staticCashBudget;
    const cashPressureActual = cardPayoffs + staticCashActual;
    const cashPressureBase = lastIncome > 0 ? lastIncome : pIncome;
    const cashPressurePct = cashPressureBase > 0 ? Math.round((cashPressureActual / cashPressureBase) * 100) : null;

    const wrap = document.createElement('div');
    wrap.className = 'budget-polish-dashboard card budget-polish-hero';
    const header = document.createElement('div');
    header.className = 'budget-polish-header';
    header.innerHTML = '<div><p class="budget-polish-eyebrow">Monthly budget</p><h2 class="budget-polish-title">Family cash plan</h2></div><p class="budget-polish-note">The top row is now KPI-style: income, spending, and savings each show projected vs actual. The cash-pressure card compares last month’s income against this month’s card payoffs plus non-card recurring cash bills.</p>';

    const grid = document.createElement('div');
    grid.className = 'budget-polish-grid budget-polish-grid-compact';
    grid.appendChild(metricCard('Income', 'Projected', money(pIncome), 'Actual', money(aIncome), 'Money expected vs received this month', 'soft-green'));
    grid.appendChild(metricCard('Spending', 'Projected', money(pSpend), 'Actual', money(aSpend), 'Budget limits vs purchases / cash outflow', 'soft-blue'));
    grid.appendChild(metricCard('Savings', 'Projected', signedMoney(pSavings), 'Actual', signedMoney(aSavings), 'Income minus spending', aSavings >= 0 ? 'soft-purple' : 'soft-amber', aSavings >= 0 ? 'pos' : 'neg'));
    grid.appendChild(metricCard('Cash pressure', 'Last income', money(lastIncome), 'Due this month', money(cashPressureActual), cashPressurePct == null ? 'Card payoffs + recurring cash bills' : ('Card payoffs + recurring cash bills · ' + cashPressurePct + '% of last month income'), cashPressurePct != null && cashPressurePct > 100 ? 'soft-amber' : 'soft-purple'));

    const actions = document.createElement('div');
    actions.className = 'budget-polish-actions';
    actions.innerHTML = '<span class="budget-polish-chip">Static cash estimate: ' + money(staticCashBudget) + ' budgeted / ' + money(staticCashActual) + ' actual</span><span class="budget-polish-chip">Card payoffs: ' + money(cardPayoffs) + '</span>';
    wrap.appendChild(header);
    wrap.appendChild(grid);
    wrap.appendChild(actions);
    anchor.parentNode.insertBefore(wrap, anchor);
  }

  function severity(row) {
    const limit = Number(row.limit || 0);
    const spent = Number(row.spent || 0);
    if (!(limit > 0)) return 'none';
    const over = spent - limit;
    const pct = limit > 0 ? spent / limit : 0;
    if (over <= 0 && pct >= 0.85) return 'near';
    if (over <= 0) return 'ok';
    if (over <= 100 || pct <= 1.10) return 'slight';
    if (pct <= 1.25) return 'warn';
    return 'danger';
  }

  function applySeverity(data) {
    if (!data || !Array.isArray(data.report && data.report.category_status)) return;
    const rows = Array.from(document.querySelectorAll('.budget-status-row'));
    data.report.category_status.forEach((row, i) => {
      const el = rows[i];
      if (!el) return;
      const sev = severity(row);
      el.classList.remove('severity-near', 'severity-slight', 'severity-warn', 'severity-danger');
      if (sev !== 'ok' && sev !== 'none') el.classList.add('severity-' + sev);
      const fill = el.querySelector('.budget-status-bar-fill');
      if (fill) {
        fill.classList.remove('severity-near', 'severity-slight', 'severity-warn', 'severity-danger');
        if (sev !== 'ok' && sev !== 'none') fill.classList.add('severity-' + sev);
      }
    });
  }

  function refresh() {
    if (!location.pathname.startsWith('/budget')) return;
    document.body.classList.add('budget-polish-active');
    const data = budgetData();
    if (!data) return;
    buildDashboard(data);
    setTimeout(() => applySeverity(data), 80);
  }

  document.addEventListener('alpine:initialized', refresh);
  window.addEventListener('load', () => setTimeout(refresh, 250));
  document.addEventListener('click', () => setTimeout(refresh, 150));
})();

// Routine card display patch: completion only fills the clicked dot.
(function () {
  function schedInt(sched, dayIdx) {
    if (typeof _schedInt === 'function') return _schedInt(sched, dayIdx);
    const n = Number((sched || [])[dayIdx]);
    return Number.isFinite(n) ? Math.max(0, Math.floor(n)) : 0;
  }
  function schedCount(sched) {
    if (typeof _taskScheduledSlotCount === 'function') return _taskScheduledSlotCount(sched);
    let n = 0;
    for (let d = 0; d < 7; d++) n += schedInt(sched, d);
    return n;
  }
  function fillCount(days) {
    if (typeof _taskTotalFillCount === 'function') return _taskTotalFillCount(days || []);
    let n = 0;
    for (const row of (days || []).slice(0, 7)) for (const val of (row || [])) if (val) n += 1;
    return n;
  }
  function slotIndex(sched, dayIdx, dotIdx) {
    if (typeof _schedSlotIndex === 'function') return _schedSlotIndex(sched, dayIdx, dotIdx);
    let k = 0;
    for (let d = 0; d < dayIdx; d++) k += schedInt(sched, d);
    return k + dotIdx;
  }
  function fixedDotClass(task, dayIdx, dotIdx) {
    const sched = task.scheduled || [];
    const isScheduled = dotIdx < schedInt(sched, dayIdx);
    const row = task.days[dayIdx] || [];
    const filled = !!row[dotIdx];
    const cls = {};
    if (filled) {
      cls.filled = true;
      if (!isScheduled) cls.unscheduled = true;
      return cls;
    }
    const nSched = schedCount(sched);
    const nFill = fillCount(task.days || []);
    const pool = Math.min(nSched, nFill);
    const freq = Number(task.freq || 0);
    if (freq > 0 && freq < 1 && nSched > 0 && nFill === 0) {
      cls['overdue-1'] = true;
      return cls;
    }
    const todayIdx = this.todayIdx;
    if (todayIdx > 6 && isScheduled) {
      cls['overdue-4'] = true;
      return cls;
    }
    const slotK = isScheduled ? slotIndex(sched, dayIdx, dotIdx) : -1;
    if (todayIdx >= 0 && todayIdx <= 6 && dayIdx <= todayIdx && isScheduled && slotK >= pool) {
      const lev = typeof this._overdueStreakLevel === 'function' ? this._overdueStreakLevel(task) : 1;
      if (lev > 0) {
        cls['overdue-' + lev] = true;
        return cls;
      }
    }
    if (!isScheduled) cls.unscheduled = true;
    return cls;
  }
  function patchAllRoutineCards() {
    if (!window.Alpine) return;
    document.querySelectorAll('[x-data]').forEach((el) => {
      let data;
      try { data = window.Alpine.$data(el); } catch (_) { return; }
      if (!data || !data.card || typeof data.dotClass !== 'function') return;
      if (data.__routineCardDisplayFixApplied) return;
      data.dotClass = fixedDotClass;
      data.__routineCardDisplayFixApplied = true;
    });
  }
  document.addEventListener('alpine:initialized', () => setTimeout(patchAllRoutineCards, 0));
  document.addEventListener('click', () => setTimeout(patchAllRoutineCards, 0));
  window.addEventListener('load', () => setTimeout(patchAllRoutineCards, 50));
})();
