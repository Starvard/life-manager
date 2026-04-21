"""
Category inference and user override management for budget transactions.

Three-tier resolution (most important first):
  1. ``category_override`` on the transaction (explicit user pick)
  2. Keyword rules: built-in defaults + rules learned from user overrides
  3. Source-provided category (Plaid personal_finance_category.primary or
     legacy sheet category_display), mapped to a friendly display name

Rules are persisted in ``data/budget/categories.json`` under ``"rules"`` as
``{"keyword_lowercase": "Display Category"}``. When a user edits a
transaction's category via the UI, a rule is learned automatically so that
future similar transactions pick up the same category.
"""

from __future__ import annotations

import os
import re
import threading

import config
from services.budget_category_list import BUDGET_CATEGORY_ORDER
from services.budget_store import (
    load_categories,
    save_categories,
    load_transactions,
    save_transactions,
    load_budgets,
    save_budgets,
)

# ── Built-in display categories (emoji + label), ordered for pickers ─

BUDGET_CATEGORIES = list(BUDGET_CATEGORY_ORDER)


# Map Plaid personal_finance_category.primary values to our display categories
_PLAID_PRIMARY_MAP = {
    "INCOME": "💰 Other Income",
    "TRANSFER_IN": "📩 Internal Transfer",
    "TRANSFER_OUT": "📩 Internal Transfer",
    "LOAN_PAYMENTS": "💳 Credit Card Payments",
    "BANK_FEES": "🏬 Shopping",
    "ENTERTAINMENT": "🎉 Entertainment",
    "FOOD_AND_DRINK": "🍴Restaurants",
    "GENERAL_MERCHANDISE": "🏬 Shopping",
    "HOME_IMPROVEMENT": "🛖 Home Improvement",
    "MEDICAL": "🚑 Medical Fund",
    "PERSONAL_CARE": "💆‍♀️ Massage",
    "GENERAL_SERVICES": "🏬 Shopping",
    "GOVERNMENT_AND_NON_PROFIT": "🏬 Shopping",
    "TRANSPORTATION": "⛽ Gas",
    "TRAVEL": "🎉 Entertainment",
    "RENT_AND_UTILITIES": "⚡Electricity",
    "GROCERIES": "🛒 Groceries",
    "SUBSCRIPTION": "🎉 Entertainment",
    "OTHER": "🏬 Shopping",
}


