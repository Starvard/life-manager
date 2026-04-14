"""
Parse Google Sheets *monthly tab* HTML exports (e.g. April.html) into a structured
overview: totals snapshot, category blocks, bill payments, weekly grid, ledger line.

Layout matches the user's 15-column waffle export; anchors on header text.
"""

from __future__ import annotations

import os
import re
from typing import Any

from bs4 import BeautifulSoup


def _row_texts(row) -> list[str]:
    return [
        re.sub(r"\s+", " ", c.get_text(separator=" ", strip=True)).strip()
        for c in row.find_all("td")
    ]


def _parse_money(s: str) -> float | None:
    if s is None:
        return None
    t = str(s).strip()
    if not t or t in ("-", "—", "#N/A"):
        return None
    t = t.replace(",", "").replace("$", "")
    neg = False
    if t.startswith("(") and t.endswith(")"):
        neg = True
        t = t[1:-1].strip()
    if t.startswith("-"):
        neg = not neg
        t = t[1:].strip()
    if not t:
        return None
    try:
        v = float(t)
        return -v if neg else v
    except ValueError:
        return None


_MONTH_KEY = re.compile(r"^\d{4}-\d{2}$")
_WEEK_COL = re.compile(r"^\d{2}/\d{1,2}\s*-\s*\d{2}/\d{1,2}")


