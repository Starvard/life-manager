"""
Plaid integration for the Budget tab.

Soft-dependent: `plaid-python` is only imported lazily, and all entry points
return structured errors when credentials are missing, so the Budget page still
works for users who want to do manual CSV imports only.

Stored per-item state lives in `data/budget/plaid_items.json`:

    {
      "items": [
        {
          "item_id": "…",
          "access_token": "…",
          "institution_name": "Chase",
          "accounts": [ {"account_id": "…", "name": "…", "mask": "…", "type": "…"} ],
          "cursor": null,
          "created_at": "…",
          "last_sync": "…"
        }
      ]
    }
"""

from __future__ import annotations

import os
import threading
from datetime import datetime
from typing import Any

import config
from services import plaid_credentials

_items_lock = threading.Lock()


# ── Credential / client bootstrap ─────────────────────────────────

def is_configured() -> bool:
    return plaid_credentials.is_configured()


def _get_client():
    """Lazily construct a Plaid API client. Raises RuntimeError if missing creds/SDK."""
    creds = plaid_credentials.get_credentials()
    if not (creds["client_id"] and creds["secret"]):
        raise RuntimeError(
            "Plaid is not configured. Paste PLAID_CLIENT_ID and PLAID_SECRET on the "
            "Connect tab, or set them in Cursor \u2192 Cloud Agents \u2192 Secrets "
            "(only picked up when a new agent VM starts)."
        )
    try:
        import plaid
        from plaid.api import plaid_api
    except ImportError as e:
        raise RuntimeError(
            "plaid-python is not installed. Run `pip install plaid-python`."
        ) from e

    host = {
        "sandbox": plaid.Environment.Sandbox,
        "development": getattr(plaid.Environment, "Development", plaid.Environment.Sandbox),
        "production": plaid.Environment.Production,
    }.get(creds["env"], plaid.Environment.Sandbox)

    configuration = plaid.Configuration(
        host=host,
        api_key={
            "clientId": creds["client_id"],
            "secret": creds["secret"],
        },
    )
    api_client = plaid.ApiClient(configuration)
    return plaid_api.PlaidApi(api_client)


# ── Item (connected bank) persistence ─────────────────────────────

def _load_items_file() -> dict:
    from services.budget_store import _load_json  # lazy to avoid cycles

    data = _load_json(config.BUDGET_PLAID_ITEMS_FILE)
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return data
    return {"items": []}


def _save_items_file(data: dict) -> None:
    from services.budget_store import _save_json

    _save_json(config.BUDGET_PLAID_ITEMS_FILE, data)


def list_items_public() -> list[dict]:
    """Return connected items with secrets stripped for the UI."""
    with _items_lock:
        data = _load_items_file()
    out = []
    for it in data.get("items", []):
        out.append(
            {
                "item_id": it.get("item_id"),
                "institution_name": it.get("institution_name") or "Bank",
                "accounts": it.get("accounts") or [],
                "created_at": it.get("created_at"),
                "last_sync": it.get("last_sync"),
            }
        )
    return out


def remove_item(item_id: str) -> bool:
    with _items_lock:
        data = _load_items_file()
        before = len(data.get("items", []))
        data["items"] = [it for it in data.get("items", []) if it.get("item_id") != item_id]
        _save_items_file(data)
    return len(data["items"]) < before


# ── Link token / public token exchange ────────────────────────────

def create_link_token(user_id: str = "life-manager-user") -> dict:
    """Return {link_token, expiration} or {error}."""
    if not is_configured():
        return {"error": "Plaid is not configured. Add PLAID_CLIENT_ID + PLAID_SECRET."}
    try:
        from plaid.model.link_token_create_request import LinkTokenCreateRequest
        from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
        from plaid.model.products import Products
        from plaid.model.country_code import CountryCode
    except ImportError:
        return {"error": "plaid-python is not installed."}

    try:
        client = _get_client()
        creds = plaid_credentials.get_credentials()
        req_kwargs: dict[str, Any] = dict(
            products=[Products("transactions")],
            client_name="Life Manager",
            country_codes=[CountryCode("US")],
            language="en",
            user=LinkTokenCreateRequestUser(client_user_id=user_id),
        )
        if creds.get("redirect_uri"):
            req_kwargs["redirect_uri"] = creds["redirect_uri"]
        response = client.link_token_create(LinkTokenCreateRequest(**req_kwargs))
        return {
            "link_token": response["link_token"],
            "expiration": str(response.get("expiration") or ""),
            "env": creds["env"],
        }
    except Exception as e:  # pragma: no cover - surface nicely in UI
        return {"error": f"Plaid link_token_create failed: {e}"}