# Built-in keyword rules (matched as case-insensitive substrings on description)
_DEFAULT_KEYWORD_RULES: list[tuple[str, str]] = [
    # Groceries / food
    ("whole foods", "🛒 Groceries"),
    ("trader joe", "🛒 Groceries"),
    ("safeway", "🛒 Groceries"),
    ("kroger", "🛒 Groceries"),
    ("aldi", "🛒 Groceries"),
    ("publix", "🛒 Groceries"),
    ("wegmans", "🛒 Groceries"),
    ("costco", "🛒 Groceries"),
    ("walmart", "🛒 Groceries"),
    ("target", "🏬 Shopping"),
    ("cvs", "🩺 Reoccuring Med."),
    ("walgreens", "🩺 Reoccuring Med."),
    ("rite aid", "🩺 Reoccuring Med."),
    # Dining
    ("doordash", "🍴Restaurants"),
    ("ubereats", "🍴Restaurants"),
    ("uber eats", "🍴Restaurants"),
    ("grubhub", "🍴Restaurants"),
    ("chipotle", "🍴Restaurants"),
    ("starbucks", "🍴Restaurants"),
    ("dunkin", "🍴Restaurants"),
    ("mcdonald", "🍴Restaurants"),
    ("panera", "🍴Restaurants"),
    ("domino", "🍴Restaurants"),
    ("pizza", "🍴Restaurants"),
    ("restaurant", "🍴Restaurants"),
    ("cafe", "🍴Restaurants"),
    # Transportation / gas (ride-share → general transport spend)
    ("uber", "⛽ Gas"),
    ("lyft", "⛽ Gas"),
    ("shell", "⛽ Gas"),
    ("chevron", "⛽ Gas"),
    ("exxon", "⛽ Gas"),
    ("bp ", "⛽ Gas"),
    (" bp#", "⛽ Gas"),
    ("mobil", "⛽ Gas"),
    ("costco gas", "⛽ Gas"),
    ("valero", "⛽ Gas"),
    ("sunoco", "⛽ Gas"),
    # Subscriptions / digital
    ("netflix", "📺 Netflix"),
    ("spotify", "🎉 Entertainment"),
    ("hulu", "🎉 Entertainment"),
    ("disney+", "🎉 Entertainment"),
    ("hbo", "🎉 Entertainment"),
    ("apple.com/bill", "👜 Amazon Prime"),
    ("icloud", "📸 Google One"),
    ("youtube", "🎉 Entertainment"),
    ("prime video", "👜 Amazon Prime"),
    ("amazon prime", "👜 Amazon Prime"),
    ("audible", "👜 Amazon Prime"),
    ("dropbox", "📸 Google One"),
    ("chatgpt", "🤖 Chat GPT"),
    ("openai", "🤖 Chat GPT"),
    ("google one", "📸 Google One"),
    # Shopping
    ("amazon", "🏬 Shopping"),
    ("amzn mktp", "🏬 Shopping"),
    ("ebay", "🏬 Shopping"),
    ("etsy", "🏬 Shopping"),
    ("best buy", "🏬 Shopping"),
    # Housing / utilities
    ("rent", "🏡 Mortgage"),
    ("mortgage", "🏡 Mortgage"),
    ("hoa ", "🏡 Mortgage"),
    ("comcast", "🖥️ Internet"),
    ("xfinity", "🖥️ Internet"),
    ("spectrum", "🖥️ Internet"),
    ("verizon", "🖥️ Internet"),
    ("at&t", "🖥️ Internet"),
    ("t-mobile", "🖥️ Internet"),
    ("tmobile", "🖥️ Internet"),
    ("pge ", "⚡Electricity"),
    ("pg&e", "⚡Electricity"),
    ("con ed", "⚡Electricity"),
    ("coned", "⚡Electricity"),
    ("water", "💦 Water"),
    ("electric", "⚡Electricity"),
    # Health
    ("cvs pharmacy", "🚑 Medical Fund"),
    ("urgent care", "🚑 Medical Fund"),
    ("dental", "🚑 Medical Fund"),
    ("vision", "🚑 Medical Fund"),
    ("hospital", "🚑 Medical Fund"),
    # Travel / hotels → entertainment bucket for simplicity
    ("airbnb", "🎉 Entertainment"),
    ("airlines", "🎉 Entertainment"),
    ("delta air", "🎉 Entertainment"),
    ("united air", "🎉 Entertainment"),
    ("american air", "🎉 Entertainment"),
    ("southwest air", "🎉 Entertainment"),
    ("marriott", "🎉 Entertainment"),
    ("hilton", "🎉 Entertainment"),
    ("hyatt", "🎉 Entertainment"),
    # Transfers / income
    ("payroll", "💰 Other Income"),
    ("direct dep", "💰 Other Income"),
    ("paycheck", "💰 Other Income"),
    ("venmo", "📩 Internal Transfer"),
    ("zelle", "📩 Internal Transfer"),
    ("cash app", "📩 Internal Transfer"),
    ("cashapp", "📩 Internal Transfer"),
    ("paypal", "📩 Internal Transfer"),
    ("transfer to", "📩 Internal Transfer"),
    ("transfer from", "📩 Internal Transfer"),
    # Fees
    ("interest charge", "💳 Credit Card Payments"),
    ("late fee", "💳 Credit Card Payments"),
    ("overdraft", "💳 Credit Card Payments"),
    ("atm fee", "💳 Credit Card Payments"),
    # Pets
    ("petco", "🐩 Reoccuring Dog"),
    ("petsmart", "🐩 Reoccuring Dog"),
    ("chewy", "🐩 Reoccuring Dog"),
    # Kids
    ("daycare", "🎉 Entertainment"),
    ("preschool", "🎉 Entertainment"),
    # Donations
    ("donat", "🏬 Shopping"),
]


# Cached merged ruleset, invalidated by categories.json mtime. Each cache hit
# also returns the keys pre-sorted by length-desc so we don't re-sort on every
# transaction.
_rules_lock = threading.Lock()
_rules_cache: tuple[float | None, dict[str, str], list[str]] | None = None


