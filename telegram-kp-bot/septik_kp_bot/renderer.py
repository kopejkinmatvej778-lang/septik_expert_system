from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


BLACK = (16, 24, 21)
GREEN = (0, 70, 51)
GRID = (214, 218, 218)
WHITE = (255, 255, 255)


FONT_CANDIDATES = [
    (
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
    ),
    (
        "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Bold.ttf",
    ),
    (
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
    ),
    (
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    ),
]


def find_fonts(regular: str | None, bold: str | None) -> tuple[str, str]:
    if regular and bold and Path(regular).exists() and Path(bold).exists():
        return regular, bold
    for regular_candidate, bold_candidate in FONT_CANDIDATES:
        if Path(regular_candidate).exists() and Path(bold_candidate).exists():
            return regular_candidate, bold_candidate
    raise RuntimeError("No compatible serif fonts found. Set FONT_REGULAR_PATH and FONT_BOLD_PATH.")


def format_rub(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, str):
        return value
    return f"{int(value):,}".replace(",", " ") + " р."


def font(path_regular: str, path_bold: str, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path_bold if bold else path_regular, size)


def text_width(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> int:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0]


def draw_right(draw: ImageDraw.ImageDraw, x: int, y: float, text: str, fnt: ImageFont.FreeTypeFont, fill=BLACK) -> None:
    box = draw.textbbox((0, 0), text, font=fnt)
    draw.text((x - (box[2] - box[0]), y), text, font=fnt, fill=fill)


def draw_center(draw: ImageDraw.ImageDraw, x: int, y: float, text: str, fnt: ImageFont.FreeTypeFont, fill=BLACK) -> None:
    box = draw.textbbox((0, 0), text, font=fnt)
    draw.text((x - (box[2] - box[0]) / 2, y), text, font=fnt, fill=fill)


def row_y(draw: ImageDraw.ImageDraw, top: float, row_h: float, text: str, fnt: ImageFont.FreeTypeFont) -> float:
    box = draw.textbbox((0, 0), text, font=fnt)
    return top + (row_h - (box[3] - box[1])) / 2 - 1


def redraw_grid(draw: ImageDraw.ImageDraw, x_lines: list[int], top: int, bottom: int, rows: int) -> float:
    rows = max(rows, 1)
    draw.rectangle((x_lines[0], top, x_lines[-1], bottom), fill=WHITE)
    for x in x_lines:
        draw.line((x, top, x, bottom), fill=GRID, width=1)
    row_h = (bottom - top) / rows
    for i in range(rows + 1):
        y = round(top + i * row_h)
        draw.line((x_lines[0], y, x_lines[-1], y), fill=GRID, width=1)
    return row_h


def display_value(row: dict[str, Any], key: str) -> str:
    display_key = f"display_{key}"
    if row.get(display_key):
        return str(row[display_key])
    return format_rub(row.get(key))


def normalize_rows(rows: list[dict[str, Any]]) -> list[tuple[str, str, str, str, str, str]]:
    normalized = []
    for idx, row in enumerate(rows, start=1):
        normalized.append(
            (
                str(row.get("number") or idx),
                str(row.get("name") or ""),
                str(row.get("unit") or ""),
                str(row.get("quantity") or ""),
                display_value(row, "unit_price"),
                display_value(row, "total"),
            )
        )
    return normalized


def draw_rows(
    draw: ImageDraw.ImageDraw,
    rows: list[tuple[str, str, str, str, str, str]],
    top: int,
    row_h: float,
    mode: str,
    fonts: dict[str, ImageFont.FreeTypeFont],
) -> None:
    fnt = fonts["mat"] if mode == "materials" else fonts["work"]
    fnt_small = fonts["mat_small"] if mode == "materials" else fonts["work_small"]
    fnt_tiny = fonts["mat_tiny"] if mode == "materials" else fonts["work_tiny"]
    fnt_bold = fonts["mat_bold"] if mode == "materials" else fonts["work_bold"]

    for idx, row in enumerate(rows):
        y_top = top + idx * row_h
        num, name, unit, qty, price, total = row
        name_font = fnt
        if text_width(draw, name, name_font) > 360:
            name_font = fnt_small
        if text_width(draw, name, name_font) > 360:
            name_font = fnt_tiny
        y = row_y(draw, y_top, row_h, "123", fnt)
        draw_center(draw, 76, y, num, fnt)
        draw.text((113, y), name, font=name_font, fill=BLACK)
        draw_center(draw, 552, y, unit, fnt)
        draw_center(draw, 631, y, qty, fnt)
        draw_right(draw, 818, y, price, fnt)
        draw_right(draw, 943, y, total, fnt_bold)


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_proposal_png(
    payload: dict[str, Any],
    template: Path,
    output: Path,
    font_regular_path: str | None = None,
    font_bold_path: str | None = None,
) -> dict[str, Any]:
    warnings: list[dict[str, Any]] = []
    client = payload.get("client", {})
    materials = normalize_rows(payload.get("materials", []))
    works = normalize_rows(payload.get("works", []))
    totals = payload.get("totals", {})
    font_regular, font_bold = find_fonts(font_regular_path, font_bold_path)

    if len(materials) > 12:
        warnings.append({"type": "needs_layout_review", "section": "materials", "rows": len(materials), "limit": 12})
    if len(works) > 8:
        warnings.append({"type": "needs_layout_review", "section": "works", "rows": len(works), "limit": 8})

    fonts = {
        "field": font(font_regular, font_bold, 18),
        "field_bold": font(font_regular, font_bold, 19, True),
        "mat": font(font_regular, font_bold, 15),
        "mat_small": font(font_regular, font_bold, 14),
        "mat_tiny": font(font_regular, font_bold, 12),
        "mat_bold": font(font_regular, font_bold, 15, True),
        "work": font(font_regular, font_bold, 16),
        "work_small": font(font_regular, font_bold, 15),
        "work_tiny": font(font_regular, font_bold, 13),
        "work_bold": font(font_regular, font_bold, 16, True),
        "total": font(font_regular, font_bold, 18, True),
        "grand": font(font_regular, font_bold, 42, True),
    }

    image = Image.open(template).convert("RGB")
    draw = ImageDraw.Draw(image)

    draw.text((129, 394), str(client.get("name") or "—"), font=fonts["field_bold"], fill=BLACK)
    draw.text((390, 394), str(client.get("address") or "—"), font=fonts["field"], fill=BLACK)
    draw.text((613, 394), str(client.get("phone") or "—"), font=fonts["field"], fill=BLACK)
    draw.text((834, 394), str(client.get("date") or "—"), font=fonts["field"], fill=BLACK)

    x_lines = [52, 100, 487, 586, 676, 834, 969]
    mat_h = redraw_grid(draw, x_lines, 516, 872, len(materials))
    draw_rows(draw, materials, 516, mat_h, "materials", fonts)
    draw_right(draw, 943, 891, format_rub(totals.get("materials")), fonts["total"])

    work_h = redraw_grid(draw, x_lines, 984, 1227, len(works))
    draw_rows(draw, works, 984, work_h, "works", fonts)
    draw_right(draw, 943, 1236, format_rub(totals.get("works")), fonts["total"])

    draw_right(draw, 945, 1286, format_rub(totals.get("grand_total")), fonts["grand"], fill=GREEN)

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, quality=95)
    reopened = Image.open(output)
    return {
        "ok": True,
        "file_type": "proposal_png",
        "local_path": str(output),
        "width": reopened.width,
        "height": reopened.height,
        "sha256": checksum(output),
        "warnings": warnings,
    }
