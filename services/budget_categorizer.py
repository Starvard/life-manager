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

import re

from services.budget_store import load_categories, save_categories

# ── Built-in display categories for our simple budget ────────────

BUDGET_CATEGORIES = [
    "Income",
    "Housing",
    "Utilities",
    "Groceries",
    "Dining",
    "Transportation",
    "Gas",
    "Shopping",
    "Entertainment",
    "Subscriptions",
    "Personal Care",
    "Medical",
    "Travel",
    "Education",
    "Kids",
    "Pets",
    "Gifts & Donations",
    "Fees & Interest",
    "Taxes",
    "Transfers",
    "Savings",
    "Investments",
    "Loans",
    "Other",
]


# Map Plaid personal_finance_category.primary values to our display categories
_PLAID_PRIMARY_MAP = {
    "INCOME": "Income",
    "TRANSFER_IN": "Transfers",
    "TRANSFER_OUT": "Transfers",
    "LOAN_PAYMENTS": "Loans",
    "BANK_FEES": "Fees & Interest",
    "ENTERTAINMENT": "Entertainment",
    "FOOD_AND_DRINK": "Dining",
    "GENERAL_MERCHANDISE": "Shopping",
    "HOME_IMPROVEMENT": "Housing",
    "MEDICAL": "Medical",
    "PERSONAL_CARE": "Personal Care",
    "GENERAL_SERVICES": "Other",
    "GOVERNMENT_AND_NON_PROFIT": "Gifts & Donations",
    "TRANSPORTATION": "Transportation",
    "TRAVEL": "Travel",
    "RENT_AND_UTILITIES": "Utilities",
    "GROCERIES": "Groceries",
    "SUBSCRIPTION": "Subscriptions",
    "OTHER": "Other",
}


# Built-in keyword rules (matched as case-insensitive substrings on description)
_DEFAULT_KEYWORD_RULES: list[tuple[str, str]] = [
    # Groceries / food
    ("whole foods", "Groceries"),
    ("trader joe", "Groceries"),
    ("safeway", "Groceries"),
    ("kroger", "Groceries"),
    ("aldi", "Groceries"),
    ("publix", "Groceries"),
    ("wegmans", "Groceries"),
    ("costco", "Groceries"),
    ("walmart", "Groceries"),
    ("target", "Shopping"),
    ("cvs", "Personal Care"),
    ("walgreens", "Personal Care"),
    ("rite aid", "Personal Care"),
    # Dining
    ("doordash", "Dining"),
    ("ubereats", "Dining"),
    ("uber eats", "Dining"),
    ("grubhub", "Dining"),
    ("chipotle", "Dining"),
    ("starbucks", "Dining"),
    ("dunkin", "Dining"),
    ("mcdonald", "Dining"),
    ("panera", "Dining"),
    ("domino", "Dining"),
    ("pizza", "Dining"),
    ("restaurant", "Dining"),
    ("cafe", "Dining"),
    # Transportation / gas
    ("uber", "Transportation"),
    ("lyft", "Transportation"),
    ("shell", "Gas"),
    ("chevron", "Gas"),
    ("exxon", "Gas"),
    ("bp ", "Gas"),
    (" bp#", "Gas"),
    ("mobil", "Gas"),
    ("costco gas", "Gas"),
    ("valero", "Gas"),
    ("sunoco", "Gas"),
    # Subscriptions
    ("netflix", "Subscriptions"),
    ("spotify", "Subscriptions"),
    ("hulu", "Subscriptions"),
    ("disney+", "Subscriptions"),
    ("hbo", "Subscriptions"),
    ("apple.com/bill", "Subscriptions"),
    ("icloud", "Subscriptions"),
    ("youtube", "Subscriptions"),
    ("prime video", "Subscriptions"),
    ("amazon prime", "Subscriptions"),
    ("audible", "Subscriptions"),
    ("dropbox", "Subscriptions"),
    ("chatgpt", "Subscriptions"),
    ("openai", "Subscriptions"),
    # Shopping
    ("amazon", "Shopping"),
    ("amzn mktp", "Shopping"),
    ("ebay", "Shopping"),
    ("etsy", "Shopping"),
    ("best buy", "Shopping"),
    # Housing / utilities
    ("rent", "Housing"),
    ("mortgage", "Housing"),
    ("hoa ", "Housing"),
    ("comcast", "Utilities"),
    ("xfinity", "Utilities"),
    ("spectrum", "Utilities"),
    ("verizon", "Utilities"),
    ("at&t", "Utilities"),
    ("t-mobile", "Utilities"),
    ("tmobile", "Utilities"),
    ("pge ", "Utilities"),
    ("pg&e", "Utilities"),
    ("con ed", "Utilities"),
    ("coned", "Utilities"),
    ("water", "Utilities"),
    ("electric", "Utilities"),
    # Health
    ("cvs pharmacy", "Medical"),
    ("urgent care", "Medical"),
    ("dental", "Medical"),
    ("vision", "Medical"),
    ("hospital", "Medical"),
    # Travel
    ("airbnb", "Travel"),
    ("airlines", "Travel"),
    ("delta air", "Travel"),
    ("united air", "Travel"),
    ("american air", "Travel"),
    ("southwest air", "Travel"),
    ("marriott", "Travel"),
    ("hilton", "Travel"),
    ("hyatt", "Travel"),
    # Transfers / income
    ("payroll", "Income"),
    ("direct dep", "Income"),
    ("paycheck", "Income"),
    ("venmo", "Transfers"),
    ("zelle", "Transfers"),
    ("cash app", "Transfers"),
    ("cashapp", "Transfers"),
    ("paypal", "Transfers"),
    ("transfer to", "Transfers"),
    ("transfer from", "Transfers"),
    # Fees
    ("interest charge", "Fees & Interest"),
    ("late fee", "Fees & Interest"),
    ("overdraft", "Fees & Interest"),
    ("atm fee", "Fees & Interest"),
    # Pets
    ("petco", "Pets"),
    ("petsmart", "Pets"),
    ("chewy", "Pets"),
    # Kids
    ("daycare", "Kids"),
    ("preschool", "Kids"),
    # Donations
    ("donat", "Gifts & Donations"),
]


