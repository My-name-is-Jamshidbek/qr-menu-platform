"""QR code rendering.

Each table gets an SVG for one-off reprints and there is a single printable PDF sheet
for the whole room. Both encode `<site>/t/<token>`: the token, never the table number,
so the codes cannot be enumerated.
"""

from io import BytesIO

import segno
from decouple import config
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from apps.tables.models import Table

SVG_SCALE = 8
SVG_BORDER = 2
# Error correction M survives a scuffed sticker without inflating the module count.
ERROR_CORRECTION = "m"

# Sheet geometry, in millimetres.
COLUMNS = 3
ROWS = 4
MARGIN = 15 * mm
CELL_GAP = 6 * mm
CAPTION_HEIGHT = 10 * mm


def site_url() -> str:
    """Public site root the QR codes point at.

    The frontend publishes itself under `NEXT_PUBLIC_SITE_URL`; on a single-origin
    deployment that is also `FRONTEND_URL`, which is the fallback.
    """
    configured = getattr(settings, "NEXT_PUBLIC_SITE_URL", None) or config(
        "NEXT_PUBLIC_SITE_URL", default=""
    )
    return (configured or settings.FRONTEND_URL).rstrip("/")


def scan_url(table: Table) -> str:
    return f"{site_url()}{table.scan_path()}"


def table_qr_svg(table: Table) -> bytes:
    """One table's QR code as a standalone SVG document."""
    buffer = BytesIO()
    segno.make(scan_url(table), error=ERROR_CORRECTION).save(
        buffer, kind="svg", scale=SVG_SCALE, border=SVG_BORDER, xmldecl=True, svgclass=None
    )
    return buffer.getvalue()


def _qr_image(table: Table) -> ImageReader:
    buffer = BytesIO()
    segno.make(scan_url(table), error=ERROR_CORRECTION).save(buffer, kind="png", scale=10, border=1)
    buffer.seek(0)
    return ImageReader(buffer)


def qr_sheet_pdf(tables: list[Table]) -> bytes:
    """A printable A4 sheet, twelve labelled codes per page."""
    buffer = BytesIO()
    page_width, page_height = A4
    document = canvas.Canvas(buffer, pagesize=A4)
    document.setTitle("BOSS KAFE table QR codes")

    cell_width = (page_width - 2 * MARGIN - (COLUMNS - 1) * CELL_GAP) / COLUMNS
    cell_height = (page_height - 2 * MARGIN - (ROWS - 1) * CELL_GAP) / ROWS
    code_size = min(cell_width, cell_height - CAPTION_HEIGHT)
    per_page = COLUMNS * ROWS

    for index, table in enumerate(tables):
        if index and index % per_page == 0:
            document.showPage()

        slot = index % per_page
        column = slot % COLUMNS
        row = slot // COLUMNS

        left = MARGIN + column * (cell_width + CELL_GAP)
        top = page_height - MARGIN - row * (cell_height + CELL_GAP)

        document.drawImage(
            _qr_image(table),
            left + (cell_width - code_size) / 2,
            top - code_size,
            width=code_size,
            height=code_size,
            mask="auto",
        )
        document.setFont("Helvetica-Bold", 12)
        caption = table.label or f"Table {table.number}"
        document.drawCentredString(left + cell_width / 2, top - code_size - 6 * mm, caption)

    document.showPage()
    document.save()
    return buffer.getvalue()
