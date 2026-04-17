"""
Bank-agnostic CSV importer for the Budget tab.

Works as a fallback for any bank/credit-card export, using a forgiving
column detector that matches common header names used by Chase, Bank of
America, Amex, Discover, Capital One, Mint, Ally, Wells Fargo, etc.

Usage:
    records = parse_csv_text(raw_text, source_name="chase_aug.csv")
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime

from services.budget_dedupe import compute_fingerprint


# Header aliases (lowercased, non-alphanumeric stripped)
_DATE_HEADERS = {
    "date", "transactiondate", "postingdate", "posteddate", "postdate",
    "tradedate", "transdate",
}
_DESC_HEADERS = {
    "description", "desc", "memo", "details", "payee", "merchant", "name",
    "originaldescription", "merchantname",
}
_AMOUNT_HEADERS = {"amount", "value", "transactionamount"}
_DEBIT_HEADERS = {"debit", "withdrawal", "withdrawals", "moneyout", "expense", "outflow"}
_CREDIT_HEADERS = {"credit", "deposit", "deposits", "moneyin", "income", "inflow"}
_CATEGORY_HEADERS = {"category", "categories", "type", "transactiontype"}
_ACCOUNT_HEADERS = {"account", "accountname", "cardmember", "card"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").strip().lower())


def _find(headers_normalized: list[str], aliases: set[str]) -> int | None:
    for i, h in enumerate(headers_normalized):
        if h in aliases:
            return i
    return None


def _to_float(s: str) -> float:
    if s is None:
        return 0.0
    s = str(s).strip()
    if not s:
        return 0.0
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    s = s.replace(",", "").replace("$", "").replace("USD", "").strip()
    if s.startswith("-"):
        neg = True
        s = s[1:]
    try:
        v = float(s)
    except ValueError:
        return 0.0
    return -v if neg else v


_DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%m/%d/%y",
    "%d/%m/%Y",
    "%b %d, %Y",
    "%d %b %Y",
    "%B %d, %Y",
]


def _normalize_date(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", s)
    if m:
        return m.group(1)
    return s


def parse_csv_text(text: str, source_name: str = "upload.csv") -> list[dict]:
    """Parse a CSV string into transaction records. Returns [] if it can't be understood."""
    if not text:
        return []

    # Strip BOM
    if text.startswith("\ufeff"):
        text = text[1:]

    # Use Sniffer to guess dialect; fall back to comma.
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel

    reader = csv.reader(io.StringIO(text), dialect=dialect)
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        return []

    # Find the header row: the first row where we can locate a date column.
    header_row_idx = None
    for i, row in enumerate(rows[:10]):
        normed = [_norm(c) for c in row]
        if _find(normed, _DATE_HEADERS) is not None and (
            _find(normed, _DESC_HEADERS) is not None
            or _find(normed, _AMOUNT_HEADERS) is not None
            or _find(normed, _DEBIT_HEADERS) is not None
        ):
            header_row_idx = i
            break
    if header_row_idx is None:
        return []

    headers = rows[header_row_idx]
    normed = [_norm(h) for h in headers]

    c_date = _find(normed, _DATE_HEADERS)
    c_desc = _find(normed, _DESC_HEADERS)
    c_amt = _find(normed, _AMOUNT_HEADERS)
    c_debit = _find(normed, _DEBIT_HEADERS)
    c_credit = _find(normed, _CREDIT_HEADERS)
    c_cat = _find(normed, _CATEGORY_HEADERS)
    c_acct = _find(normed, _ACCOUNT_HEADERS)

    out: list[dict] = []
    for row in rows[header_row_idx + 1 :]:
        if not row or c_date is None or c_date >= len(row):
            continue
        date_str = _normalize_date(row[c_date])
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            continue

        desc = (row[c_desc].strip() if c_desc is not None and c_desc < len(row) else "") or "(transaction)"
        cat_display = (row[c_cat].strip() if c_cat is not None and c_cat < len(row) else "")
        acct = (row[c_acct].strip() if c_acct is not None and c_acct < len(row) else "")

        debit = _to_float(row[c_debit]) if c_debit is not None and c_debit < len(row) else 0.0
        credit = _to_float(row[c_credit]) if c_credit is not None and c_credit < len(row) else 0.0
        amt = 0.0
        if c_amt is not None and c_amt < len(row):
            amt = _to_float(row[c_amt])

        if credit or debit:
            internal_amount = credit - debit
        else:
            internal_amount = amt

        tx_id_raw = f"csv|{date_str}|{desc}|{internal_amount:.2f}|{source_name}"
        fingerprint = compute_fingerprint(date_str, desc, internal_amount, tx_id_raw)
        stable_id = "tx_csv_" + fingerprint[:16]

        out.append(
            {
                "id": stable_id,
                "transaction_id": tx_id_raw,
                "date": date_str,
                "description": desc,
                "category": "OTHER",
                "category_display": cat_display or "",
                "category_override": None,
                "credit": round(max(internal_amount, 0), 2) if not (credit or debit) else round(credit, 2),
                "debit": round(max(-internal_amount, 0), 2) if not (credit or debit) else round(debit, 2),
                "amount": round(internal_amount, 2),
                "account": acct,
                "source": "csv",
                "source_file": source_name,
                "fingerprint": fingerprint,
                "is_duplicate": False,
                "duplicate_of": None,
            }
        )
    return out
