"""
File-backed storage for budget data: transactions, monthly plans, categories.

Transactions:  data/budget/transactions.json
Monthly plans: data/budget/plans/<YYYY-MM>.json
Categories:    data/budget/categories.json
Import meta:   data/budget/import_meta.json
"""

import json
import os
import threading
from datetime import datetime

import config

_file_locks: dict[str, threading.Lock] = {}
_locks_lock = threading.Lock()


def _get_lock(path: str) -> threading.Lock:
    with _locks_lock:
        if path not in _file_locks:
            _file_locks[path] = threading.Lock()
        return _file_locks[path]


def _ensure_dirs():
    os.makedirs(config.BUDGET_DATA_DIR, exist_ok=True)
    os.makedirs(config.BUDGET_PLANS_DIR, exist_ok=True)


def _load_json(path: str) -> dict | list | None:
    lock = _get_lock(path)
    with lock:
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            return None


def _save_json(path: str, data):
    lock = _get_lock(path)
    with lock:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)


# ── Transactions ──────────────────────────────────────────────────

def load_transactions() -> list[dict]:
    _ensure_dirs()
    data = _load_json(config.BUDGET_TRANSACTIONS_FILE)
    if isinstance(data, list):
        return data
    return []


def save_transactions(txns: list[dict]):
    _ensure_dirs()
    _save_json(config.BUDGET_TRANSACTIONS_FILE, txns)


def get_transaction_by_id(tx_id: str) -> dict | None:
    for tx in load_transactions():
        if tx.get("id") == tx_id:
            return tx
    return None


def update_transaction(tx_id: str, updates: dict) -> dict | None:
    txns = load_transactions()
    for tx in txns:
        if tx.get("id") == tx_id:
            tx.update(updates)
            save_transactions(txns)
            return tx
    return None


def get_transactions_by_month(month: str) -> list[dict]:
    """Filter transactions by month key like '2026-01'."""
    return [
        tx for tx in load_transactions()
        if tx.get("date", "")[:7] == month
    ]


def get_available_months() -> list[str]:
    """Return sorted month keys from transactions, saved overviews, and plans."""
    months = set()
    for tx in load_transactions():
        d = tx.get("date", "")
        if len(d) >= 7:
            months.add(d[:7])
    if os.path.isdir(config.BUDGET_OVERVIEW_DIR):
        for f in os.listdir(config.BUDGET_OVERVIEW_DIR):
            if f.endswith(".json") and len(f) >= 8:
                months.add(f[:-5])
    for m in list_plan_months():
        months.add(m)
    return sorted(months)


# ── Sheet overview (parsed monthly tab HTML) ────────────────────

def _overview_path(month: str) -> str:
    return os.path.join(config.BUDGET_OVERVIEW_DIR, f"{month}.json")


def load_overview(month: str) -> dict | None:
    _ensure_dirs()
    os.makedirs(config.BUDGET_OVERVIEW_DIR, exist_ok=True)
    data = _load_json(_overview_path(month))
    return data if isinstance(data, dict) else None


def save_overview(month: str, overview: dict):
    _ensure_dirs()
    os.makedirs(config.BUDGET_OVERVIEW_DIR, exist_ok=True)
    overview = dict(overview)
    overview["month"] = month
    _save_json(_overview_path(month), overview)


def refresh_overviews_from_exports(exports_dir: str) -> int:
    """Parse monthly HTML tabs and write data/budget/overviews/<month>.json."""
    from services.budget_overview_import import import_all_monthly_overviews

    parsed = import_all_monthly_overviews(exports_dir)
    for mkey, data in parsed.items():
        save_overview(mkey, data)
    return len(parsed)


# ── Monthly Plans ─────────────────────────────────────────────────

def _plan_path(month: str) -> str:
    return os.path.join(config.BUDGET_PLANS_DIR, f"{month}.json")


def load_plan(month: str) -> dict:
    _ensure_dirs()
    data = _load_json(_plan_path(month))
    if isinstance(data, dict):
        return data
    return _default_plan(month)


def save_plan(month: str, plan: dict):
    _ensure_dirs()
    plan["month"] = month
    _save_json(_plan_path(month), plan)


def _default_plan(month: str) -> dict:
    return {
        "month": month,
        "sections": {
            "income": {"label": "Income", "items": []},
            "bills": {"label": "Bills", "items": []},
            "savings": {"label": "Savings", "items": []},
            "food_gas": {"label": "Food & Gas", "items": []},
            "subscriptions": {"label": "Subscriptions", "items": []},
            "personal": {"label": "Personal Care", "items": []},
            "misc": {"label": "Misc", "items": []},
        },
        "notes": "",
    }


