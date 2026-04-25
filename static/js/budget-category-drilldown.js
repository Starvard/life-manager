// Budget category drilldown: click a category row to show the spending breakdown in the main dashboard.
(function () {
  let selectedCategory = null;

  function injectStyles() {
    if (document.getElementById('budget-category-drilldown-styles')) return;
    const style = document.createElement('style');
    style.id = 'budget-category-drilldown-styles';
    style.textContent = `
      body.budget-polish-active .budget-status-row { cursor:pointer; transition: border-color .15s ease, background .15s ease, transform .15s ease; }
      body.budget-polish-active .budget-status-row:hover { border-color:rgba(191,219,254,.45); background:rgba(191,219,254,.07); transform:translateY(-1px); }
      body.budget-polish-active .budget-status-row.budget-category-selected { border-color:rgba(125,211,252,.65); background:rgba(125,211,252,.1); }
      .budget-category-breakdown { margin-top:1rem; border:1px solid rgba(148,163,184,.16); border-radius:1rem; padding:.9rem; background:rgba(15,23,42,.18); }
      .budget-category-breakdown-head { display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; margin-bottom:.75rem; }
      .budget-category-breakdown-title { margin:0; font-size:1rem; line-height:1.25; }
      .budget-category-breakdown-note { margin:.2rem 0 0; color:rgba(148,163,184,.95); font-size:.76rem; line-height:1.35; }
      .budget-category-clear { border:1px solid rgba(148,163,184,.22); border-radius:999px; background:rgba(15,23,42,.2); color:inherit; padding:.35rem .65rem; font-size:.76rem; cursor:pointer; white-space:nowrap; }
      .budget-category-metrics { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.6rem; margin-bottom:.85rem; }
      .budget-category-metric { border:1px solid rgba(148,163,184,.14); border-radius:.85rem; padding:.65rem; background:rgba(255,255,255,.035); }
      .budget-category-metric span { display:block; color:rgba(148,163,184,.92); font-size:.68rem; text-transform:uppercase; letter-spacing:.05em; font-weight:800; margin-bottom:.18rem; }
      .budget-category-metric strong { display:block; font-size:1rem; color:rgba(248,250,252,.96); }
      .budget-category-tx-list { display:grid; gap:.45rem; max-height:22rem; overflow:auto; padding-right:.2rem; }
      .budget-category-tx { display:grid; grid-template-columns:5.25rem 1fr auto; gap:.65rem; align-items:center; border:1px solid rgba(148,163,184,.12); border-radius:.75rem; padding:.55rem .65rem; background:rgba(255,255,255,.025); }
      .budget-category-tx-date { color:rgba(148,163,184,.95); font-size:.74rem; }
      .budget-category-tx-desc { min-width:0; }
      .budget-category-tx-desc strong { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:.86rem; }
      .budget-category-tx-desc small { display:block; color:rgba(148,163,184,.92); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; margin-top:.08rem; }
      .budget-category-tx-amount { font-weight:800; font-size:.86rem; text-align:right; }
      .budget-category-empty { color:rgba(148,163,184,.95); font-size:.82rem; margin:.3rem 0 0; }
      @media (max-width:760px){ .budget-category-metrics{grid-template-columns:repeat(2,minmax(0,1fr));}.budget-category-tx{grid-template-columns:4.4rem 1fr;}.budget-category-tx-amount{grid-column:2;text-align:left;} }
    `;
    document.head.appendChild(style);
  }

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

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
  }

  function budgetData() {
    const root = document.querySelector('[x-data^="budgetPage"]');
    if (!root || !window.Alpine) return null;
    try { return window.Alpine.$data(root); } catch (_) { return null; }
  }

  function displayCat(data, tx) {
    if (data && typeof data.displayCat === 'function') return data.displayCat(tx);
    return tx.category_override || tx.category_display || tx.category || '🏬 Shopping';
  }

  function statusRows(data) {
    return Array.isArray(data && data.report && data.report.category_status) ? data.report.category_status : [];
  }

  function rowForCategory(data, cat) {
    return statusRows(data).find((r) => r.category === cat) || null;
  }

  function txnsForCategory(data, cat) {
    const txns = Array.isArray(data && data.transactions) ? data.transactions : [];
    return txns
      .filter((tx) => !tx.is_duplicate && displayCat(data, tx) === cat)
      .sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')));
  }

  function avgForCategory(data, cat) {
    const avg = data && data.report && data.report.category_average_spend ? data.report.category_average_spend[cat] : null;
    return avg && Number(avg.average) ? avg : null;
  }

  function metric(label, value) {
    return '<div class="budget-category-metric"><span>' + esc(label) + '</span><strong>' + esc(value) + '</strong></div>';
  }

  function renderBreakdown(data) {
    document.querySelectorAll('.budget-category-breakdown').forEach((el) => el.remove());
    document.querySelectorAll('.budget-status-row.budget-category-selected').forEach((el) => el.classList.remove('budget-category-selected'));

    if (!selectedCategory || !data) return;

    const dashboard = document.querySelector('.budget-polish-dashboard');
    if (!dashboard) return;

    const row = rowForCategory(data, selectedCategory);
    const txns = txnsForCategory(data, selectedCategory);
    const outflow = txns.reduce((sum, tx) => sum + (Number(tx.amount) < 0 ? Math.abs(Number(tx.amount)) : 0), 0);
    const inflow = txns.reduce((sum, tx) => sum + (Number(tx.amount) > 0 ? Number(tx.amount) : 0), 0);
    const rowSpent = row ? Number(row.spent || 0) : outflow;
    const limit = row ? Number(row.limit || 0) : Number((data.budgetLimits || {})[selectedCategory] || 0);
    const remaining = limit > 0 ? limit - rowSpent : null;
    const avg = avgForCategory(data, selectedCategory);

    const matches = statusRows(data).map((r) => r.category);
    const idx = matches.indexOf(selectedCategory);
    const domRow = idx >= 0 ? document.querySelectorAll('.budget-status-row')[idx] : null;
    if (domRow) domRow.classList.add('budget-category-selected');

    const recent = txns.slice(0, 30).map((tx) => {
      const amount = Number(tx.amount || 0);
      return '<div class="budget-category-tx">'
        + '<div class="budget-category-tx-date">' + esc(tx.date || '') + '</div>'
        + '<div class="budget-category-tx-desc"><strong>' + esc(tx.description || 'Transaction') + '</strong><small>' + esc(tx.account || '') + '</small></div>'
        + '<div class="budget-category-tx-amount">' + esc(money(amount)) + '</div>'
        + '</div>';
    }).join('');

    const panel = document.createElement('div');
    panel.className = 'budget-category-breakdown';
    panel.innerHTML = [
      '<div class="budget-category-breakdown-head">',
      '  <div><h3 class="budget-category-breakdown-title">' + esc(selectedCategory) + '</h3><p class="budget-category-breakdown-note">Clicked category breakdown for this month. Showing the spending total, budget context, and the transactions making it up.</p></div>',
      '  <button type="button" class="budget-category-clear">Clear</button>',
      '</div>',
      '<div class="budget-category-metrics">',
      metric('Spent', money(rowSpent || outflow)),
      metric('Budget', limit > 0 ? money(limit) : 'No limit'),
      metric('Remaining', remaining == null ? '—' : signedMoney(remaining)),
      metric('Transactions', String(txns.length)),
      metric('Outflow', money(outflow)),
      metric('Inflow', money(inflow)),
      metric('Average / mo', avg ? money(avg.average) : '—'),
      metric('Avg months', avg ? String(avg.months || 0) : '—'),
      '</div>',
      txns.length ? '<div class="budget-category-tx-list">' + recent + '</div>' : '<p class="budget-category-empty">No transactions found in this category for the selected month.</p>'
    ].join('');

    panel.querySelector('.budget-category-clear').addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      selectedCategory = null;
      renderBreakdown(data);
    });

    dashboard.appendChild(panel);
  }

  function wireRows(data) {
    const rows = Array.from(document.querySelectorAll('.budget-status-row'));
    const stats = statusRows(data);
    rows.forEach((el, i) => {
      const cat = stats[i] && stats[i].category;
      if (!cat || el.__budgetCategoryDrilldownCat === cat) return;
      el.__budgetCategoryDrilldownCat = cat;
      el.setAttribute('role', 'button');
      el.setAttribute('tabindex', '0');
      el.setAttribute('title', 'Show ' + cat + ' breakdown above');
      const choose = () => {
        selectedCategory = selectedCategory === cat ? null : cat;
        renderBreakdown(data);
        const panel = document.querySelector('.budget-category-breakdown');
        if (panel && typeof panel.scrollIntoView === 'function') panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      };
      el.addEventListener('click', choose);
      el.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          choose();
        }
      });
    });
  }

  function refresh() {
    if (!location.pathname.startsWith('/budget')) return;
    injectStyles();
    const data = budgetData();
    if (!data) return;
    wireRows(data);
    renderBreakdown(data);
  }

  document.addEventListener('alpine:initialized', () => setTimeout(refresh, 100));
  window.addEventListener('load', () => setTimeout(refresh, 350));
  document.addEventListener('click', () => setTimeout(refresh, 240));
})();
