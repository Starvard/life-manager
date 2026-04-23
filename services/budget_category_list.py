"""
Canonical ordered list of budget category display names (emoji + label).

Used by ``budget_categorizer.BUDGET_CATEGORIES`` so the picker and reports stay
consistent. Edit this file to add/reorder categories app-wide.
"""

from __future__ import annotations

# Used when separating card payoffs from "everyday" spending in reports.
CREDIT_CARD_PAYMENT_CATEGORY = "💳 Credit Card Payments"
INTERNAL_TRANSFER_CATEGORY = "📩 Internal Transfer"

# Positive amounts in these categories count as "earned" / take-home for projections & alerts.
# (Other payees, e.g. Gusto, should map to one of these via keyword rules or overrides.)
SALARY_INCOME_CATEGORY_NAMES: frozenset[str] = frozenset(
    {
        "🔥 Dyndrite",
        "💰 Other Income",
        "💵 Jenna Sales",
        "🎈From Savings",
    }
)

# User-defined emoji categories — order is preserved in dropdowns and quick-pick grids.
BUDGET_CATEGORY_ORDER: list[str] = [
    "🛒 Groceries",
    "🍴Restaurants",
    "🏬 Shopping",
    "⛽ Gas",
    "🎉 Entertainment",
    "🤖 Chat GPT",
    "📺 Netflix",
    "📸 Google One",
    "👜 Amazon Prime",
    "🖥️ Internet",
    "📞 Phone",
    "🎭 YouTube",
    "⚡Electricity",
    "🔥 Natural Gas",
    "💦 Water",
    "🏡 Mortgage",
    "💳 Credit Card Payments",
    "🏎 Car Maintenance",
    "🏎️ Car Insurance",
    "🛠️ Home Maintenance",
    "🛖 Home Improvement",
    "💸 Retirement",
    "🩺 Reoccuring Med.",
    "🚑 Medical Fund",
    "💆‍♀️ Massage",
    "💃 Dance Class",
    "🏊 Swim",
    "🐩 Reoccuring Dog",
    "🔥 Dyndrite",
    "💰 Other Income",
    "💵 Jenna Sales",
    "📩 Internal Transfer",
    "🎈From Savings",
    "❌DUPLICATE",
]
