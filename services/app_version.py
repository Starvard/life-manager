"""
Release label for Home and ``/healthz``.

Production: GitHub Actions sets ``LM_APP_VERSION`` to ``pr<merge request number>`` at deploy.
Local: optional ``version.txt``, else ``git rev-parse --short`` if available, else ``dev``.
"""

from __future__ import annotations

import os
import subprocess
import threading

_DEFAULT = "dev"
# Repo root: .../life-manager/services/app_version.py -> parent dir is package root
_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
_VERSION_FILE = os.path.join(_ROOT, "version.txt")
_GIT_DIR = os.path.join(_ROOT, ".git")

_cache_lock = threading.Lock()
_cached_version: tuple[str, str] | None = None
_cached_env: str | None = None
_cached_file_mtime: float | None = None


def _version_file_mtime() -> float | None:
    try:
        return os.path.getmtime(_VERSION_FILE)
    except OSError:
        return None


def _git_short_rev() -> str | None:
    if not os.path.isdir(_GIT_DIR) and not os.path.isfile(_GIT_DIR):
        return None
    try:
        p = subprocess.run(
            ["git", "rev-parse", "--short=7", "HEAD"],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if p.returncode == 0:
            s = (p.stdout or "").strip()
            if 4 <= len(s) <= 16 and s.isalnum():
                return s
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return None


def _resolve_app_version(env: str) -> tuple[str, str]:
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
    rev = _git_short_rev()
    if rev:
        return (rev, "git")
    return (_DEFAULT, "default")


def get_app_version() -> tuple[str, str]:
    """
    Return (version_string, source) where source is one of
    ``env`` | ``file`` | ``git`` | ``default``.
    """
    global _cached_env, _cached_file_mtime, _cached_version
    env = (os.environ.get("LM_APP_VERSION", "") or "").strip()
    mtime = _version_file_mtime()
    with _cache_lock:
        if (
            _cached_version is not None
            and _cached_env == env
            and _cached_file_mtime == mtime
        ):
            return _cached_version
        _cached_env = env
        _cached_file_mtime = mtime
        _cached_version = _resolve_app_version(env)
        return _cached_version
