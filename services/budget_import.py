"""
Parse Google Sheets HTML exports into normalized transaction records.

Reads the <table class="waffle"> and detects columns by header row
("Transaction Date", "Transaction ID", …) so both compact exports
(Transactions.html) and wide exports (All 2026 Transactions.html) work.

Monthly tabs (January.html, April.html, …) are budget layouts, not ledgers;
they are not imported — use only transaction export files.
"""

import hashlib
import os
import re
from bs4 import BeautifulSoup

from services.budget_dedupe import compute_fingerprint

# Only these files are transaction ledgers; month/template HTML is skipped.
_TRANSACTION_HTML_NAMES = frozenset(
    {
        "transactions.html",
        "all 2026 transactions.html",
    }
)


def _normalize_header(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _parse_header_map(cell_texts: list[str]) -> dict[str, int] | None:
    """
    Map logical field -> column index using the header row.
    Returns None if this row does not look like a transaction header.
    """
    norm = [_normalize_header(t) for t in cell_texts]
    if "transaction date" not in norm or "transaction id" not in norm:
        return None

    def first_col(*aliases: str) -> int | None:
        for a in aliases:
            try:
                return norm.index(a)
            except ValueError:
                continue
        return None

    date_i = first_col("transaction date")
    tid_i = first_col("transaction id")
    if date_i is None or tid_i is None:
        return None

    m: dict[str, int] = {
        "date": date_i,
        "transaction_id": tid_i,
    }
    optional = {
        "category_display": ("new category",),
        "description": ("description",),
        "credit": ("credit",),
        "debit": ("debit",),
        "category_api": ("category",),
        "account": ("bank/card", "account"),
    }
    for key, aliases in optional.items():
        idx = first_col(*aliases)
        if idx is not None:
            m[key] = idx
    return m


def _row_cell_texts(row) -> list[str]:
    return [
        re.sub(r"\s+", " ", c.get_text(separator=" ", strip=True)).strip()
        for c in row.find_all("td")
    ]


def _looks_like_date(s: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", (s or "").strip()))


def parse_sheets_html(filepath: str) -> list[dict]:
    """Parse a Google Sheets HTML export and return normalized transactions."""
    with open(filepath, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="waffle")
    if not table:
        return []

    rows = table.find_all("tr")
    col_map: dict[str, int] | None = None
    transactions: list[dict] = []

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 6:
            continue

        texts = _row_cell_texts(row)
        if col_map is None:
            parsed = _parse_header_map(texts)
            if parsed:
                col_map = parsed
                continue
            # No header row yet — try legacy layouts (older exports).
            tx = _try_legacy_row(texts, filepath)
            if tx:
                transactions.append(tx)
            continue

        date_str = texts[col_map["date"]].strip() if col_map["date"] < len(texts) else ""
        if not _looks_like_date(date_str):
            continue
        if _normalize_header(date_str) == "transaction date":
            continue

        tid_i = col_map["transaction_id"]
        tx_id_raw = texts[tid_i].strip() if tid_i < len(texts) else ""
        if not tx_id_raw or tx_id_raw == "#N/A":
            continue

        ci = col_map.get("credit")
        di = col_map.get("debit")
        credit = _parse_number(texts[ci] if ci is not None and ci < len(texts) else "")
        debit = _parse_number(texts[di] if di is not None and di < len(texts) else "")
        amount = credit - debit

        cat_disp_i = col_map.get("category_display")
        api_i = col_map.get("category_api")
        desc_i = col_map.get("description")
        acct_i = col_map.get("account")

        category_display = (
            texts[cat_disp_i].strip()
            if cat_disp_i is not None and cat_disp_i < len(texts)
            else ""
        )
        category_api = (
            texts[api_i].strip() if api_i is not None and api_i < len(texts) else ""
        )
        description = (
            texts[desc_i].strip() if desc_i is not None and desc_i < len(texts) else ""
        )
        account = (
            texts[acct_i].strip() if acct_i is not None and acct_i < len(texts) else ""
        )

        stable_id = _make_stable_id(tx_id_raw, date_str, description, amount)
        fingerprint = compute_fingerprint(date_str, description, amount, tx_id_raw)

        transactions.append(
            {
                "id": stable_id,
                "transaction_id": tx_id_raw,
                "date": date_str,
                "description": description,
                "category": category_api or "OTHER",
                "category_display": category_display
                or _humanize_category(category_api),
                "category_override": None,
                "credit": round(credit, 2),
                "debit": round(debit, 2),
                "amount": round(amount, 2),
                "account": account,
                "source": "bootstrap_html",
                "source_file": os.path.basename(filepath),
                "fingerprint": fingerprint,
                "is_duplicate": False,
                "duplicate_of": None,
            }
        )

    return transactions


def _try_legacy_row(cell_texts: list[str], filepath: str) -> dict | None:
    """
    Older single-sheet layout: leading empty col, date in col 1, tx id col 7.
    """
    if len(cell_texts) < 8:
        return None
    date_str = cell_texts[1].strip()
    if not _looks_like_date(date_str):
        return None
    tx_id_raw = cell_texts[7].strip() if len(cell_texts) > 7 else ""
    if not tx_id_raw or tx_id_raw == "#N/A":
        return None

    credit = _parse_number(cell_texts[4] if len(cell_texts) > 4 else "")
    debit = _parse_number(cell_texts[5] if len(cell_texts) > 5 else "")
    amount = credit - debit
    category_display = cell_texts[2].strip() if len(cell_texts) > 2 else ""
    category_api = cell_texts[6].strip() if len(cell_texts) > 6 else ""
    description = cell_texts[3].strip() if len(cell_texts) > 3 else ""
    account = cell_texts[8].strip() if len(cell_texts) > 8 else ""

    stable_id = _make_stable_id(tx_id_raw, date_str, description, amount)
    fingerprint = compute_fingerprint(date_str, description, amount, tx_id_raw)
    return {
        "id": stable_id,
        "transaction_id": tx_id_raw,
        "date": date_str,
        "description": description,
        "category": category_api or "OTHER",
        "category_display": category_display or _humanize_category(category_api),
        "category_override": None,
        "credit": round(credit, 2),
        "debit": round(debit, 2),
        "amount": round(amount, 2),
        "account": account,
        "source": "bootstrap_html",
        "source_file": os.path.basename(filepath),
        "fingerprint": fingerprint,
        "is_duplicate": False,
        "duplicate_of": None,
    }


def import_from_directory(dir_path: str) -> list[dict]:
    """Import transactions from transaction-export HTML files only."""
    all_txns: list[dict] = []
    if not os.path.isdir(dir_path):
        return all_txns

    for fname in sorted(os.listdir(dir_path)):
        low = fname.lower()
        if not low.endswith(".html"):
            continue
        if low not in _TRANSACTION_HTML_NAMES:
            continue
        fpath = os.path.join(dir_path, fname)
        all_txns.extend(parse_sheets_html(fpath))

    return all_txns


def _parse_number(s: str) -> float:
    s = (s or "").strip().replace(",", "").replace("$", "")
    if not s or s == "#N/A":
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _make_stable_id(tx_id: str, date: str, desc: str, amount: float) -> str:
    raw = f"{tx_id}|{date}|{desc}|{amount}"
    return "tx_" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def _humanize_category(api_cat: str) -> str:
    if not api_cat:
        return "Other"
    return api_cat.replace("_", " ").title()
