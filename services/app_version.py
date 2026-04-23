"""
Release label for Home and ``/healthz``.

Production: GitHub Actions sets ``LM_APP_VERSION`` to ``pr<merge request number>`` at deploy.
Local: optional ``version.txt``, else ``git rev-parse --short`` if available, else ``dev``.
"""

from __future__ import annotations

import os
import subprocess

_DEFAULT = "dev"
# Repo root: .../life-manager/services/app_version.py -> parent dir is package root
_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
_VERSION_FILE = os.path.join(_ROOT, "version.txt")
_GIT_DIR = os.path.join(_ROOT, ".git")


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


def get_app_version() -> tuple[str, str]:
    """
    Return (version_string, source) where source is one of
    ``env`` | ``file`` | ``git`` | ``default``.
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
    rev = _git_short_rev()
    if rev:
        return (rev, "git")
    return (_DEFAULT, "default")