def exchange_public_token(public_token: str, institution_name: str = "") -> dict:
    """Exchange a Link public_token for an access_token and persist the Item."""
    if not is_configured():
        return {"error": "Plaid is not configured."}
    try:
        from plaid.model.item_public_token_exchange_request import (
            ItemPublicTokenExchangeRequest,
        )
        from plaid.model.accounts_get_request import AccountsGetRequest
    except ImportError:
        return {"error": "plaid-python is not installed."}

    try:
        client = _get_client()
        exch = client.item_public_token_exchange(
            ItemPublicTokenExchangeRequest(public_token=public_token)
        )
        access_token = exch["access_token"]
        item_id = exch["item_id"]
    except Exception as e:
        return {"error": f"Plaid token exchange failed: {e}"}

    accounts: list[dict] = []
    try:
        acc_resp = client.accounts_get(AccountsGetRequest(access_token=access_token))
        for a in acc_resp.get("accounts", []) or []:
            accounts.append(
                {
                    "account_id": a.get("account_id"),
                    "name": a.get("name") or a.get("official_name") or "Account",
                    "mask": a.get("mask") or "",
                    "type": str(a.get("type") or ""),
                    "subtype": str(a.get("subtype") or ""),
                }
            )
    except Exception:
        pass

    with _items_lock:
        data = _load_items_file()
        data.setdefault("items", []).append(
            {
                "item_id": item_id,
                "access_token": access_token,
                "institution_name": institution_name or "Bank",
                "accounts": accounts,
                "cursor": None,
                "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "last_sync": None,
            }
        )
        _save_items_file(data)

    return {
        "ok": True,
        "item_id": item_id,
        "institution_name": institution_name or "Bank",
        "accounts": accounts,
    }


# ── Transactions sync ─────────────────────────────────────────────

def _plaid_tx_to_record(t: dict, account_lookup: dict[str, dict]) -> dict:
    """Convert a Plaid transaction object to our internal record shape."""
    from services.budget_dedupe import compute_fingerprint

    amt = float(t.get("amount") or 0)
    # Plaid amounts are positive for debits (money leaving) — invert for our sign convention
    internal_amount = -amt
    date_str = str(t.get("date") or "")
    if hasattr(t.get("date"), "isoformat"):
        date_str = t["date"].isoformat()
    name = t.get("name") or t.get("merchant_name") or "(transaction)"
    pfc = (t.get("personal_finance_category") or {}) or {}
    primary = str(pfc.get("primary") or "").upper() or "OTHER"
    detailed = str(pfc.get("detailed") or "")
    tx_id_raw = str(t.get("transaction_id") or "")
    account_id = str(t.get("account_id") or "")
    account_info = account_lookup.get(account_id) or {}
    account_label_parts = [
        p
        for p in [account_info.get("institution"), account_info.get("name"), account_info.get("mask")]
        if p
    ]
    account = " · ".join(account_label_parts) if account_label_parts else ""

    stable_id = "tx_plaid_" + tx_id_raw if tx_id_raw else "tx_plaid_" + compute_fingerprint(
        date_str, name, internal_amount, ""
    )[:16]
    fingerprint = compute_fingerprint(date_str, name, internal_amount, tx_id_raw)

    return {
        "id": stable_id,
        "transaction_id": tx_id_raw,
        "date": date_str,
        "description": name,
        "category": primary,
        "category_display": (detailed or primary or "OTHER")
        .replace("_", " ")
        .title(),
        "category_override": None,
        "credit": round(max(internal_amount, 0), 2),
        "debit": round(max(-internal_amount, 0), 2),
        "amount": round(internal_amount, 2),
        "account": account,
        "source": "plaid",
        "source_file": account_info.get("institution") or "plaid",
        "fingerprint": fingerprint,
        "is_duplicate": False,
        "duplicate_of": None,
        "pending": bool(t.get("pending", False)),
    }


