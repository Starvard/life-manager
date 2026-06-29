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

# Plaid's max Transactions history window is 730 days. This only affects newly
# linked Items; existing Items that were initialized with a shorter history
# window must be removed and re-linked if older transactions are needed.
PLAID_TRANSACTION_DAYS_REQUESTED = 730


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

def _transactions_link_config() -> Any:
    """Return the Transactions Link config for the installed plaid-python version."""
    try:
        from plaid.model.link_token_create_request_transactions import (
            LinkTokenCreateRequestTransactions,
        )

        return LinkTokenCreateRequestTransactions(
            days_requested=PLAID_TRANSACTION_DAYS_REQUESTED
        )
    except Exception:
        # Older generated plaid-python builds may not expose this model class yet,
        # but LinkTokenCreateRequest still serializes nested dicts correctly.
        return {"days_requested": PLAID_TRANSACTION_DAYS_REQUESTED}


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
            transactions=_transactions_link_config(),
        )
        if creds.get("redirect_uri"):
            req_kwargs["redirect_uri"] = creds["redirect_uri"]
        response = client.link_token_create(LinkTokenCreateRequest(**req_kwargs))
        return {
            "link_token": response["link_token"],
            "expiration": str(response.get("expiration") or ""),
            "env": creds["env"],
            "days_requested": PLAID_TRANSACTION_DAYS_REQUESTED,
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


def _reset_item_cursors(items: list[dict]) -> None:
    """Force the next Plaid sync call to return the full initial history again.

    Only used by the explicit "Full re-sync" path (``full_rebuild=True``). Day
    to day, syncs are incremental and keep the stored cursor so Plaid only
    returns the delta since last time — that is the cost-efficient pattern.
    """
    with _items_lock:
        data = _load_items_file()
        wanted = {it.get("item_id") for it in items}
        for sit in data.get("items", []):
            if sit.get("item_id") in wanted:
                sit["cursor"] = None
                sit["last_sync"] = None
        _save_items_file(data)


# ── Auto-sync settings (throttled background refresh) ─────────────

AUTO_SYNC_DEFAULT_ENABLED = True
AUTO_SYNC_DEFAULT_INTERVAL_HOURS = 12.0
# Never let the throttle drop below this many hours, so a misconfigured value
# can't turn every page load into a billable Plaid call.
AUTO_SYNC_MIN_INTERVAL_HOURS = 1.0


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", ""))
    except (ValueError, TypeError):
        return None


def get_auto_sync_settings() -> dict:
    """Return {enabled, interval_hours, last_auto_sync} from the items file."""
    with _items_lock:
        data = _load_items_file()
    enabled = data.get("auto_sync")
    if enabled is None:
        enabled = AUTO_SYNC_DEFAULT_ENABLED
    try:
        interval = float(data.get("auto_sync_interval_hours") or AUTO_SYNC_DEFAULT_INTERVAL_HOURS)
    except (TypeError, ValueError):
        interval = AUTO_SYNC_DEFAULT_INTERVAL_HOURS
    interval = max(AUTO_SYNC_MIN_INTERVAL_HOURS, interval)
    return {
        "enabled": bool(enabled),
        "interval_hours": interval,
        "last_auto_sync": data.get("last_auto_sync"),
    }


def set_auto_sync_settings(enabled: bool | None = None, interval_hours: float | None = None) -> dict:
    with _items_lock:
        data = _load_items_file()
        if enabled is not None:
            data["auto_sync"] = bool(enabled)
        if interval_hours is not None:
            try:
                data["auto_sync_interval_hours"] = max(
                    AUTO_SYNC_MIN_INTERVAL_HOURS, float(interval_hours)
                )
            except (TypeError, ValueError):
                pass
        _save_items_file(data)
    return get_auto_sync_settings()


def _mark_auto_sync_now() -> None:
    with _items_lock:
        data = _load_items_file()
        data["last_auto_sync"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        _save_items_file(data)


def auto_sync_if_due(force: bool = False) -> dict:
    """Run an incremental sync only if auto-sync is on and the throttle elapsed.

    Returns ``{"ran": bool, "due": bool, ...}``. Designed to be called on every
    Budget page load: the throttle lives server-side so multiple loads/devices
    don't each trigger a (billable) Plaid call.
    """
    settings = get_auto_sync_settings()
    if not is_configured():
        return {"ran": False, "due": False, "reason": "not_configured", **settings}
    with _items_lock:
        items = list(_load_items_file().get("items", []))
    if not items:
        return {"ran": False, "due": False, "reason": "no_items", **settings}
    if not force and not settings["enabled"]:
        return {"ran": False, "due": False, "reason": "disabled", **settings}

    last = _parse_iso(settings["last_auto_sync"])
    due = True
    if last is not None and not force:
        elapsed_h = (datetime.utcnow() - last).total_seconds() / 3600.0
        due = elapsed_h >= settings["interval_hours"]
    if not due:
        return {"ran": False, "due": False, "reason": "throttled", **settings}

    # Stamp the time *before* syncing so a slow/failed call doesn't let a
    # second concurrent page load kick off another sync.
    _mark_auto_sync_now()
    result = sync_all_items(full_rebuild=False)
    result["ran"] = bool(result.get("ok"))
    result["due"] = True
    result.update(get_auto_sync_settings())
    return result


# ── Transactions sync (incremental by default) ───────────────────

def _apply_incremental_updates(
    existing: list[dict],
    added_records: list[dict],
    modified_records: list[dict],
    removed_tx_ids: list[str],
) -> list[dict]:
    """Apply a Plaid delta to the stored transaction list.

    - ``removed`` Plaid rows are dropped.
    - ``modified`` rows replace the matching stored row in place, preserving the
      user's category override.
    - ``added`` rows (plus any modified rows we couldn't match) are merged with
      the existing dedupe logic so relinks don't double-count.
    """
    from services.budget_dedupe import deduplicate_transactions, merge_new_transactions

    removed_set = {r for r in removed_tx_ids if r}
    modified_by_id = {
        r.get("transaction_id"): r for r in modified_records if r.get("transaction_id")
    }

    new_existing: list[dict] = []
    for tx in existing:
        tid = tx.get("transaction_id")
        is_plaid = tx.get("source") == "plaid"
        if is_plaid and tid and tid in removed_set:
            continue
        if is_plaid and tid and tid in modified_by_id:
            rec = dict(modified_by_id.pop(tid))
            # Carry user decisions forward across the modification.
            if tx.get("category_override"):
                rec["category_override"] = tx["category_override"]
            if tx.get("is_duplicate") is False:
                rec["is_duplicate"] = False
            new_existing.append(rec)
        else:
            new_existing.append(tx)

    incoming_adds = list(added_records) + list(modified_by_id.values())
    if incoming_adds:
        return merge_new_transactions(new_existing, incoming_adds)
    return deduplicate_transactions(new_existing)


def sync_all_items(full_rebuild: bool = False) -> dict:
    """Run /transactions/sync for every connected Item. Returns a summary.

    By default this is a true **incremental** cursor sync: each Item's stored
    cursor is reused so Plaid only returns the transactions that changed since
    last time. This is the cost-efficient pattern — pulling the full multi-year
    history on every sync (which the app used to do) multiplies Plaid API calls
    and is the main reason syncs got expensive.

    Pass ``full_rebuild=True`` for the rare cleanup case (e.g. right after a
    bank relink): cursors are cleared, the entire history is re-pulled, and all
    ``source=plaid`` rows are rebuilt from scratch. Manual/CSV rows are kept.
    """
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

    if full_rebuild:
        # Clear cursors so Plaid returns the initial full history for each Item.
        _reset_item_cursors(items)
        for it in items:
            it["cursor"] = None

    client = _get_client()
    all_added_records: list[dict] = []
    all_modified_records: list[dict] = []
    all_removed_ids: list[str] = []
    per_item_summary: list[dict] = []
    errors: list[str] = []

    for it in items:
        access_token = it.get("access_token")
        cursor = None if full_rebuild else (it.get("cursor") or None)
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
            while has_more and loop_guard < 50:
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

        # Persist fresh cursor / last_sync only after this item succeeds.
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

        all_added_records.extend(added_records)
        all_modified_records.extend(modified_records)
        all_removed_ids.extend(removed_ids)
        per_item_summary.append(
            {
                "institution_name": institution,
                "item_id": it.get("item_id"),
                "added": len(added_records),
                "modified": len(modified_records),
                "removed": len(removed_ids),
            }
        )

    existing = load_transactions()
    removed_plaid_count = 0
    any_changes = bool(all_added_records or all_modified_records or all_removed_ids)

    if full_rebuild:
        non_plaid_existing = [tx for tx in existing if tx.get("source") != "plaid"]
        removed_plaid_count = len(existing) - len(non_plaid_existing)
        if all_added_records or all_modified_records:
            merged = merge_new_transactions(
                non_plaid_existing, all_added_records + all_modified_records
            )
        else:
            # All Items failed / returned nothing: keep history rather than wipe.
            merged = existing if errors else non_plaid_existing
    elif any_changes:
        merged = _apply_incremental_updates(
            existing, all_added_records, all_modified_records, all_removed_ids
        )
    else:
        # Nothing changed — leave the file (and its cache) untouched.
        merged = existing

    if merged is not existing:
        save_transactions(merged)

    return {
        "ok": True,
        "mode": "full_rebuild" if full_rebuild else "incremental",
        "items": per_item_summary,
        "added": sum(s.get("added", 0) for s in per_item_summary),
        "modified": sum(s.get("modified", 0) for s in per_item_summary),
        "removed": sum(s.get("removed", 0) for s in per_item_summary),
        "rebuilt_plaid_rows_removed": removed_plaid_count,
        "total": len(merged),
        "errors": errors,
    }