def _load_rules() -> dict[str, str]:
    """Return merged rules: built-ins overlaid with learned overrides."""
    cats = load_categories()
    learned = cats.get("rules") or {}
    merged: dict[str, str] = {k.lower(): v for k, v in dict(_DEFAULT_KEYWORD_RULES).items()}
    for k, v in learned.items():
        if k and v:
            merged[str(k).lower()] = str(v)
    return merged


def _match_rule(description: str, rules: dict[str, str]) -> str | None:
    if not description:
        return None
    hay = description.lower()
    # Prefer longer keyword matches first
    for kw in sorted(rules.keys(), key=len, reverse=True):
        if kw and kw in hay:
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
            return "Income"
    except (TypeError, ValueError):
        pass
    return "Other"


def get_display_category(tx: dict) -> str:
    """Return the best display name for a transaction's category.

    User overrides win; otherwise auto-infer via keyword rules + source data.
    """
    override = tx.get("category_override")
    if override:
        return str(override)
    return infer_category(tx)


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


def set_category_override(tx: dict, new_category: str) -> dict:
    """Apply a user category override to a transaction (and learn a rule)."""
    clean = (new_category or "").strip()
    tx["category_override"] = clean or None
    if clean:
        learn_rule_from_override(tx, clean)
    return tx


def get_all_categories(transactions: list[dict]) -> list[str]:
    """Return sorted list of all unique display categories."""
    cats = set(BUDGET_CATEGORIES)
    for tx in transactions or []:
        cats.add(get_display_category(tx))
    # Filter out empties/None
    return sorted(c for c in cats if c)


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


def delete_keyword_rule(keyword: str) -> bool:
    cats = load_categories()
    rules = cats.get("rules") or {}
    key = (keyword or "").strip().lower()
    if key in rules:
        del rules[key]
        cats["rules"] = rules
        save_categories(cats)
        return True
    return False


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
