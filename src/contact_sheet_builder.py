from __future__ import annotations
import logging
import math
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Thumbnail dimensions within the contact sheet
THUMB_W = 160
THUMB_H = 160
LABEL_H = 20
PADDING = 8
BACKGROUND = (30, 30, 30)
LABEL_COLOR = (220, 220, 220)
MISSING_COLOR = (80, 80, 80)


def build_contact_sheet(
    image_dir: Path,
    token_ids: list[int],
    out_dir: Path,
    *,
    columns: int = 10,
    include_pdf: bool = True,
) -> None:
    """
    Lay out all downloaded images into a contact sheet PNG (and optionally PDF).
    Missing images are shown as a grey placeholder.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.error(
            "Pillow is required for contact sheet generation. "
            "Install it with: pip install Pillow"
        )
        return

    cell_w = THUMB_W + PADDING * 2
    cell_h = THUMB_H + LABEL_H + PADDING * 2
    rows = math.ceil(len(token_ids) / columns)

    sheet_w = cell_w * columns
    sheet_h = cell_h * rows
    sheet = Image.new("RGB", (sheet_w, sheet_h), BACKGROUND)
    draw = ImageDraw.Draw(sheet)

    # Attempt to load a font; fall back to default
    font: object
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except OSError:
        try:
            font = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", 12)
        except OSError:
            font = ImageFont.load_default()

    for idx, token_id in enumerate(token_ids):
        col = idx % columns
        row = idx // columns
        x = col * cell_w + PADDING
        y = row * cell_h + PADDING

        # Find the image file (any extension)
        candidates = list(image_dir.glob(f"{token_id}.*")) + list(image_dir.glob(str(token_id)))
        thumb: Optional[Image.Image] = None
        if candidates:
            try:
                img = Image.open(candidates[0]).convert("RGB")
                img.thumbnail((THUMB_W, THUMB_H))
                thumb = img
            except Exception as exc:
                logger.debug("Could not open image for ID %d: %s", token_id, exc)

        if thumb is None:
            # Grey placeholder
            placeholder = Image.new("RGB", (THUMB_W, THUMB_H), MISSING_COLOR)
            thumb = placeholder

        # Center the thumbnail in its cell
        offset_x = x + (THUMB_W - thumb.width) // 2
        offset_y = y + (THUMB_H - thumb.height) // 2
        sheet.paste(thumb, (offset_x, offset_y))

        # Label
        label = str(token_id)
        label_x = x + THUMB_W // 2
        label_y = y + THUMB_H + 4
        draw.text((label_x, label_y), label, fill=LABEL_COLOR, font=font, anchor="mt")  # type: ignore[arg-type]

    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / "contact_sheet.png"
    sheet.save(str(png_path), "PNG")
    logger.info("Wrote contact sheet: %s (%dx%d)", png_path, sheet_w, sheet_h)

    if include_pdf:
        _write_pdf(sheet, out_dir)


def _write_pdf(sheet, out_dir: Path) -> None:
    try:
        from reportlab.lib.pagesizes import A3, landscape
        from reportlab.pdfgen import canvas as rl_canvas
        import io
        from PIL import Image

        pdf_path = out_dir / "contact_sheet.pdf"
        page_w, page_h = landscape(A3)

        c = rl_canvas.Canvas(str(pdf_path), pagesize=(page_w, page_h))

        # Scale the sheet to fit the page
        img_w, img_h = sheet.size
        scale = min(page_w / img_w, page_h / img_h)
        draw_w = img_w * scale
        draw_h = img_h * scale
        draw_x = (page_w - draw_w) / 2
        draw_y = (page_h - draw_h) / 2

        buf = io.BytesIO()
        sheet.save(buf, format="PNG")
        buf.seek(0)
        c.drawImage(
            buf,  # type: ignore[arg-type]
            draw_x, draw_y, width=draw_w, height=draw_h,
        )
        c.save()
        logger.info("Wrote PDF contact sheet: %s", pdf_path)
    except ImportError:
        logger.warning(
            "reportlab not installed – skipping PDF export. "
            "Install with: pip install reportlab"
        )
    except Exception as exc:
        logger.warning("PDF generation failed: %s", exc)