def parse_monthly_budget_html(filepath: str) -> dict[str, Any] | None:
    """
    Return overview dict or None if file does not look like a monthly budget sheet.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="waffle")
    if not table:
        return None

    rows = [_row_texts(r) for r in table.find_all("tr")]
    if not rows:
        return None

    month = _extract_month_key(rows)
    if not month:
        return None

    overview: dict[str, Any] = {
        "month": month,
        "source_file": os.path.basename(filepath),
        "snapshot": _extract_snapshot(rows),
        "ledger": _extract_ledger(rows),
        "weekly": _extract_weekly(rows),
        "bill_payments": _extract_bill_payments(rows),
        "panels": _extract_panels(rows),
    }
    return overview


def _extract_month_key(rows: list[list[str]]) -> str | None:
    for t in rows:
        if len(t) > 2 and t[1].strip().lower() == "month" and _MONTH_KEY.match(t[2].strip()):
            return t[2].strip()
    return None


def _extract_snapshot(rows: list[list[str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, t in enumerate(rows):
        if (
            len(t) > 5
            and t[3] == "Allocated"
            and t[4] == "Actual"
            and t[5] == "Remaining"
        ):
            for j in range(i + 1, min(i + 10, len(rows))):
                r = rows[j]
                if len(r) < 6:
                    continue
                label = (r[2] or "").strip()
                if not label:
                    continue
                if label == "Totals":
                    break
                if label in ("Income", "Spending", "Saving", "In - Out"):
                    out.append(
                        {
                            "label": label,
                            "allocated": _parse_money(r[3]),
                            "actual": _parse_money(r[4]),
                            "remaining": _parse_money(r[5])
                            if r[5] and r[5].strip() not in ("-", "—", "")
                            else None,
                        }
                    )
            break
    return out


def _extract_ledger(rows: list[list[str]]) -> dict[str, float | None]:
    for i, t in enumerate(rows):
        if len(t) > 5 and t[3] == "Debit" and t[4] == "Credit" and t[5] == "Delta":
            if i + 1 < len(rows):
                r = rows[i + 1]
                if len(r) > 5 and r[2].strip() == "Transactions":
                    return {
                        "debit": _parse_money(r[3]),
                        "credit": _parse_money(r[4]),
                        "delta": _parse_money(r[5]),
                    }
            break
    return {"debit": None, "credit": None, "delta": None}


def _extract_weekly(rows: list[list[str]]) -> dict[str, Any]:
    """
    Header row has consecutive week range labels starting at column 2.
    Data rows use the same start column for the category name, amounts follow.
    """
    for i, t in enumerate(rows):
        w0 = None
        for idx, c in enumerate(t):
            if _WEEK_COL.match((c or "").strip()):
                w0 = idx
                break
        if w0 is None:
            continue
        cols: list[str] = []
        k = w0
        while k < len(t) and _WEEK_COL.match((t[k] or "").strip()):
            cols.append((t[k] or "").strip())
            k += 1
        if len(cols) < 2:
            continue
        # Header has weeks at w0..; data rows put the label one column left of w0.
        name_col = w0 - 1
        if name_col < 0:
            continue
        data_rows: list[dict[str, Any]] = []
        for j in range(i + 1, min(i + 12, len(rows))):
            r = rows[j]
            if len(r) < w0 + len(cols):
                break
            name = (r[name_col] or "").strip()
            if not name or name.lower() == "totals":
                break
            cells = []
            for c in range(len(cols)):
                ci = w0 + c
                cells.append(_parse_money(r[ci]) if ci < len(r) else None)
            data_rows.append({"name": name, "amounts": cells})
        return {"columns": cols, "rows": data_rows}
    return {"columns": [], "rows": []}


def _extract_bill_payments(rows: list[list[str]]) -> list[dict[str, Any]]:
    start = None
    for i, t in enumerate(rows):
        if len(t) > 9 and t[9].strip() == "Bill Payments":
            start = i + 1
            break
    if start is None:
        return []

    items: list[dict[str, Any]] = []
    for j in range(start, min(start + 25, len(rows))):
        r = rows[j]
        if len(r) < 11:
            continue
        left = (r[9] or "").strip()
        if left.lower().startswith("total"):
            break
        if not left:
            continue
        amt = _parse_money(r[10]) if len(r) > 10 else None
        items.append({"name": left, "amount": amt})
    return items


def _extract_panels(rows: list[list[str]]) -> dict[str, Any]:
    """
    First budget band: Income (cols 2–4) + Bills (6–8) + Savings (9–12), rows 5–10.
    Food & Subscriptions band ~rows 14–18.
    Personal & Misc ~rows 22–26.
    """
    panels: dict[str, Any] = {
        "income": [],
        "bills": [],
        "savings": [],
        "food_gas": [],
        "subscriptions": [],
        "personal": [],
        "misc": [],
    }

    # Income + Bills + Savings (rows after header row 4)
    for j in range(5, 11):
        if j >= len(rows):
            break
        r = rows[j]
        if len(r) < 9:
            continue
        if (r[1] or "").strip().lower().startswith("totals"):
            break
        if (r[1] or "").strip():
            panels["income"].append(
                {
                    "name": r[1].strip(),
                    "allocated": _parse_money(r[2]),
                    "received": _parse_money(r[3]),
                }
            )
        if (r[5] or "").strip():
            panels["bills"].append(
                {
                    "name": r[5].strip(),
                    "allocated": _parse_money(r[6]),
                    "remaining": _parse_money(r[7]),
                }
            )
    for j in range(5, 22):
        if j >= len(rows):
            break
        r = rows[j]
        if len(r) < 13:
            continue
        sname = (r[9] or "").strip()
        if not sname:
            continue
        if sname.lower().startswith("total"):
            break
        panels["savings"].append(
            {
                "name": sname,
                "allocated": _parse_money(r[10]),
                "send_to_bank": _parse_money(r[11]),
                "in_bank": _parse_money(r[12]) if len(r) > 12 else None,
            }
        )

    # Food & gas + Subscriptions
    for j in range(14, 20):
        if j >= len(rows):
            break
        r = rows[j]
        if len(r) < 8:
            continue
        r1 = (r[1] or "").strip()
        if r1 and r1 not in ("Allocated", "Food & Gas") and not r1.lower().startswith(
            "totals"
        ):
            panels["food_gas"].append(
                {
                    "name": r1,
                    "allocated": _parse_money(r[2]),
                    "remaining": _parse_money(r[3]),
                }
            )
        if (r[5] or "").strip():
            panels["subscriptions"].append(
                {
                    "name": r[5].strip(),
                    "allocated": _parse_money(r[6]),
                    "remaining": _parse_money(r[7]),
                }
            )

    # Personal + Misc
    for j in range(22, 30):
        if j >= len(rows):
            break
        r = rows[j]
        if len(r) < 8:
            continue
        p1 = (r[1] or "").strip()
        if p1 and p1 not in ("Allocated", "Personal Care") and not p1.lower().startswith(
            "totals"
        ):
            panels["personal"].append(
                {
                    "name": p1,
                    "allocated": _parse_money(r[2]),
                    "remaining": _parse_money(r[3]),
                }
            )
        if (r[5] or "").strip():
            panels["misc"].append(
                {
                    "name": r[5].strip(),
                    "allocated": _parse_money(r[6]),
                    "remaining": _parse_money(r[7]),
                }
            )

    return panels


def import_all_monthly_overviews(exports_dir: str) -> dict[str, dict[str, Any]]:
    """Scan directory; parse any HTML that contains a Month / YYYY-MM row."""
    out: dict[str, dict[str, Any]] = {}
    if not os.path.isdir(exports_dir):
        return out
    for fname in sorted(os.listdir(exports_dir)):
        if not fname.lower().endswith(".html"):
            continue
        # Skip pure transaction ledgers (handled elsewhere)
        if fname.lower() in ("transactions.html", "all 2026 transactions.html"):
            continue
        if fname.lower() == "2026 template.html":
            continue
        fpath = os.path.join(exports_dir, fname)
        try:
            parsed = parse_monthly_budget_html(fpath)
        except OSError:
            continue
        if parsed and parsed.get("month"):
            out[parsed["month"]] = parsed
    return out