def _load_rules_cached() -> tuple[dict[str, str], list[str]]:
    """Return (rules, sorted_keys). Cached against ``categories.json`` mtime."""
    global _rules_cache
    try:
        mtime = os.path.getmtime(config.BUDGET_CATEGORIES_FILE)
    except OSError:
        mtime = None

    with _rules_lock:
        if _rules_cache is not None and _rules_cache[0] == mtime:
            return _rules_cache[1], _rules_cache[2]
        cats = load_categories()
        learned = cats.get("rules") or {}
        merged: dict[str, str] = {
            k.lower(): v for k, v in dict(_DEFAULT_KEYWORD_RULES).items()
        }
        for k, v in learned.items():
            if k and v:
                merged[str(k).lower()] = str(v)
        sorted_keys = sorted([k for k in merged.keys() if k], key=len, reverse=True)
        _rules_cache = (mtime, merged, sorted_keys)
        return merged, sorted_keys


def _invalidate_rules_cache() -> None:
    global _rules_cache
    with _rules_lock:
        _rules_cache = None


def _load_rules() -> dict[str, str]:
    """Return merged rules: built-ins overlaid with learned overrides."""
    rules, _ = _load_rules_cached()
    return rules


def _match_rule(description: str, rules: dict[str, str]) -> str | None:
    if not description:
        return None
    hay = description.lower()
    _, sorted_keys = _load_rules_cached()
    for kw in sorted_keys:
        if kw in hay:
            return rules[kw]
    return None


def infer_category(tx: dict) -> str:
    """Return the best auto-detected display category for a transaction.

    Does not consider ``category_override`` — call :func:`get_display_category`
    for the user-facing category that respects overrides.
    """
    rules = _load_rules()

    # 1. Keyword rules beat the source category to allow learning.
    hit = _match_rule(tx.get("description", ""), rules)
    if hit:
        return hit

    # 2. Plaid / source-provided category mapping
    primary = (tx.get("category") or "").upper()
    if primary in _PLAID_PRIMARY_MAP:
        cat = _PLAID_PRIMARY_MAP[primary]
        # Special-case: Plaid PRIMARY == FOOD_AND_DRINK for groceries → Dining is wrong.
        # We can't distinguish easily without detailed; leave as Dining but rules above
        # will usually have matched Groceries for known supermarkets already.
        return cat

    # 3. Fall back to source-provided display string if it exists
    disp = (tx.get("category_display") or "").strip()
    if disp:
        return disp

    # 4. Amount-based fallback
    try:
        if float(tx.get("amount") or 0) > 0:
            return "💰 Other Income"
    except (TypeError, ValueError):
        pass
    return "🏬 Shopping"


def get_display_category(tx: dict) -> str:
    """Return the best display name for a transaction's category.

    User overrides win; otherwise auto-infer via keyword rules + source data.
    """
    override = tx.get("category_override")
    if override:
        return str(override)
    return infer_category(tx)


def category_sort_key(name: str) -> tuple[int, str]:
    """Sort key: known order first, then alphabetically for extras."""
    try:
        idx = BUDGET_CATEGORIES.index(name)
        return (0, f"{idx:04d}")
    except ValueError:
        return (1, (name or "").lower())


def learn_rule_from_override(tx: dict, new_category: str) -> None:
    """When the user changes a transaction's category, remember a keyword rule.

    We extract the first alphabetic word (>= 3 chars) from the description as
    the keyword. This is a pragmatic, reversible heuristic — users can edit
    :data:`categories.json` directly to refine.
    """
    if not new_category:
        return
    desc = (tx.get("description") or "").strip()
    if not desc:
        return
    tokens = re.findall(r"[A-Za-z][A-Za-z'&\-]{2,}", desc)
    if not tokens:
        return
    keyword = tokens[0].lower()
    # Skip very generic words that would over-match
    if keyword in {"the", "and", "inc", "llc", "for", "payment", "pos", "ach", "debit", "credit"}:
        if len(tokens) >= 2:
            keyword = tokens[1].lower()
        else:
            return

    cats = load_categories()
    rules = cats.get("rules") or {}
    rules[keyword] = new_category
    cats["rules"] = rules
    save_categories(cats)
    _invalidate_rules_cache()


def set_category_override(tx: dict, new_category: str) -> dict:
    """Apply a user category override to a transaction (and learn a rule)."""
    clean = (new_category or "").strip()
    tx["category_override"] = clean or None
    if clean:
        learn_rule_from_override(tx, clean)
    return tx


