#!/usr/bin/env python3
"""Render the expansion-method preview without generating dataset rows."""

from __future__ import annotations

import argparse
import io
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from PIL import Image, ImageDraw, ImageFont, ImageOps

from _shared import LEVELS, ReleaseError


WIDTH = 1780
MARGIN = 34
CARD_WIDTH = 400
CARD_HEIGHT = 248
CARD_GAP = 22
BACKGROUND = "#f3f4f6"
CARD = "#ffffff"
INK = "#12151a"
MUTED = "#5f6772"
BORDER = "#c7ccd3"
BLUE = "#2f67d8"
GREEN = "#217a4a"
AMBER = "#a35f00"
PURPLE = "#7651c9"


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    del bold
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _rows(root: Path) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for level in LEVELS:
        matches = sorted((root / "data" / level).glob("train-*.parquet"))
        if len(matches) != 1:
            raise ReleaseError(f"expected one {level} Parquet shard")
        table = pq.read_table(
            matches[0],
            columns=[
                "id",
                "label",
                "grammar_id",
                "variation_role",
                "image",
                "target_image",
            ],
        )
        for row in table.to_pylist():
            found[str(row["id"])] = row
    return found


def _payload(row: dict[str, Any], field: str = "image") -> bytes:
    value = row[field]
    if not isinstance(value, dict) or not value.get("bytes"):
        raise ReleaseError(f"{row['id']}: missing {field} bytes")
    return bytes(value["bytes"])


def _fit(payload: bytes, size: tuple[int, int]) -> Image.Image:
    with Image.open(io.BytesIO(payload)) as opened:
        image = opened.convert("RGB")
    image = ImageOps.contain(image, size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "white")
    canvas.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
    return canvas


def _paper_variant(payload: bytes, size: tuple[int, int]) -> Image.Image:
    fitted = _fit(payload, (size[0] - 44, size[1] - 34))
    page = Image.new("RGB", size, "#f8f5ed")
    page.paste(fitted, (22, 24))
    draw = ImageDraw.Draw(page)
    draw.text((22, 6), "Fig. 2a · device geometry", fill="#6d6a63", font=_font(11))
    draw.rectangle((12, 14, size[0] - 12, size[1] - 10), outline="#d8d2c5")
    return page


def _ellipsize(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    width: int,
) -> str:
    if draw.textbbox((0, 0), text, font=font)[2] <= width:
        return text
    suffix = "..."
    value = text
    while value and draw.textbbox((0, 0), value + suffix, font=font)[2] > width:
        value = value[:-1]
    return value.rstrip() + suffix


