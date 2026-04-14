"""
Category inference and user override management for budget transactions.

Uses a two-tier system:
  1. API category from the data source (e.g. INCOME, FOOD_AND_DRINK)
  2. Display category from the source (e.g. "Dyndrite", "Restaurants")
  3. User override that takes precedence over both

Provides a default rule set that maps API categories to budget sections,
plus keyword-based rules for common merchants.
"""

from services.budget_store import load_categories, save_categories

SECTION_MAP = {
    "INCOME": "income",
    "TRANSFER_IN": "income",
    "RENT_AND_UTILITIES": "bills",
    "LOAN_PAYMENTS": "bills",
    "FOOD_AND_DRINK": "food_gas",
    "GAS": "food_gas",
    "TRANSPORTATION": "food_gas",
    "ENTERTAINMENT": "misc",
    "GENERAL_MERCHANDISE": "misc",
    "SUBSCRIPTION": "subscriptions",
    "PERSONAL_CARE": "personal",
    "MEDICAL": "personal",
    "TRANSFER_OUT": "savings",
    "OTHER": "misc",
}

DISPLAY_NAMES = {
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
    "GAS": "Gas",
    "SUBSCRIPTION": "Subscriptions",
    "OTHER": "Other",
}


def get_display_category(tx: dict) -> str:
    """Return the best display name for a transaction's category."""
    override = tx.get("category_override")
    if override:
        return override
    display = tx.get("category_display")
    if display:
        return display
    api_cat = tx.get("category", "OTHER")
    return DISPLAY_NAMES.get(api_cat, api_cat.replace("_", " ").title())


def get_budget_section(tx: dict) -> str:
    """Map a transaction to a budget plan section key."""
    api_cat = tx.get("category", "OTHER")
    return SECTION_MAP.get(api_cat, "misc")


def set_category_override(tx: dict, new_category: str) -> dict:
    """Apply a user category override to a transaction."""
    tx["category_override"] = new_category.strip() if new_category else None
    return tx


def get_all_categories(transactions: list[dict]) -> list[str]:
    """Return sorted list of all unique display categories from transactions."""
    cats = set()
    for tx in transactions:
        cats.add(get_display_category(tx))
    cats.update(DISPLAY_NAMES.values())
    return sorted(cats)


def is_income(tx: dict) -> bool:
    return float(tx.get("amount", 0)) > 0


def is_expense(tx: dict) -> bool:
    return float(tx.get("amount", 0)) < 0
