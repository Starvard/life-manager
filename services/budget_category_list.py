"""
Canonical ordered list of budget category display names (emoji + label).

Used by ``budget_categorizer.BUDGET_CATEGORIES`` so the picker and reports stay
consistent. Edit this file to add/reorder categories app-wide.
"""

from __future__ import annotations

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
    "⚡Electricity",
    "🔥 Natural Gas",
    "💦 Water",
    "🏡 Mortgage",
    "💳 Credit Card Payments",
    "🏎 Car Maintenance",
    "🏎️ Car Insurance",
    "🛠️ Home Maintenance",
    "🛖 Home Improvement",
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