def get_all_categories(transactions: list[dict]) -> list[str]:
    """Return display categories: canonical emoji list first, then any extras."""
    canon = list(BUDGET_CATEGORIES)
    canon_set = set(canon)
    extra_set: set[str] = set()
    for tx in transactions or []:
        c = get_display_category(tx)
        if c and c not in canon_set:
            extra_set.add(c)
    extras = sorted(extra_set, key=category_sort_key)
    return canon + extras


def list_keyword_rules() -> list[dict]:
    """Return user-learned keyword rules as an orderable list."""
    cats = load_categories()
    rules = cats.get("rules") or {}
    return sorted(
        [{"keyword": k, "category": v} for k, v in rules.items()],
        key=lambda r: r["keyword"],
    )


def upsert_keyword_rule(keyword: str, category: str) -> None:
    cats = load_categories()
    rules = cats.get("rules") or {}
    rules[(keyword or "").strip().lower()] = (category or "").strip()
    cats["rules"] = {k: v for k, v in rules.items() if k and v}
    save_categories(cats)
    _invalidate_rules_cache()


def delete_keyword_rule(keyword: str) -> bool:
    cats = load_categories()
    rules = cats.get("rules") or {}
    key = (keyword or "").strip().lower()
    if key in rules:
        del rules[key]
        cats["rules"] = rules
        save_categories(cats)
        _invalidate_rules_cache()
        return True
    return False


def bulk_set_category(
    transactions: list[dict],
    ids: list[str],
    new_category: str,
    *,
    learn: bool = True,
) -> int:
    """Apply the same category override to many transactions by id. Returns count updated."""
    clean = (new_category or "").strip()
    if not clean:
        return 0
    id_set = {i for i in ids if i}
    if not id_set:
        return 0
    n = 0
    learned = False
    for tx in transactions or []:
        tid = tx.get("id")
        if tid not in id_set:
            continue
        tx["category_override"] = clean
        if learn and not learned:
            learn_rule_from_override(tx, clean)
            learned = True
        n += 1
    return n


def replace_budget_category_globally(old_name: str, new_name: str) -> dict:
    """Rename or merge a category everywhere: transactions, rules, budget limits.

    Every transaction whose *display* category equals ``old_name`` gets
    ``category_override`` set to ``new_name`` so the old label disappears from
    pickers and reports.
    """
    old = (old_name or "").strip()
    new = (new_name or "").strip()
    if not old or not new:
        return {"ok": False, "error": "Both old and new category names are required."}
    if old == new:
        return {"ok": True, "transactions_updated": 0, "rules_updated": 0, "budget_moved": False}

    txns = load_transactions()
    tx_n = 0
    for tx in txns:
        if get_display_category(tx) == old:
            tx["category_override"] = new
            tx_n += 1
    if tx_n:
        save_transactions(txns)

    cats = load_categories()
    rules = dict(cats.get("rules") or {})
    rule_n = 0
    for kw, cat in list(rules.items()):
        if cat == old:
            rules[kw] = new
            rule_n += 1
    if rule_n:
        cats["rules"] = rules
        save_categories(cats)
        _invalidate_rules_cache()

    bud = load_budgets()
    limits = dict(bud.get("limits") or {})
    budget_moved = False
    if old in limits:
        amt = limits.pop(old)
        limits[new] = round(float(limits.get(new, 0)) + float(amt), 2)
        budget_moved = True
        save_budgets(limits)

    return {
        "ok": True,
        "transactions_updated": tx_n,
        "rules_updated": rule_n,
        "budget_moved": budget_moved,
    }


def recategorize_all(transactions: list[dict]) -> int:
    """Re-apply rules to every transaction that doesn't have a user override.

    Updates ``category_display`` in-place and returns the number of changes.
    """
    changed = 0
    for tx in transactions or []:
        if tx.get("category_override"):
            continue
        new_cat = infer_category(tx)
        if tx.get("category_display") != new_cat:
            tx["category_display"] = new_cat
            changed += 1
    return changed


def is_income(tx: dict) -> bool:
    return float(tx.get("amount", 0)) > 0


def is_expense(tx: dict) -> bool:
    return float(tx.get("amount", 0)) < 0
