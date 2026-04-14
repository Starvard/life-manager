"""
Duplicate detection for budget transactions.

Uses a two-level approach:
  1. Exact match on transaction_id (provider-assigned)
  2. Fuzzy match on date + description + amount fingerprint

Keeps the first occurrence and marks later ones as duplicates.
"""

import hashlib


def compute_fingerprint(date: str, description: str, amount: float, tx_id: str) -> str:
    """Stable fingerprint for a transaction, used for duplicate detection."""
    raw = f"{tx_id}|{date}|{description}|{amount:.2f}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def deduplicate_transactions(txns: list[dict]) -> list[dict]:
    """
    Mark duplicate transactions in-place and return the full list.

    A transaction is duplicate if another transaction with the same
    transaction_id (exact) or same fingerprint already exists earlier
    in the list.
    """
    seen_tx_ids: dict[str, str] = {}
    seen_fingerprints: dict[str, str] = {}

    for tx in txns:
        tx_id_raw = tx.get("transaction_id", "")
        fingerprint = tx.get("fingerprint", "")
        stable_id = tx.get("id", "")

        if tx_id_raw and tx_id_raw in seen_tx_ids:
            tx["is_duplicate"] = True
            tx["duplicate_of"] = seen_tx_ids[tx_id_raw]
            continue

        if fingerprint and fingerprint in seen_fingerprints:
            tx["is_duplicate"] = True
            tx["duplicate_of"] = seen_fingerprints[fingerprint]
            continue

        tx["is_duplicate"] = False
        tx["duplicate_of"] = None

        if tx_id_raw:
            seen_tx_ids[tx_id_raw] = stable_id
        if fingerprint:
            seen_fingerprints[fingerprint] = stable_id

    return txns


def merge_new_transactions(existing: list[dict], incoming: list[dict]) -> list[dict]:
    """
    Merge incoming transactions into existing list without creating duplicates.

    Uses transaction_id as the primary key: if an incoming tx has the same
    transaction_id as an existing one, it's skipped. New transactions are
    appended and then the full list is re-deduped by fingerprint.
    """
    existing_tx_ids = {
        tx.get("transaction_id") for tx in existing
        if tx.get("transaction_id")
    }
    existing_fingerprints = {
        tx.get("fingerprint") for tx in existing
        if tx.get("fingerprint")
    }

    added = []
    for tx in incoming:
        tx_id = tx.get("transaction_id", "")
        fp = tx.get("fingerprint", "")

        if tx_id and tx_id in existing_tx_ids:
            continue
        if fp and fp in existing_fingerprints:
            continue

        added.append(tx)
        if tx_id:
            existing_tx_ids.add(tx_id)
        if fp:
            existing_fingerprints.add(fp)

    merged = existing + added
    return deduplicate_transactions(merged)
