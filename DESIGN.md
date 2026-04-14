# Life Manager -- Design Document

## Purpose

An ADHD-friendly routine and baby tracking app. Interactive notecards are filled out in-browser (mobile or desktop). History is a browsable collection of completed cards. PDF printing is optional.

## File Map

```
life-manager/
  app.py                     Flask entry point, all routes (HTML + JSON API)
  config.py                  Paths, constants
  routines.yaml              Routine area/task definitions (source of truth for scheduling)
  baby_config.yaml           Baby tracker track definitions
  requirements.txt           Python deps: flask, reportlab, pyyaml, pillow
  DESIGN.md                  This file

  services/
    routine_manager.py       Load/save routines.yaml
    week_planner.py          Weekly dot scheduling (global load-balanced)
    card_store.py            Read/write/auto-generate routine + baby card JSON
    card_generator.py        PDF export for routine cards
    baby_card_generator.py   PDF export for baby cards
    review.py                Legacy review/suggestion engine

  templates/
    base.html                Shell: sidebar (desktop) / bottom tabs (mobile), Alpine.js CDN
    dashboard.html            Overview + quick actions
    cards.html               Interactive routine cards (Alpine.js components)
    baby.html                Interactive baby cards (Alpine.js components)
    routines.html            Edit areas and tasks
    review.html              Weekly review

  static/
    css/style.css            Mobile-first responsive styles
    js/app.js                Alpine.js components and API helpers
    manifest.json            PWA-lite manifest for Android home screen

  data/
    routine-cards/           One JSON per area per week
      2026-W12/
        hygiene.json
        self-care.json
        ...
    baby-cards/              One JSON per day
      2026-03-16.json
      2026-03-17.json
      ...
    cards/                   Generated PDFs (export)
    photos/                  Uploaded review photos
```

## Data Models

### Routine Card (`data/routine-cards/<week_key>/<area_key>.json`)

```json
{
  "week_key": "2026-W12",
  "area_key": "hygiene",
  "area_name": "Hygiene",
  "week_start": "2026-03-16",
  "tasks": [
    {
      "name": "Shower",
      "freq": 4,
      "days": [[false],[false],[false],[false],[false],[false],[false]],
      "scheduled": [0, 1, 1, 0, 1, 0, 1]
    }
  ],
  "notes": ""
}
```

- `days` is 7 arrays (Mon-Sun). Every day has at least 1 boolean (always clickable). `true` = completed.
- `scheduled` is 7 integers: how many dots the planner assigned to each day. `0` means unscheduled (dot renders gray/dashed but is still interactive). Dots at index `doi < scheduled[d]` are "scheduled" (bright); dots at `doi >= scheduled[d]` are "bonus" (dimmed).
- Overdue dots: scheduled + unfilled + day is in the past = orange-to-red gradient.
- Scheduling uses a spacing-first algorithm: evenly-spaced base pattern + rotation scoring against global day-load totals.
- **Carryover**: Rolls **only** when (a) the **previous ISO week** had an unfilled *scheduled* dot for that task, (b) **this week’s plan does not already schedule Monday** (avoids doubling up when the planner already put a dot there), and (c) **`freq` is at most 2/week and below daily** (`freq < 7` and `freq ≤ 2`). Examples that roll: weekly deep clean, bi-weekly, monthly-style. **Skipped** for 3+ times/week (e.g. shower ×4) — those already have several touchpoints per week; overdue coloring on each scheduled dot is the nudge. Applied on first generate and on load if missing (`carryover_week_key` idempotency).
- **High-frequency reconcile**: On load, tasks with **`freq > 2` or `freq ≥ 7`** are re-synced to `plan_week` dot counts (and row lengths). Preserves checkmarks where indices still line up; strips `carryover` metadata. Fixes old JSON where carryover had added extra Monday slots even though `scheduled` was later edited.
- **`extra_tasks`**: Per-week, per-area one-off rows (name + 7 optional dots). Shown under “This week only” on the cards UI; not written to `routines.yaml`. Preserved across “Save routines” regeneration for the same week.

Auto-generated from `routines.yaml` + `week_planner.plan_week()` on first access. Subsequent loads return saved state. Old cards without `scheduled` are migrated on load.

### Baby Card (`data/baby-cards/<YYYY-MM-DD>.json`)

