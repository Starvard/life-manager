"""
Generates daily 5x3 inch baby tracking notecards from saved card state.

Pages are 3x5 portrait; content is rotated 90 degrees so it reads
landscape when you hold the printed card horizontally.

Can render both blank templates and filled cards from the card store.
"""

import os
from datetime import date, timedelta

from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen.canvas import Canvas

from config import CARDS_DIR

CONTENT_W = 5 * inch
CONTENT_H = 3 * inch

PAGE_W = 3 * inch
PAGE_H = 5 * inch

CARD_PAD_X = 0.10 * inch
CARD_PAD_Y = 0.06 * inch
HEADER_H = 0.24 * inch

HEADER_BG = HexColor("#553C9A")
GRID_COLOR = HexColor("#CBD5E0")
LABEL_COLOR = HexColor("#1A202C")
MUTED_COLOR = HexColor("#718096")
SECTION_BG = HexColor("#F7FAFC")
FILLED_COLOR = HexColor("#553C9A")

TRACK_ORDER = [
    "nursing_l", "nursing_r", "bottle",
    "wet_diaper", "dirty_diaper",
    "rowan_sleep", "jenna_sleep",
    "tylenol", "ibuprofen", "notes",
]


def _draw_baby_content(c: Canvas, card: dict):
    """Draw baby card content from stored card data."""
    ix = CARD_PAD_X
    iy = CARD_PAD_Y
    iw = CONTENT_W - 2 * CARD_PAD_X
    ih = CONTENT_H - 2 * CARD_PAD_Y

    header_y = iy + ih - HEADER_H
    c.setFillColor(HEADER_BG)
    c.roundRect(ix, header_y, iw, HEADER_H, 3, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(ix + 6, header_y + 7,
                 f"BABY {card.get('baby_name', 'Baby').upper()}")
    c.setFont("Helvetica", 7)
    c.drawRightString(ix + iw - 6, header_y + 8, card.get("date", ""))

    tracks = card.get("tracks", {})
    ordered = [k for k in TRACK_ORDER if k in tracks]
    for k in tracks:
        if k not in ordered:
            ordered.append(k)

    if not ordered:
        return

    label_w = 1.0 * inch
    grid_x = ix + label_w
    grid_w = iw - label_w
    available_h = header_y - iy - 2
    row_h = available_h / len(ordered)

    for ri, key in enumerate(ordered):
        track = tracks[key]
        row_top = header_y - ri * row_h
        row_bot = row_top - row_h
        row_mid = (row_top + row_bot) / 2

        if ri % 2 == 0:
            c.setFillColor(SECTION_BG)
            c.rect(ix, row_bot, iw, row_h, fill=1, stroke=0)

        c.setStrokeColor(GRID_COLOR)
        c.setLineWidth(0.3)
        c.line(ix, row_bot, ix + iw, row_bot)

        label = track.get("label", key)
        font_size = 6.5 if len(label) <= 14 else 5.5
        c.setFont("Helvetica-Bold", font_size)
        c.setFillColor(LABEL_COLOR)
        c.drawString(ix + 3, row_mid - 2, label)

        hint = track.get("hint", "")
        if hint:
            c.setFont("Helvetica", 4.5)
            c.setFillColor(MUTED_COLOR)
            c.drawString(ix + 3, row_mid - 7.5, hint)

        c.setStrokeColor(GRID_COLOR)
        c.setLineWidth(0.3)
        c.line(grid_x, row_bot, grid_x, row_top)

        t = track.get("type", "")

        if t == "tally":
            count = track.get("count", 0)
            if count > 0:
                c.setFont("Helvetica-Bold", 8)
                c.setFillColor(LABEL_COLOR)
                c.drawString(grid_x + 4, row_mid - 3, str(count))

        elif t == "blocks":
            squares = track.get("squares", [False] * 48)
            sq_w = grid_w / 48
            for si, filled in enumerate(squares):
                sx = grid_x + si * sq_w
                if filled:
                    c.setFillColor(FILLED_COLOR)
                    c.rect(sx + 0.5, row_bot + 2, sq_w - 1, row_h - 4,
                           fill=1, stroke=0)
                else:
                    c.setStrokeColor(HexColor("#E8ECF0"))
                    c.setLineWidth(0.15)
                    c.rect(sx + 0.5, row_bot + 2, sq_w - 1, row_h - 4,
                           fill=0, stroke=1)

            for hi in range(0, 24, 6):
                hx = grid_x + (hi * 2) * sq_w
                c.setStrokeColor(GRID_COLOR)
                c.setLineWidth(0.3)
                c.line(hx, row_bot, hx, row_top)
                labels = {0: "12a", 6: "6a", 12: "12p", 18: "6p"}
                if hi in labels:
                    c.setFont("Helvetica", 3.5)
                    c.setFillColor(MUTED_COLOR)
                    c.drawCentredString(hx + sq_w * 6, row_top - 3,
                                       labels[hi])

        elif t == "notes":
            text = track.get("text", "")
            if text:
                c.setFont("Helvetica", 5.5)
                c.setFillColor(LABEL_COLOR)
                c.drawString(grid_x + 3, row_mid - 2, text[:60])

    c.setStrokeColor(GRID_COLOR)
    c.setLineWidth(0.5)
    c.rect(ix, iy, iw, ih, fill=0, stroke=1)


def generate_baby_card_pdf(card: dict) -> str:
    """Generate a single-day baby card PDF from stored card data."""
    os.makedirs(CARDS_DIR, exist_ok=True)
    card_date = card.get("date", "unknown")
    baby_name = card.get("baby_name", "baby").lower()
    filename = f"baby-{baby_name}-{card_date}.pdf"
    filepath = os.path.join(CARDS_DIR, filename)

    c = Canvas(filepath, pagesize=(PAGE_W, PAGE_H))
    c.setTitle(f"Baby Tracking - {card_date}")

    c.saveState()
    c.translate(0, PAGE_H)
    c.rotate(-90)
    _draw_baby_content(c, card)
    c.restoreState()

    c.save()
    return filepath


def generate_baby_cards_pdf(start_date: date, num_days: int = 7,
                            baby_name: str = "Baby") -> str:
    """Generate multi-day blank baby cards (legacy support)."""
    from services.card_store import get_baby_card

    os.makedirs(CARDS_DIR, exist_ok=True)
    end_date = start_date + timedelta(days=num_days - 1)
    filename = f"baby-{baby_name.lower()}-{start_date.isoformat()}-to-{end_date.isoformat()}.pdf"
    filepath = os.path.join(CARDS_DIR, filename)

    cv = Canvas(filepath, pagesize=(PAGE_W, PAGE_H))
    cv.setTitle(f"Baby Tracking - {baby_name}")

    for day_offset in range(num_days):
        card_date = start_date + timedelta(days=day_offset)
        if day_offset > 0:
            cv.showPage()
        card = get_baby_card(card_date.isoformat())
        cv.saveState()
        cv.translate(0, PAGE_H)
        cv.rotate(-90)
        _draw_baby_content(cv, card)
        cv.restoreState()

    cv.save()
    return filepath
