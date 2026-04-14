"""Generate or load VAPID keys for Web Push (P-256)."""

from __future__ import annotations

import base64
import json
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

import config


def _generate_pair() -> tuple[str, str]:
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    pub = private_key.public_key()
    raw = pub.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    pub_b64url = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return priv_pem, pub_b64url


def ensure_vapid_keys() -> tuple[str, str]:
    """
    Return (private_pem, public_key_b64url) for applicationServerKey.
    Persists to config.VAPID_KEYS_FILE on first run.
    """
    path = config.VAPID_KEYS_FILE
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["private_pem"], data["public_b64url"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    priv, pub = _generate_pair()
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"private_pem": priv, "public_b64url": pub}, f, indent=2)
    return priv, pub


def vapid_private_key_pem_path() -> str:
    """
    Path to PEM file for pywebpush. That library parses PEM reliably from a file,
    not from an in-memory string (Vapid.from_string can mis-handle PKCS#8).
    """
    priv_pem, _ = ensure_vapid_keys()
    pem_path = os.path.join(config.DATA_DIR, "vapid_private.pem")
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(pem_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(priv_pem.strip() + "\n")
    return pem_path
