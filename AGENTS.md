# AGENTS.md

## Cursor Cloud specific instructions

### Overview

Life Manager is a self-contained Flask (Python) web application — an ADHD-friendly routine tracker, baby tracker, and budget manager. There is **no database**: all data is stored as flat JSON files under `./data/`. No external services (Redis, Postgres, etc.) are required.

### Running the dev server

```
python3 app.py
```

Starts Flask on `http://0.0.0.0:5000` with debug mode and hot-reload enabled. Note: use `python3`, not `python` (the latter may not be available).

### Key environment variables (all optional)

See `config.py` for the full list. Defaults are suitable for local development; no `.env` file is needed.

### Lint / Tests

The project has no formal linter or test framework configured. To verify Python syntax across all source files:

```
python3 -m py_compile app.py && for f in config.py seed_data.py services/*.py; do python3 -m py_compile "$f"; done
```

### Project structure

See `DESIGN.md` for the full file map and architecture. Key entry point is `app.py` (Flask routes + API). Business logic lives in `services/`. Templates use Jinja2 + Alpine.js. Configuration is in `routines.yaml` and `baby_config.yaml`.

### Gotchas

- The `seed_data.py` module runs at import time (called in `app.py`). It is a no-op when `LM_DATA_DIR` is unset or points to `./data` (local dev), so it won't interfere locally.
- The `data/` directory is checked into the repo with sample data; it provides a working starting state for development.
- PDF generation (`reportlab` + `pillow`) requires system libraries (libjpeg, zlib, freetype) which are only needed inside Docker — on the VM they install via pip's bundled wheels.