def sync_all_items() -> dict:
    """Run /transactions/sync for every connected Item. Returns a summary."""
    from services.budget_dedupe import merge_new_transactions
    from services.budget_store import load_transactions, save_transactions

    if not is_configured():
        return {"ok": False, "error": "Plaid is not configured."}

    try:
        from plaid.model.transactions_sync_request import TransactionsSyncRequest
    except ImportError:
        return {"ok": False, "error": "plaid-python is not installed."}

    with _items_lock:
        data = _load_items_file()
        items = list(data.get("items", []))

    if not items:
        return {"ok": False, "error": "No banks connected yet."}

    client = _get_client()
    all_new_records: list[dict] = []
    removed_tx_ids: list[str] = []
    per_item_summary: list[dict] = []
    errors: list[str] = []

    for it in items:
        access_token = it.get("access_token")
        cursor = it.get("cursor")
        institution = it.get("institution_name") or "Bank"
        account_lookup = {
            a.get("account_id"): {
                "institution": institution,
                "name": a.get("name"),
                "mask": a.get("mask"),
            }
            for a in (it.get("accounts") or [])
        }

        added_records: list[dict] = []
        modified_records: list[dict] = []
        removed_ids: list[str] = []
        has_more = True
        loop_guard = 0
        try:
            while has_more and loop_guard < 20:
                loop_guard += 1
                req_kwargs = {"access_token": access_token}
                if cursor:
                    req_kwargs["cursor"] = cursor
                resp = client.transactions_sync(TransactionsSyncRequest(**req_kwargs))

                # Refresh account lookup from response (ensures masks are populated)
                for a in resp.get("accounts", []) or []:
                    account_lookup[a.get("account_id")] = {
                        "institution": institution,
                        "name": a.get("name") or a.get("official_name") or "Account",
                        "mask": a.get("mask") or "",
                    }

                for t in resp.get("added", []) or []:
                    added_records.append(_plaid_tx_to_record(t, account_lookup))
                for t in resp.get("modified", []) or []:
                    modified_records.append(_plaid_tx_to_record(t, account_lookup))
                for t in resp.get("removed", []) or []:
                    removed_ids.append(str(t.get("transaction_id") or ""))

                has_more = bool(resp.get("has_more"))
                cursor = resp.get("next_cursor") or cursor
        except Exception as e:
            errors.append(f"{institution}: {e}")
            per_item_summary.append(
                {"institution_name": institution, "item_id": it.get("item_id"), "error": str(e)}
            )
            continue

        # Persist cursor / last_sync
        with _items_lock:
            fresh = _load_items_file()
            for sit in fresh.get("items", []):
                if sit.get("item_id") == it.get("item_id"):
                    sit["cursor"] = cursor
                    sit["last_sync"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
                    if not sit.get("accounts") and account_lookup:
                        sit["accounts"] = [
                            {"account_id": aid, "name": a.get("name"), "mask": a.get("mask"), "type": "", "subtype": ""}
                            for aid, a in account_lookup.items()
                        ]
            _save_items_file(fresh)

        all_new_records.extend(added_records)
        all_new_records.extend(modified_records)
        removed_tx_ids.extend([tid for tid in removed_ids if tid])
        per_item_summary.append(
            {
                "institution_name": institution,
                "item_id": it.get("item_id"),
                "added": len(added_records),
                "modified": len(modified_records),
                "removed": len(removed_ids),
            }
        )

    # Apply to transactions store
    existing = load_transactions()
    if removed_tx_ids:
        existing = [tx for tx in existing if tx.get("transaction_id") not in set(removed_tx_ids)]

    # For modified records we want to overwrite the existing row
    incoming_by_tx = {r.get("transaction_id"): r for r in all_new_records if r.get("transaction_id")}
    if incoming_by_tx:
        updated_existing: list[dict] = []
        for tx in existing:
            tid = tx.get("transaction_id")
            if tid and tid in incoming_by_tx:
                merged_row = dict(incoming_by_tx.pop(tid))
                # Preserve user overrides / dupe dismissals
                if tx.get("category_override"):
                    merged_row["category_override"] = tx["category_override"]
                merged_row["is_duplicate"] = tx.get("is_duplicate", False)
                updated_existing.append(merged_row)
            else:
                updated_existing.append(tx)
        existing = updated_existing
        remaining_new = list(incoming_by_tx.values())
    else:
        remaining_new = all_new_records

    if remaining_new:
        merged = merge_new_transactions(existing, remaining_new)
    else:
        merged = existing
    save_transactions(merged)

    return {
        "ok": True,
        "items": per_item_summary,
        "added": sum(s.get("added", 0) for s in per_item_summary),
        "modified": sum(s.get("modified", 0) for s in per_item_summary),
        "removed": sum(s.get("removed", 0) for s in per_item_summary),
        "total": len(merged),
        "errors": errors,
    }