```json
{
  "date": "2026-03-16",
  "baby_name": "Robinson",
  "tracks": {
    "nursing_l":    {"type": "blocks", "squares": [48 booleans], "label": "Nursing L"},
    "nursing_r":    {"type": "blocks", "squares": [48 booleans], "label": "Nursing R"},
    "bottle":       {"type": "blocks", "squares": [48 booleans], "label": "Bottle"},
    "wet_diaper":   {"type": "tally", "count": 0, "label": "Wet Diaper"},
    "dirty_diaper": {"type": "tally", "count": 0, "label": "Dirty Diaper"},
    "rowan_sleep":  {"type": "blocks", "squares": [48 booleans], "label": "Rowan Sleep"},
    "jenna_sleep":  {"type": "blocks", "squares": [48 booleans], "label": "Jenna Sleep"},
    "tylenol":      {"type": "blocks", "squares": [48 booleans], "label": "Tylenol (J)"},
    "ibuprofen":    {"type": "blocks", "squares": [48 booleans], "label": "Ibuprofen (J)"},
    "notes":        {"type": "notes", "text": ""}
  }
}
```

All block tracks use 48 booleans representing 30-minute intervals across 24 hours. Auto-generated from `baby_config.yaml` on first access.

### Routine Config (`routines.yaml`)

```yaml
areas:
  hygiene:
    name: Hygiene
    tasks:
      - name: Floss
        freq: 14          # times per week (14 = 2x daily)
      - name: HVAC
        freq_per_year: 2   # converted to freq internally
      - name: Trash
        freq: 1
        on_days: [1]      # optional: 0=Mon … 6=Sun — pin dots to these weekdays
```

- **`on_days`**: Optional list of weekday indices (`0` Monday through `6` Sunday). When set, the planner places scheduled dots on those days instead of auto-balancing. `freq` rounded to an integer is how many dots appear; if that exceeds the number of checked days, dots cycle across the selected days (e.g. `freq: 4` with Mon+Wed only → two dots each on Mon and Wed). Daily tasks (`freq >= 7`) ignore `on_days`. Rare tasks (`freq_per_year` / sub-weekly) can use `on_days` for which weekday the single due dot appears.

### Baby Config (`baby_config.yaml`)

Only three track types: `blocks` (48 shadeable squares), `tally` (+/- counter), `notes` (free text).

```yaml
baby_name: Robinson
tracks:
  - key: nursing_l
    label: Nursing L
    type: blocks
    hint: shade when feeding
  - key: rowan_sleep
    label: Rowan Sleep
    type: blocks
    hint: shade 30-min blocks
  - key: wet_diaper
    label: Wet Diaper
    type: tally
  - key: notes
    label: Notes
    type: notes
```

## API Reference

All JSON API endpoints are under `/api/`. HTML page routes remain for server-rendered shells.

### Routine Cards

| Method | Path | Body | Returns |
|--------|------|------|---------|
| GET | `/api/routine-cards/<week_key>` | -- | `{areas: {key: cardJSON}}` |
| PATCH | `/api/routine-cards/<week_key>/<area_key>/toggle` | `{task: int, day: int, dot: int}` | `{ok, value}` |
| PUT | `/api/routine-cards/<week_key>/<area_key>/notes` | `{notes: str}` | `{ok}` |
| GET | `/api/routine-cards/weeks` | -- | `{weeks: [str]}` |

### Baby Cards

| Method | Path | Body | Returns |
|--------|------|------|---------|
| GET | `/api/baby-cards/<date>` | -- | full card JSON |
| PATCH | `/api/baby-cards/<date>/track` | `{track: str, ...fields}` | `{ok}` |
| GET | `/api/baby-cards/days` | -- | `{days: [str]}` |

### Existing HTML Routes

| Path | Purpose |
|------|---------|
| `/` | Dashboard |
| `/cards` | Interactive routine cards |
| `/baby` | Interactive baby tracker |
| `/routines` | Edit routine config |
| `/review` | Weekly review |

## UI Components

### Routine Card
- Container: white bg, 12px radius, subtle shadow
- Header: dark slate bar with area name + week
- Grid: task names left, 7 day columns, tappable dot circles (32px on mobile)
- Dot states: open circle (border only) -> filled circle (solid + scale animation)
- Notes field at bottom

### Baby Card
- Container: white bg, 12px radius, purple header
- Track rows: label left, interactive content right
- Block tracks: 24 columns x 2 rows (48 half-hour squares), time labels every 3 hours, tappable to shade/unshade
- Tally: minus/plus buttons flanking a counter
- Notes: expandable textarea
- PATCH body for blocks: `{track: str, square: int, value: bool}`
- PATCH body for tally: `{track: str, count: int}`
- PATCH body for notes: `{track: str, text: str}`

### Navigation
- Desktop: left sidebar (220px)
- Mobile (<768px): bottom tab bar (fixed)
- Week/day pickers in page headers

## Running the App

```bash
cd life-manager
pip install -r requirements.txt
python app.py
```

Starts on `0.0.0.0:5000`. Local IP printed at startup for phone access.
