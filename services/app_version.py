"""App release version: single source of truth in repo root ``version.txt``."""

from __future__ import annotations

import os

_DEFAULT = "0.0.0-dev"
# Repo root: .../life-manager/services/app_version.py -> parent dir is package root
_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
_VERSION_FILE = os.path.join(_ROOT, "version.txt")


def get_app_version() -> tuple[str, str]:
    """
    Return (version_string, source) where source is one of
    ``env`` | ``file`` | ``default``.
    """
    env = (os.environ.get("LM_APP_VERSION", "") or "").strip()
    if env:
        return (env, "env")
    try:
        if os.path.isfile(_VERSION_FILE):
            with open(_VERSION_FILE, "r", encoding="utf-8") as f:
                raw = f.read().strip()
            if raw and len(raw) < 200 and "\n" not in raw and "\r" not in raw:
                return (raw, "file")
    except OSError:
        pass
    return (_DEFAULT, "default")