def _draw_card(
    sheet: Image.Image,
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    *,
    image: Image.Image,
    title: str,
    subtitle: str,
    accent: str,
) -> None:
    draw.rounded_rectangle(
        (x, y, x + CARD_WIDTH, y + CARD_HEIGHT),
        radius=10,
        fill=CARD,
        outline=BORDER,
        width=1,
    )
    draw.rectangle((x, y, x + 7, y + CARD_HEIGHT), fill=accent)
    image_x = x + 20
    image_y = y + 16
    image_size = (CARD_WIDTH - 40, 154)
    fitted = ImageOps.contain(image, image_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", image_size, "white")
    canvas.paste(
        fitted,
        ((image_size[0] - fitted.width) // 2, (image_size[1] - fitted.height) // 2),
    )
    sheet.paste(canvas, (image_x, image_y))
    draw.rectangle(
        (image_x, image_y, image_x + image_size[0], image_y + image_size[1]),
        outline="#e2e5e9",
    )
    title_font = _font(14, bold=True)
    subtitle_font = _font(11)
    draw.text(
        (x + 20, y + 181),
        _ellipsize(draw, title, title_font, CARD_WIDTH - 40),
        fill=INK,
        font=title_font,
    )
    draw.text(
        (x + 20, y + 213),
        _ellipsize(draw, subtitle, subtitle_font, CARD_WIDTH - 40),
        fill=MUTED,
        font=subtitle_font,
    )


def _section(
    draw: ImageDraw.ImageDraw,
    y: int,
    title: str,
    description: str,
    color: str,
) -> None:
    draw.text((MARGIN, y), title, fill=color, font=_font(23, bold=True))
    draw.text((MARGIN, y + 34), description, fill=MUTED, font=_font(14))


def render_preview(root: Path, output: Path) -> None:
    rows = _rows(root)
    height = 1640
    sheet = Image.new("RGB", (WIDTH, height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (MARGIN, 26),
        "PixCell expansion machine · approval preview",
        fill=INK,
        font=_font(31, bold=True),
    )
    draw.text(
        (MARGIN, 72),
        "No new rows are generated here. This shows which changes count and how they remain separated.",
        fill=MUTED,
        font=_font(16),
    )

    sections = [
        (
            124,
            "A · New representation grammar",
            "Different construction mechanism or topology = new representation_id.",
            BLUE,
            [
                "directional_coupler_sbend_2x2",
                "directional_coupler_concentric_90deg_2x2",
                "corrugated_contra_directional_coupler_2x2",
                "three_rail_directional_coupler_3x3",
            ],
        ),
        (
            474,
            "B · Controlled realization",
            "Same grammar, a causal physical regime; not random parameter jitter.",
            GREEN,
            [
                "l1_02_rotate__b1__proposal_a",
                "l1_02_rotate__c2__proposal_b",
                "l1_03_mirror__a1__proposal_a",
                "l1_03_mirror__c1__proposal_b",
            ],
        ),
        (
            824,
            "C · Useful equivariance",
            "Same grammar and leakage group; add pose only when code/ports learn something.",
            AMBER,
            [
                "l0_01_rectangle__semantic__mild_landscape",
                "l0_01_rectangle__equivariance__mild_portrait",
                "l0_01_rectangle__equivariance__landscape_rot45",
            ],
        ),
    ]
    for y, title, description, color, identifiers in sections:
        _section(draw, y, title, description, color)
        x = MARGIN
        for identifier in identifiers:
            row = rows[identifier]
            _draw_card(
                sheet,
                draw,
                x,
                y + 72,
                image=_fit(_payload(row), (360, 154)),
                title=str(row["label"]),
                subtitle=(
                    f"{row['variation_role']} · grammar {str(row['grammar_id'])[:24]}"
                ),
                accent=color,
            )
            x += CARD_WIDTH + CARD_GAP

    render_y = 1174
    _section(
        draw,
        render_y,
        "D · Visual-domain rendering",
        "Same geometry and code = separate render_id; never counted as representation diversity.",
        PURPLE,
    )
    render_row = rows["chirped_apodized_tapered_grating_1x0"]
    render_cards = [
        (
            _fit(_payload(render_row, "image"), (360, 154)),
            "Maximum-visibility supervision",
            "primary image · topology and fine features",
        ),
        (
            _fit(_payload(render_row, "target_image"), (360, 154)),
            "Physical-aspect target",
            "same geometry · canonical raster",
        ),
        (
            _paper_variant(_payload(render_row, "target_image"), (360, 154)),
            "Paper-style companion preview",
            "same geometry · separate render configuration",
        ),
    ]
    x = MARGIN
    for image, title, subtitle in render_cards:
        _draw_card(
            sheet,
            draw,
            x,
            render_y + 72,
            image=image,
            title=title,
            subtitle=subtitle,
            accent=PURPLE,
        )
        x += CARD_WIDTH + CARD_GAP

    pipeline_y = 1530
    stages = [
        ("Grammar spec", BLUE),
        ("Executable program", GREEN),
        ("Machine admission", AMBER),
        ("Review gallery", PURPLE),
        ("Versioned config", INK),
    ]
    x = MARGIN
    for index, (label, color) in enumerate(stages):
        box_width = 270
        draw.rounded_rectangle(
            (x, pipeline_y, x + box_width, pipeline_y + 54),
            radius=9,
            fill="#ffffff",
            outline=color,
            width=2,
        )
        draw.text((x + 18, pipeline_y + 17), label, fill=color, font=_font(15))
        x += box_width
        if index < len(stages) - 1:
            draw.line(
                (x + 8, pipeline_y + 27, x + 62, pipeline_y + 27), fill=MUTED, width=2
            )
            draw.polygon(
                [
                    (x + 62, pipeline_y + 27),
                    (x + 51, pipeline_y + 20),
                    (x + 51, pipeline_y + 34),
                ],
                fill=MUTED,
            )
            x += 82

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="PNG", compress_level=6, optimize=False)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    root = args.root.expanduser().resolve()
    output = (
        args.output.expanduser().resolve()
        if args.output is not None
        else root / "factory" / "expansion" / "preview.png"
    )
    render_preview(root, output)
    print(f"rendered expansion preview: {output}")


if __name__ == "__main__":
    main()
