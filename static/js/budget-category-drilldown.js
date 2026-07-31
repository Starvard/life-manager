// Budget category drilldown: click a category row to expand transactions inline.
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
      .budget-category-breakdown { margin:.45rem 0 .85rem; border:1px solid rgba(148,163,184,.16); border-radius:1rem; padding:.85rem; background:rgba(15,23,42,.18); cursor:default; }
      .budget-category-breakdown-head { display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; margin-bottom:.75rem; }
      .budget-category-breakdown-title { margin:0; font-size:1rem; line-height:1.25; }
      .budget-category-breakdown-note { margin:.2rem 0 0; color:rgba(148,163,184,.95); font-size:.76rem; line-height:1.35; }
      .budget-category-clear { border:1px solid rgba(148,163,184,.22); border-radius:999px; background:rgba(15,23,42,.2); color:inherit; padding:.35rem .65rem; font-size:.76rem; cursor:pointer; white-space:nowrap; }
      .budget-category-vendor-wrap { display:grid; grid-template-columns:minmax(8rem,12rem) 1fr; gap:.85rem; align-items:center; margin-bottom:.85rem; }
      .budget-category-pie { width:9.5rem; height:9.5rem; border-radius:999px; border:1px solid rgba(148,163,184,.2); background:rgba(255,255,255,.04); box-shadow:inset 0 0 0 1.45rem rgba(15,23,42,.74); }
      .budget-category-vendors { display:grid; gap:.35rem; }
      .budget-category-vendor { display:flex; align-items:center; justify-content:space-between; gap:.6rem; font-size:.78rem; color:rgba(226,232,240,.94); }
      .budget-category-vendor-left { display:flex; align-items:center; min-width:0; gap:.42rem; }
      .budget-category-dot { flex:0 0 .58rem; width:.58rem; height:.58rem; border-radius:999px; box-shadow:0 0 0 2px rgba(255,255,255,.05); }
      .budget-category-vendor-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .budget-category-vendor-amt { color:rgba(248,250,252,.96); font-weight:800; white-space:nowrap; }
      .budget-category-tx-list { display:grid; gap:.45rem; max-height:24rem; overflow:auto; padding-right:.2rem; }
      .budget-category-tx { display:grid; grid-template-columns:5.25rem 1fr auto; gap:.65rem; align-items:center; border:1px solid rgba(148,163,184,.12); border-left-width:.35rem; border-radius:.75rem; padding:.55rem .65rem; background:rgba(255,255,255,.025); }
      .budget-category-tx-date { color:rgba(148,163,184,.95); font-size:.74rem; }
      .budget-category-tx-desc { min-width:0; }
      .budget-category-tx-desc strong { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:.86rem; }
      .budget-category-tx-desc small { display:block; color:rgba(148,163,184,.92); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; margin-top:.08rem; }
      .budget-category-tx-amount { font-weight:800; font-size:.86rem; text-align:right; }
      .budget-category-empty { color:rgba(148,163,184,.95); font-size:.82rem; margin:.3rem 0 0; }
      @media (max-width:760px){ .budget-category-vendor-wrap{grid-template-columns:1fr}.budget-category-pie{width:8.5rem;height:8.5rem;margin:auto}.budget-category-tx{grid-template-columns:4.4rem 1fr;}.budget-category-tx-amount{grid-column:2;text-align:left;} }
    `;
    document.head.appendChild(style);
  }

  function money(n) {
    const v = Number(n || 0);
    const abs = Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return (v < 0 ? '-$' : '$') + abs;
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' })[c]; });
  }

  function budgetData() {
    const root = document.querySelector('[x-data^="budgetPage"]');
    if (!root || !window.Alpine) return null;
    try { return window.Alpine.$data(root); } catch (_) { return null; }
  }

  function displayCat(data, tx) {
    if (data && typeof data.displayCat === 'function') return data.displayCat(tx);
    return tx.category_override || tx.category_display || tx.category || 'Shopping';
  }

  function statusRows(data) {
    return Array.isArray(data && data.report && data.report.category_status) ? data.report.category_status : [];
  }

  function txnsForCategory(data, cat) {
    const txns = Array.isArray(data && data.transactions) ? data.transactions : [];
    return txns
      .filter(function (tx) { return !tx.is_duplicate && displayCat(data, tx) === cat; })
      .sort(function (a, b) { return String(b.date || '').localeCompare(String(a.date || '')); });
  }

  function hashString(s) {
    let h = 0;
    const str = String(s || 'Other');
    for (let i = 0; i < str.length; i++) h = ((h << 5) - h + str.charCodeAt(i)) | 0;
    return Math.abs(h);
  }

  function colorForVendor(vendor) {
    const h = hashString(vendor) % 360;
    return 'hsl(' + h + ', 72%, 68%)';
  }

  function vendorName(tx) {
    let raw = String(tx.merchant_name || tx.name || tx.description || 'Other').trim();
    raw = raw.replace(/\s+/g, ' ').replace(/[0-9]{2,}/g, '').replace(/[*#]/g, ' ').trim();
    const words = raw.split(' ').filter(Boolean);
    if (words.length > 4) raw = words.slice(0, 4).join(' ');
    return raw || 'Other';
  }

  function vendorTotals(txns) {
    const map = new Map();
    txns.forEach(function (tx) {
      const vendor = vendorName(tx);
      const total = Math.abs(Number(tx.amount || 0));
      map.set(vendor, (map.get(vendor) || 0) + total);
    });
    return Array.from(map.entries()).map(function (entry) {
      return { vendor: entry[0], total: entry[1], color: colorForVendor(entry[0]) };
    }).sort(function (a, b) { return b.total - a.total; });
  }

  function pieGradient(vendors) {
    const total = vendors.reduce(function (s, v) { return s + v.total; }, 0);
    if (!(total > 0)) return 'rgba(255,255,255,.04)';
    let start = 0;
    const pieces = vendors.map(function (v) {
      const end = start + (v.total / total) * 100;
      const piece = v.color + ' ' + start.toFixed(2) + '% ' + end.toFixed(2) + '%';
      start = end;
      return piece;
    });
    return 'conic-gradient(' + pieces.join(', ') + ')';
  }

  function renderBreakdown(data, afterRow) {
    document.querySelectorAll('.budget-category-breakdown').forEach(function (el) { el.remove(); });
    document.querySelectorAll('.budget-status-row.budget-category-selected').forEach(function (el) { el.classList.remove('budget-category-selected'); });
    if (!selectedCategory || !data || !afterRow) return;
    afterRow.classList.add('budget-category-selected');

    const txns = txnsForCategory(data, selectedCategory);
    const vendors = vendorTotals(txns).slice(0, 8);
    const vendorList = vendors.map(function (v) {
      return '<div class="budget-category-vendor">'
        + '<div class="budget-category-vendor-left"><span class="budget-category-dot" style="background:' + esc(v.color) + '"></span><span class="budget-category-vendor-name">' + esc(v.vendor) + '</span></div>'
        + '<span class="budget-category-vendor-amt">' + esc(money(v.total)) + '</span>'
        + '</div>';
    }).join('');

    const recent = txns.slice(0, 40).map(function (tx) {
      const amount = Number(tx.amount || 0);
      const vendor = vendorName(tx);
      const color = colorForVendor(vendor);
      return '<div class="budget-category-tx" style="border-left-color:' + esc(color) + '">'
        + '<div class="budget-category-tx-date">' + esc(tx.date || '') + '</div>'
        + '<div class="budget-category-tx-desc"><strong>' + esc(tx.description || vendor || 'Transaction') + '</strong><small>' + esc(vendor + (tx.account ? ' · ' + tx.account : '')) + '</small></div>'
        + '<div class="budget-category-tx-amount">' + esc(money(amount)) + '</div>'
        + '</div>';
    }).join('');

    const panel = document.createElement('div');
    panel.className = 'budget-category-breakdown';
    panel.addEventListener('click', function (event) { event.stopPropagation(); });
    panel.innerHTML = [
      '<div class="budget-category-breakdown-head">',
      '  <div><h3 class="budget-category-breakdown-title">' + esc(selectedCategory) + '</h3><p class="budget-category-breakdown-note">Transactions in this category, grouped visually by vendor.</p></div>',
      '  <button type="button" class="budget-category-clear">Clear</button>',
      '</div>',
      txns.length ? '<div class="budget-category-vendor-wrap"><div class="budget-category-pie" style="background:' + esc(pieGradient(vendors)) + '"></div><div class="budget-category-vendors">' + vendorList + '</div></div>' : '',
      txns.length ? '<div class="budget-category-tx-list">' + recent + '</div>' : '<p class="budget-category-empty">No transactions found in this category for the selected month.</p>'
    ].join('');

    panel.querySelector('.budget-category-clear').addEventListener('click', function (event) {
      event.preventDefault();
      event.stopPropagation();
      selectedCategory = null;
      renderBreakdown(data, null);
    });

    afterRow.insertAdjacentElement('afterend', panel);
  }

  function wireRows(data) {
    const rows = Array.from(document.querySelectorAll('.budget-status-row'));
    const stats = statusRows(data);
    rows.forEach(function (el, i) {
      const cat = stats[i] && stats[i].category;
      if (!cat || el.__budgetCategoryDrilldownCat === cat) return;
      el.__budgetCategoryDrilldownCat = cat;
      el.setAttribute('role', 'button');
      el.setAttribute('tabindex', '0');
      el.setAttribute('title', 'Show ' + cat + ' transactions');
      const choose = function () {
        selectedCategory = selectedCategory === cat ? null : cat;
        renderBreakdown(data, selectedCategory ? el : null);
      };
      el.addEventListener('click', choose);
      el.addEventListener('keydown', function (event) {
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
    if (selectedCategory) {
      const stats = statusRows(data);
      const idx = stats.findIndex(function (r) { return r.category === selectedCategory; });
      const row = idx >= 0 ? document.querySelectorAll('.budget-status-row')[idx] : null;
      renderBreakdown(data, row);
    }
  }

  document.addEventListener('alpine:initialized', function () { setTimeout(refresh, 100); });
  window.addEventListener('load', function () { setTimeout(refresh, 350); });
  document.addEventListener('click', function () { setTimeout(refresh, 240); });
})();
