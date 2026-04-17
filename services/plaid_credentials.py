"""
Resolve Plaid credentials from (in priority order):

1. ``data/budget/plaid_credentials.json`` — pasted via the UI.
2. ``PLAID_CLIENT_ID`` / ``PLAID_SECRET`` / ``PLAID_ENV`` / ``PLAID_REDIRECT_URI`` env vars.
3. An optional ``.env`` file in the workspace root (simple KEY=value parsing).

This is read fresh on every call so users can update creds without restarting
the Flask process. Cursor Cloud Agent secrets are only injected at VM boot,
so giving users a way to paste them is essential on an existing agent.
"""

from __future__ import annotations

import os
import threading
from typing import Any

import config

_lock = threading.Lock()
_dotenv_cache: dict[str, str] = {}
_dotenv_mtime: float | None = None


def _parse_dotenv(path: str) -> dict[str, str]:
    """Very small KEY=VALUE parser. Strips surrounding quotes. No interpolation."""
    out: dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export "):].strip()
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if (
                    len(value) >= 2
                    and value[0] == value[-1]
                    and value[0] in ("'", '"')
                ):
                    value = value[1:-1]
                if key:
                    out[key] = value
    except OSError:
        pass
    return out


def _load_dotenv_cached() -> dict[str, str]:
    """Load `.env` from workspace root (if present), with simple mtime cache."""
    global _dotenv_cache, _dotenv_mtime
    path = os.path.join(config.BASE_DIR, ".env")
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        _dotenv_cache = {}
        _dotenv_mtime = None
        return _dotenv_cache
    if _dotenv_mtime != mtime:
        _dotenv_cache = _parse_dotenv(path)
        _dotenv_mtime = mtime
    return _dotenv_cache


def _load_creds_file() -> dict[str, Any]:
    from services.budget_store import _load_json  # avoid cycles at import

    data = _load_json(config.BUDGET_PLAID_CREDS_FILE)
    if isinstance(data, dict):
        return data
    return {}


def _save_creds_file(data: dict[str, Any]) -> None:
    from services.budget_store import _save_json

    _save_json(config.BUDGET_PLAID_CREDS_FILE, data)


def get_credentials() -> dict[str, str]:
    """Return effective Plaid credentials (file > env > .env > defaults)."""
    with _lock:
        file_data = _load_creds_file()
    dotenv_data = _load_dotenv_cached()

    def _pick(key: str, default: str = "") -> str:
        v = file_data.get(key)
        if v not in (None, ""):
            return str(v).strip()
        v = os.environ.get(key)
        if v not in (None, ""):
            return str(v).strip()
        v = dotenv_data.get(key)
        if v not in (None, ""):
            return str(v).strip()
        return default

    env_val = (_pick("PLAID_ENV", "sandbox") or "sandbox").lower()
    if env_val not in ("sandbox", "development", "production"):
        env_val = "sandbox"

    return {
        "client_id": _pick("PLAID_CLIENT_ID", ""),
        "secret": _pick("PLAID_SECRET", ""),
        "env": env_val,
        "redirect_uri": _pick("PLAID_REDIRECT_URI", ""),
    }


def is_configured() -> bool:
    c = get_credentials()
    return bool(c["client_id"] and c["secret"])


def credential_source() -> dict[str, str]:
    """Where each credential came from — for the UI to explain 'not configured'."""
    with _lock:
        file_data = _load_creds_file()
    dotenv_data = _load_dotenv_cached()

    def _src(key: str) -> str:
        if file_data.get(key):
            return "app"
        if os.environ.get(key):
            return "env"
        if dotenv_data.get(key):
            return "dotenv"
        return "missing"

    return {
        "client_id": _src("PLAID_CLIENT_ID"),
        "secret": _src("PLAID_SECRET"),
        "env": _src("PLAID_ENV"),
        "redirect_uri": _src("PLAID_REDIRECT_URI"),
    }


def save_credentials(
    client_id: str | None = None,
    secret: str | None = None,
    env: str | None = None,
    redirect_uri: str | None = None,
) -> dict[str, str]:
    """Persist credentials to the app-managed JSON file. Empty strings clear a field."""
    with _lock:
        data = _load_creds_file()
        if client_id is not None:
            data["PLAID_CLIENT_ID"] = client_id.strip()
        if secret is not None:
            data["PLAID_SECRET"] = secret.strip()
        if env is not None:
            e = (env or "").strip().lower()
            if e:
                data["PLAID_ENV"] = e if e in ("sandbox", "development", "production") else "sandbox"
            else:
                data.pop("PLAID_ENV", None)
        if redirect_uri is not None:
            v = redirect_uri.strip()
            if v:
                data["PLAID_REDIRECT_URI"] = v
            else:
                data.pop("PLAID_REDIRECT_URI", None)
        # Drop fully-blank keys to keep the file tidy
        for k in list(data.keys()):
            if not data[k]:
                del data[k]
        _save_creds_file(data)
    return get_credentials()


def clear_credentials() -> None:
    with _lock:
        _save_creds_file({})
