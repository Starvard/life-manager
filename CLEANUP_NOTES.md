# Cleanup & Performance Notes

This file records the performance overhaul and the dead code that was removed,
so there is a paper trail of "what that file used to be" without keeping the
bloat around. See the PR for the full diff.

## Why the app felt "very very slow"

Profiling the front end (not the Python — pages render server-side in <60 ms)
turned up three compounding problems, all in how assets were loaded:

1. **No static caching.** Werkzeug's default for static files is
   `Cache-Control: no-cache`, which forces the browser to *revalidate every
   CSS/JS file on every page navigation*. With ~14 static files per page and a
   single-worker (4-thread) server on a 256 MB box, every tap on a nav tab
   triggered a dozen-plus blocking round-trips before the page felt ready.
   - **Fix:** `app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 365 days`. Every static
     URL already carries `?v=<cache_bust>` (the process start time, which
     changes on each deploy/restart), so a long max-age is safe — a new deploy
     gets a new query string and busts the cache automatically. After the first
     load, static assets now come straight from the browser cache (0 requests).

2. **Render-blocking Chart.js on every page.** `base.html` loaded
   `chart.js@4` (~250 KB) as a synchronous `<head>` script on *every* page,
   even though the only page that draws a chart is the dashboard — which loaded
   its **own** second copy of Chart.js anyway.
   - **Fix:** removed Chart.js from `base.html` entirely; the dashboard keeps
     its single copy and it is now `defer`-loaded.

3. **Every page downloaded every patch script.** `base.html` loaded ~10
   feature-specific/one-off scripts globally (budget polish, recipe menu fills,
   grocery sort, routine fixes…). Most pages used none of them.
   - **Fix:** introduced a `{% block body_scripts %}` in `base.html`. Now each
     page loads only the scripts it actually needs:
     - dashboard → `nav-dashboard-polish.js`
     - budget → `budget-polish.js`, `budget-category-drilldown.js`
     - recipes → `weekly-menu-sheets-entry.js`, `weekly-menu-snack-slot.js`, `grocery-consolidate-sort.js`
     - cards / cards-day → `routine-performance-fix.js`, `routine-effective-stack.js`, `nav-dashboard-polish.js`

Also removed **6 broken `<script>` references** (`cards_day.html` × 5,
`routines.html` × 1) that pointed at JS files which do not exist — each was a
404 round-trip on load.

## Deleted dead files (and what they were)

These had **zero live references** (they only referenced each other) and were
leftovers from abandoned iterations:

### Abandoned "routines v2" prototype island
A ground-up routine rewrite that was never wired into the app navigation (it
lived only at the orphan URL `/static/routines-v2.html`). Routine functionality
is served by `cards.html` + `routine-effective-stack.js`.
- `static/routines-v2.html`
- `static/css/routines-v2.css`
- `static/js/routines-v2.js`
- `static/js/routines-v2-layout.js`
- `static/js/routines-v2-seed.js` (seeded a hard-coded routine list into `localStorage`)

### Superseded routine patch island
Older client-side patches replaced by `routine-effective-stack.js` /
`routine-performance-fix.js`:
- `static/js/dynamic-routine-list.js` (old bucketed routine list renderer)
- `static/js/routine-stack-logic-fix.js` (old `/cards` carryover/overdue logic)
- `static/js/routine-overdue-box.js` (stub)
- `static/js/routine-schedule-fixes.js` (stub)
- `static/js/routine-upcoming-actions.js` (stub)

### One-off data-seed scripts (ran on every page load!)
Single-use scripts that injected a specific week's hard-coded menu. They were
loaded globally in `base.html`, so they executed on *every* page even though
they only mattered once, for one historical week:
- `static/js/weekly-menu-fill-may11.js` (hard-coded "week of May 18, 2026" menu)
- `static/js/weekly-menu-fill-may25-one-recipe.js` (hard-coded "May 25" menu reference)

## Recommendations for a future pass (not done here)

- **Routine cards double-render:** `cards.html` renders every notecard
  server-side (each an Alpine component) and then hides them all with
  `display:none` while `routine-effective-stack.js` rebuilds the real UI from
  the API. That means the browser builds the whole grid twice. Picking one
  source of truth would cut routine-page work roughly in half.
- **`style.css` is ~100 KB and `app.js` ~85 KB.** Now that they cache properly
  this is a one-time cost, but splitting per-area CSS/JS would speed first load.
- **Server-side recipe seed** (`services/may25_recipe_seed.py`) reseeds 26
  recipes on every startup; consider gating it behind a one-time flag.
