"""
Duplicate detection for budget transactions.

Uses a layered approach:
  1. Exact match on transaction_id when provider IDs are stable
  2. Stable content key for relinked Plaid items where transaction_id changes
  3. Legacy fingerprint fallback for older imported rows

Relinking Plaid can create new transaction IDs for the same historical rows.
The content key below intentionally ignores transaction_id so those rows can be
reconciled without requiring manual cleanup.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime


def _as_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _normalized_description(description: str) -> str:
    """Normalize merchant text enough to match relinked Plaid rows safely."""
    text = str(description or "").lower()
    text = text.replace("pending", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\b(pos|debit|credit|card|purchase|online|payment)\b", " ", text)
    text = re.sub(r"\b\d{4,}\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalized_account(account: str) -> str:
    """Keep enough account context to avoid cross-account false positives."""
    text = str(account or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _date_ordinal(value: str) -> int | None:
    try:
        if isinstance(value, date):
            return value.toordinal()
        return datetime.strptime(str(value or "")[:10], "%Y-%m-%d").date().toordinal()
    except Exception:
        return None


def compute_content_key(tx: dict) -> str:
    """Stable key that survives Plaid relinking.

    This deliberately ignores transaction_id. It is used only for duplicate
    reconciliation, not as a replacement primary key.
    """
    tx_date = str(tx.get("date") or tx.get("transactionDate") or "")[:10]
    amount = _as_float(tx.get("amount"))
    if not amount:
        amount = _as_float(tx.get("credit")) - _as_float(tx.get("debit"))
    desc = _normalized_description(tx.get("description") or tx.get("name") or "")
    account = _normalized_account(tx.get("account") or tx.get("bankCard") or tx.get("source_file") or "")
    raw = f"{tx_date}|{amount:.2f}|{desc}|{account}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def compute_fingerprint(date: str, description: str, amount: float, tx_id: str = "") -> str:
    """Stable-ish fingerprint for a transaction.

    Keep the old signature for callers, but stop depending on provider
    transaction_id. Plaid IDs change after relinking, while date/merchant/amount
    are the fields we actually want for duplicate reconciliation.
    """
    raw = f"{date}|{_normalized_description(description)}|{amount:.2f}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _duplicate_sort_key(tx: dict) -> tuple:
    """Prefer the row we want to keep when duplicates are found."""
    # Posted rows beat pending rows. User-reviewed rows beat untouched rows.
    pending_rank = 1 if tx.get("pending") else 0
    user_rank = 0 if (tx.get("category_override") or tx.get("is_duplicate") is False) else 1
    source_rank = 0 if tx.get("source") == "plaid" else 1
    date_rank = _date_ordinal(tx.get("date") or "") or 0
    return (pending_rank, user_rank, source_rank, -date_rank)


def _is_near_duplicate(a: dict, b: dict) -> bool:
    """Conservative fuzzy match for Plaid relink duplicates.

    Allows a small date drift only when amount, account, and merchant text match.
    """
    amount_a = _as_float(a.get("amount")) or (_as_float(a.get("credit")) - _as_float(a.get("debit")))
    amount_b = _as_float(b.get("amount")) or (_as_float(b.get("credit")) - _as_float(b.get("debit")))
    if round(amount_a, 2) != round(amount_b, 2):
        return False

    desc_a = _normalized_description(a.get("description") or a.get("name") or "")
    desc_b = _normalized_description(b.get("description") or b.get("name") or "")
    if not desc_a or not desc_b or desc_a != desc_b:
        return False

    acct_a = _normalized_account(a.get("account") or a.get("bankCard") or a.get("source_file") or "")
    acct_b = _normalized_account(b.get("account") or b.get("bankCard") or b.get("source_file") or "")
    if acct_a and acct_b and acct_a != acct_b:
        return False

    da = _date_ordinal(a.get("date") or "")
    db = _date_ordinal(b.get("date") or "")
    if da is None or db is None:
        return False
    return abs(da - db) <= 2


def _merge_preserved_fields(keeper: dict, duplicate: dict) -> None:
    """Carry user decisions forward when the newly kept row is the relinked copy."""
    if not keeper.get("category_override") and duplicate.get("category_override"):
        keeper["category_override"] = duplicate["category_override"]
    if not keeper.get("category_display") and duplicate.get("category_display"):
        keeper["category_display"] = duplicate["category_display"]


def deduplicate_transactions(txns: list[dict]) -> list[dict]:
    """
    Mark duplicate transactions in-place and return the full list.

    A transaction is duplicate if another transaction has the same provider ID,
    same relink-safe content key, same legacy fingerprint, or a conservative
    near-match within two days.
    """
    seen_tx_ids: dict[str, str] = {}
    seen_fingerprints: dict[str, str] = {}
    seen_content_keys: dict[str, str] = {}
    keepers_by_id: dict[str, dict] = {}

    # Reset first so re-running reconciliation can unstick old decisions.
    for tx in txns:
        tx["is_duplicate"] = False
        tx["duplicate_of"] = None
        tx["content_key"] = compute_content_key(tx)

    # Stable order: best keeper candidates first.
    ordered = sorted(txns, key=_duplicate_sort_key)

    for tx in ordered:
        tx_id_raw = tx.get("transaction_id", "")
        fingerprint = tx.get("fingerprint", "") or compute_fingerprint(
            str(tx.get("date") or ""),
            str(tx.get("description") or ""),
            _as_float(tx.get("amount")) or (_as_float(tx.get("credit")) - _as_float(tx.get("debit"))),
            str(tx_id_raw or ""),
        )
        content_key = tx.get("content_key") or compute_content_key(tx)
        stable_id = tx.get("id", "") or tx_id_raw or content_key

        duplicate_of = None

        if tx_id_raw and tx_id_raw in seen_tx_ids:
            duplicate_of = seen_tx_ids[tx_id_raw]
        elif content_key and content_key in seen_content_keys:
            duplicate_of = seen_content_keys[content_key]
        elif fingerprint and fingerprint in seen_fingerprints:
            duplicate_of = seen_fingerprints[fingerprint]
        else:
            for candidate_id, candidate in keepers_by_id.items():
                if _is_near_duplicate(tx, candidate):
                    duplicate_of = candidate_id
                    break

        if duplicate_of:
            tx["is_duplicate"] = True
            tx["duplicate_of"] = duplicate_of
            keeper = keepers_by_id.get(duplicate_of)
            if keeper:
                _merge_preserved_fields(keeper, tx)
            continue

        tx["is_duplicate"] = False
        tx["duplicate_of"] = None
        tx["fingerprint"] = fingerprint
        tx["content_key"] = content_key
        keepers_by_id[stable_id] = tx

        if tx_id_raw:
            seen_tx_ids[tx_id_raw] = stable_id
        if fingerprint:
            seen_fingerprints[fingerprint] = stable_id
        if content_key:
            seen_content_keys[content_key] = stable_id

    return txns


def merge_new_transactions(existing: list[dict], incoming: list[dict]) -> list[dict]:
    """
    Merge incoming transactions into existing list without creating duplicates.

    Uses transaction_id as the primary key when available, then falls back to a
    relink-safe content key so Plaid reconnections do not double-count months of
    overlapping history.
    """
    existing_tx_ids = {
        tx.get("transaction_id") for tx in existing
        if tx.get("transaction_id")
    }
    existing_content_keys = {
        compute_content_key(tx) for tx in existing
    }
    existing_fingerprints = {
        tx.get("fingerprint") for tx in existing
        if tx.get("fingerprint")
    }

    added = []
    for tx in incoming:
        tx_id = tx.get("transaction_id", "")
        content_key = compute_content_key(tx)
        fp = tx.get("fingerprint", "") or compute_fingerprint(
            str(tx.get("date") or ""),
            str(tx.get("description") or ""),
            _as_float(tx.get("amount")) or (_as_float(tx.get("credit")) - _as_float(tx.get("debit"))),
            str(tx_id or ""),
        )
        tx["content_key"] = content_key
        tx["fingerprint"] = fp

        if tx_id and tx_id in existing_tx_ids:
            continue
        if content_key and content_key in existing_content_keys:
            continue
        if fp and fp in existing_fingerprints:
            continue
        if any(_is_near_duplicate(tx, old) for old in existing):
            continue

        added.append(tx)
        if tx_id:
            existing_tx_ids.add(tx_id)
        if content_key:
            existing_content_keys.add(content_key)
        if fp:
            existing_fingerprints.add(fp)

    merged = existing + added
    return deduplicate_transactions(merged)


def reconciliation_summary(txns: list[dict]) -> dict:
    """Small helper for UI/API responses."""
    duplicates = [tx for tx in txns if tx.get("is_duplicate")]
    return {
        "total": len(txns),
        "duplicates": len(duplicates),
        "active": len(txns) - len(duplicates),
    }