def list_plan_months() -> list[str]:
    _ensure_dirs()
    if not os.path.isdir(config.BUDGET_PLANS_DIR):
        return []
    return sorted(
        f[:-5] for f in os.listdir(config.BUDGET_PLANS_DIR)
        if f.endswith(".json")
    )


# ── Categories ────────────────────────────────────────────────────

def load_categories() -> dict:
    _ensure_dirs()
    data = _load_json(config.BUDGET_CATEGORIES_FILE)
    if isinstance(data, dict):
        return data
    return _default_categories()


def save_categories(cats: dict):
    _ensure_dirs()
    _save_json(config.BUDGET_CATEGORIES_FILE, cats)


def _default_categories() -> dict:
    return {
        "rules": {},
        "display_names": {
            "INCOME": "Income",
            "RENT_AND_UTILITIES": "Bills",
            "FOOD_AND_DRINK": "Food & Drink",
            "TRANSFER_IN": "Transfer In",
            "TRANSFER_OUT": "Transfer Out",
            "LOAN_PAYMENTS": "Loan Payments",
            "GENERAL_MERCHANDISE": "Shopping",
            "ENTERTAINMENT": "Entertainment",
            "PERSONAL_CARE": "Personal Care",
            "TRANSPORTATION": "Transportation",
            "MEDICAL": "Medical",
            "SUBSCRIPTION": "Subscriptions",
            "OTHER": "Other",
        },
        "custom": [],
    }


# ── Import Metadata ──────────────────────────────────────────────

def load_import_meta() -> dict:
    _ensure_dirs()
    data = _load_json(config.BUDGET_IMPORT_META_FILE)
    if isinstance(data, dict):
        return data
    return {"imports": []}


def save_import_meta(meta: dict):
    _ensure_dirs()
    _save_json(config.BUDGET_IMPORT_META_FILE, meta)


def record_import(source_file: str, tx_count: int, fingerprint: str):
    meta = load_import_meta()
    meta.setdefault("imports", []).append({
        "source_file": source_file,
        "tx_count": tx_count,
        "fingerprint": fingerprint,
        "imported_at": datetime.now().isoformat(),
    })
    save_import_meta(meta)


# ── Monthly Report (computed) ─────────────────────────────────────

def compute_monthly_report(month: str) -> dict:
    """Compute income/expense/net totals and category breakdown for a month."""
    txns = get_transactions_by_month(month)
    plan = load_plan(month)

    total_income = 0.0
    total_expenses = 0.0
    by_category: dict[str, float] = {}

    for tx in txns:
        if tx.get("is_duplicate"):
            continue
        amt = float(tx.get("amount", 0))
        cat = tx.get("category_override") or tx.get("category_display") or tx.get("category", "Other")

        by_category[cat] = by_category.get(cat, 0) + amt

        if amt > 0:
            total_income += amt
        else:
            total_expenses += amt

    net = total_income + total_expenses

    cat_breakdown = []
    for cat, total in sorted(by_category.items(), key=lambda x: x[1]):
        cat_breakdown.append({"category": cat, "total": round(total, 2)})

    sections = plan.get("sections") or {}

    def _sum_allocated(section_key: str) -> float:
        sec = sections.get(section_key) or {}
        items = sec.get("items") or []
        return sum(float(i.get("allocated") or 0) for i in items)

    planned_income = _sum_allocated("income")
    expense_section_keys = (
        "bills",
        "savings",
        "food_gas",
        "subscriptions",
        "personal",
        "misc",
    )
    planned_expenses = sum(_sum_allocated(k) for k in expense_section_keys)

    actual_expenses = abs(total_expenses)
    snapshot = {
        "planned_income": round(planned_income, 2),
        "actual_income": round(total_income, 2),
        "income_variance": round(planned_income - total_income, 2),
        "planned_expenses": round(planned_expenses, 2),
        "actual_expenses": round(actual_expenses, 2),
        "expense_variance": round(planned_expenses - actual_expenses, 2),
        "planned_net": round(planned_income - planned_expenses, 2),
        "actual_net": round(net, 2),
        "net_variance": round((planned_income - planned_expenses) - net, 2),
        "has_planned_expenses": planned_expenses > 0,
        "has_planned_income": planned_income > 0,
    }

    return {
        "month": month,
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "net": round(net, 2),
        "transaction_count": len([t for t in txns if not t.get("is_duplicate")]),
        "categories": cat_breakdown,
        "has_plan": bool(plan.get("sections", {}).get("income", {}).get("items")),
        "snapshot": snapshot,
    }
