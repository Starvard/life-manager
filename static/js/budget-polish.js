// Budget page polish layer: dashboard summary + calmer budget severity.
(function () {
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
      return path.split('.').reduce((a, k) => (a == null ? undefined : a[k]), obj) ?? fallback;
    } catch (_) {
      return fallback;
    }
  }

  function budgetData() {
    const root = document.querySelector('[x-data^="budgetPage"]');
    if (!root || !window.Alpine) return null;
    try { return window.Alpine.$data(root); } catch (_) { return null; }
  }

  function card(label, value, sub, tone) {
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

    const projectedIncome = Number(data.projectedIncome ? data.projectedIncome() : val(data.report, 'projected.income', 0));
    const actualIncome = Number(data.lifestyleIncome ? data.lifestyleIncome() : val(data.report, 'income_salary_actual', 0));
    const projectedSpend = Number(data.projectedSpend ? data.projectedSpend() : val(data.report, 'projected.expenses', 0));
    const actualSpend = Number(data.lifestyleSpentAbs ? data.lifestyleSpentAbs() : Math.abs(val(data.report, 'lifestyle_expenses', 0)));
    const projectedSavings = projectedIncome - projectedSpend;
    const actualSavings = actualIncome - actualSpend;
    const lastIncome = Number(data.priorMonthSalaryIncome ? data.priorMonthSalaryIncome() : val(data.report, 'card_compare.prior_salary_income', 0));
    const cardPayoffs = Number(data.cardPayoffTotal ? data.cardPayoffTotal() : val(data.report, 'card_payoff_total', 0));
    const cardPct = data.cardPayoffVsPriorSalary ? data.cardPayoffVsPriorSalary() : val(data.report, 'card_compare.card_payoff_vs_salary_pct', null);

    const wrap = document.createElement('div');
    wrap.className = 'budget-polish-dashboard card budget-polish-hero';
    const header = document.createElement('div');
    header.className = 'budget-polish-header';
    header.innerHTML = '<div><p class="budget-polish-eyebrow">Monthly budget</p><h2 class="budget-polish-title">Projected vs actual</h2></div><p class="budget-polish-note">Income, spending, and savings use the same Budget rows. Credit card payoffs are shown separately because this month usually clears last month’s card spending.</p>';
    const grid = document.createElement('div');
    grid.className = 'budget-polish-grid';
    grid.appendChild(card('Projected income', money(projectedIncome), 'Income targets from Budgets', 'soft-green'));
    grid.appendChild(card('Actual income', money(actualIncome), 'Received this month', 'soft-green'));
    grid.appendChild(card('Projected spending', money(projectedSpend), 'Budgeted category spend', 'soft-blue'));
    grid.appendChild(card('Actual spending', money(actualSpend), 'Purchases / lifestyle outflow', 'soft-blue'));
    grid.appendChild(card('Projected savings', signedMoney(projectedSavings), 'Projected income minus projected spend', 'soft-purple'));
    grid.appendChild(card('Actual savings', signedMoney(actualSavings), 'Actual income minus actual spend', actualSavings >= 0 ? 'soft-purple' : 'soft-amber'));
    grid.appendChild(card('Last month income', money(lastIncome), 'Context for card payoff timing', 'soft-green'));
    grid.appendChild(card('This month card payments', money(cardPayoffs), cardPct == null ? 'Paying down prior card spend' : (Math.round(cardPct) + '% of last month income'), 'soft-amber'));
    const actions = document.createElement('div');
    actions.className = 'budget-polish-actions';
    actions.innerHTML = '<span class="budget-polish-chip">Green = comfortable</span><span class="budget-polish-chip">Purple = slightly over / close</span><span class="budget-polish-chip">Warm colors = worth attention</span>';
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
