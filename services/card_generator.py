"""
Generates print-ready PDFs of 5x3 inch routine notecards.

Each area gets its own page. The PDF page is 3x5 (portrait) so printers
handle it without issues. The content is drawn rotated 90 degrees so it
reads landscape when you hold the card horizontally.
"""

import math
import os
from datetime import date

from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen.canvas import Canvas

from config import CARDS_DIR

CONTENT_W = 5 * inch
CONTENT_H = 3 * inch

PAGE_W = 3 * inch
PAGE_H = 5 * inch

CARD_PAD_X = 0.10 * inch
CARD_PAD_Y = 0.08 * inch
HEADER_H = 0.26 * inch
COL_HEADER_H = 0.20 * inch
TASK_NAME_W = 1.45 * inch

DOT_RADIUS = 2.0
DOT_COLOR = HexColor("#333333")
GRID_COLOR = HexColor("#CCCCCC")
HEADER_BG = HexColor("#2D3748")
LABEL_COLOR = HexColor("#1A202C")
MUTED_COLOR = HexColor("#A0AEC0")

DAYS = ["M", "T", "W", "Th", "F", "Sa", "Su"]


def _draw_card_content(c: Canvas, area_plan: dict):
    """Draw card content in a 5x3 coordinate space (before rotation)."""
    tasks = area_plan["tasks"]
    area_name = area_plan["name"]
    week_start = area_plan["week_start"]

    ix = CARD_PAD_X
    iy = CARD_PAD_Y
    iw = CONTENT_W - 2 * CARD_PAD_X
    ih = CONTENT_H - 2 * CARD_PAD_Y

    header_y = iy + ih - HEADER_H
    c.setFillColor(HEADER_BG)
    c.roundRect(ix, header_y, iw, HEADER_H, 3, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(ix + 6, header_y + 8, area_name.upper())
    c.setFont("Helvetica", 7)
    c.drawRightString(ix + iw - 6, header_y + 9, f"Week of {week_start}")

    col_header_y = header_y - COL_HEADER_H
    day_col_w = (iw - TASK_NAME_W) / 7

    c.setFont("Helvetica-Bold", 6.5)
    c.setFillColor(HexColor("#4A5568"))
    for di, day in enumerate(DAYS):
        dx = ix + TASK_NAME_W + di * day_col_w + day_col_w / 2
        c.drawCentredString(dx, col_header_y + 6, day)

    line_y = col_header_y + 1
    c.setStrokeColor(GRID_COLOR)
    c.setLineWidth(0.4)
    c.line(ix, line_y, ix + iw, line_y)

    if not tasks:
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColor(MUTED_COLOR)
        c.drawCentredString(ix + iw / 2, col_header_y - 20, "No tasks configured")
        return

    available_h = col_header_y - iy
    row_h = min(available_h / max(len(tasks), 1), 0.22 * inch)

    for ti, task in enumerate(tasks):
        row_top = col_header_y - ti * row_h
        row_mid = row_top - row_h / 2

        if ti % 2 == 0:
            c.setFillColor(HexColor("#F7FAFC"))
            c.rect(ix, row_top - row_h, iw, row_h, fill=1, stroke=0)

        c.setStrokeColor(HexColor("#E2E8F0"))
        c.setLineWidth(0.2)
        c.line(ix, row_top - row_h, ix + iw, row_top - row_h)

        name = task["name"]
        has_any_dots = any(d > 0 for d in task["dots"])
        font_size = 7
        if len(name) > 20:
            font_size = 6
        if len(name) > 26:
            font_size = 5.5

        c.setFont("Helvetica", font_size)
        c.setFillColor(LABEL_COLOR if has_any_dots else MUTED_COLOR)
        c.drawString(ix + 4, row_mid - 2.5, name)

        for di in range(7):
            n_dots = task["dots"][di]
            if n_dots <= 0:
                continue
            cx = ix + TASK_NAME_W + di * day_col_w + day_col_w / 2
            _draw_dots_horizontal(c, cx, row_mid, n_dots, day_col_w)


def _draw_dots_horizontal(c: Canvas, cx: float, cy: float, count: int, cell_w: float):
    c.setFillColor(DOT_COLOR)

    if count == 1:
        c.circle(cx, cy, DOT_RADIUS, fill=1, stroke=0)
        return

    usable = cell_w - 6
    spacing = min(DOT_RADIUS * 3.5, usable / max(count - 1, 1))
    total_w = (count - 1) * spacing
    start_x = cx - total_w / 2

    for i in range(count):
        c.circle(start_x + i * spacing, cy, DOT_RADIUS, fill=1, stroke=0)


def generate_cards_pdf(area_plans: list[dict], week_key: str) -> str:
    """
    Generate a PDF with one page per area card.
    Pages are 3x5 portrait; content is rotated 90 degrees so it reads
    landscape when you hold the printed card horizontally.
    """
    os.makedirs(CARDS_DIR, exist_ok=True)
    filepath = os.path.join(CARDS_DIR, f"{week_key}.pdf")

    c = Canvas(filepath, pagesize=(PAGE_W, PAGE_H))
    c.setTitle(f"Routine Cards - {week_key}")

    first = True
    for plan in area_plans:
        if not plan["tasks"]:
            continue
        if not first:
            c.showPage()
        first = False

        c.saveState()
        c.translate(0, PAGE_H)
        c.rotate(-90)
        _draw_card_content(c, plan)
        c.restoreState()

    c.save()
    return filepath
