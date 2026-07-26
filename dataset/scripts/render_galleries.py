#!/usr/bin/env python3
"""Render deterministic contact sheets from the canonical Parquet release.

The sheets show the exact ``image`` field presented to a model.  They do not
re-render GDS, so this command works from a downloaded Hugging Face snapshot
without the geometry toolchain.
"""

from __future__ import annotations

import argparse
import io
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from PIL import Image, ImageDraw, ImageFont, ImageOps

from _shared import LEVELS, ReleaseError


BACKGROUND = "#f4f5f7"
CARD = "#ffffff"
BORDER = "#c8ccd2"
TEXT = "#111318"
MUTED = "#5c6470"
TILE_WIDTH = 360
TILE_HEIGHT = 260
IMAGE_BOX = (320, 178)
GAP = 14
OUTER = 22
HEADER_HEIGHT = 70


@dataclass(frozen=True)
class GalleryRow:
    example_id: str
    label: str
    level: str
    image_bytes: bytes


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    """Use Pillow's bundled font so output does not depend on the host OS."""

    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10 compatibility.
        return ImageFont.load_default()


def _read_rows(parquet_path: Path) -> list[GalleryRow]:
    if not parquet_path.is_file():
        raise ReleaseError(f"missing Parquet shard: {parquet_path}")
    table = pq.read_table(
        parquet_path,
        columns=["id", "label", "level", "image"],
    )
    rows: list[GalleryRow] = []
    for raw in table.to_pylist():
        image_value = raw["image"]
        payload = image_value.get("bytes") if isinstance(image_value, dict) else None
        if not payload:
            raise ReleaseError(f"{raw['id']}: image bytes are not embedded")
        rows.append(
            GalleryRow(
                example_id=str(raw["id"]),
                label=str(raw["label"]),
                level=str(raw["level"]),
                image_bytes=bytes(payload),
            )
        )
    return rows


def _fit_image(payload: bytes) -> Image.Image:
    with Image.open(io.BytesIO(payload)) as opened:
        image = opened.convert("RGB")
    image = ImageOps.contain(image, IMAGE_BOX, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", IMAGE_BOX, "white")
    x = (IMAGE_BOX[0] - image.width) // 2
    y = (IMAGE_BOX[1] - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def _ellipsize(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    width: int,
) -> str:
    if draw.textbbox((0, 0), text, font=font)[2] <= width:
        return text
    suffix = "..."
    candidate = text
    while candidate and draw.textbbox((0, 0), candidate + suffix, font=font)[2] > width:
        candidate = candidate[:-1]
    return candidate.rstrip() + suffix


def render_gallery(
    rows: list[GalleryRow],
    output_path: Path,
    *,
    title: str,
    columns: int = 6,
) -> None:
    if not rows:
        raise ReleaseError(f"cannot render empty gallery: {title}")
    columns = max(1, columns)
    row_count = math.ceil(len(rows) / columns)
    width = 2 * OUTER + columns * TILE_WIDTH + (columns - 1) * GAP
    height = (
        2 * OUTER
        + HEADER_HEIGHT
        + row_count * TILE_HEIGHT
        + max(0, row_count - 1) * GAP
    )
    sheet = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    title_font = _font(25, bold=True)
    body_font = _font(14)
    small_font = _font(12)
    draw.text((OUTER, OUTER), title, fill=TEXT, font=title_font)
    draw.text(
        (OUTER, OUTER + 36),
        f"{len(rows)} accepted image-program examples · exact model input view",
        fill=MUTED,
        font=body_font,
    )

    y_origin = OUTER + HEADER_HEIGHT
    for index, row in enumerate(rows):
        grid_y, grid_x = divmod(index, columns)
        x0 = OUTER + grid_x * (TILE_WIDTH + GAP)
        y0 = y_origin + grid_y * (TILE_HEIGHT + GAP)
        x1 = x0 + TILE_WIDTH
        y1 = y0 + TILE_HEIGHT
        draw.rounded_rectangle(
            (x0, y0, x1, y1),
            radius=8,
            fill=CARD,
            outline=BORDER,
            width=1,
        )
        fitted = _fit_image(row.image_bytes)
        image_x = x0 + (TILE_WIDTH - IMAGE_BOX[0]) // 2
        image_y = y0 + 12
        sheet.paste(fitted, (image_x, image_y))
        draw.rectangle(
            (
                image_x,
                image_y,
                image_x + IMAGE_BOX[0],
                image_y + IMAGE_BOX[1],
            ),
            outline="#e1e3e7",
            width=1,
        )
        label = _ellipsize(draw, row.label, body_font, TILE_WIDTH - 28)
        identifier = _ellipsize(
            draw,
            row.example_id,
            small_font,
            TILE_WIDTH - 28,
        )
        draw.text(
            (x0 + 14, image_y + IMAGE_BOX[1] + 13), label, fill=TEXT, font=body_font
        )
        draw.text(
            (x0 + 14, image_y + IMAGE_BOX[1] + 38),
            identifier,
            fill=MUTED,
            font=small_font,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="PNG", compress_level=6, optimize=False)


def _level_parquet(root: Path, level: str) -> Path:
    matches = sorted((root / "data" / level).glob("train-*.parquet"))
    if len(matches) != 1:
        raise ReleaseError(f"expected one shard for {level}, found {len(matches)}")
    return matches[0]


def render_release_galleries(root: Path, *, columns: int = 6) -> dict[str, Any]:
    root = root.resolve()
    gallery_dir = root / "galleries"
    gallery_dir.mkdir(parents=True, exist_ok=True)
    all_rows: list[GalleryRow] = []
    outputs: dict[str, Any] = {}
    for level in LEVELS:
        rows = _read_rows(_level_parquet(root, level))
        output = gallery_dir / f"{level}.png"
        render_gallery(
            rows,
            output,
            title=f"PixCell curriculum {level.upper()}",
            columns=columns,
        )
        outputs[level] = {
            "path": output.relative_to(root).as_posix(),
            "rows": len(rows),
            "size_px": list(Image.open(output).size),
        }
        all_rows.extend(rows)
    combined = gallery_dir / "all.png"
    render_gallery(
        all_rows,
        combined,
        title="PixCell representation-first image-to-code curriculum · L0–L4",
        columns=max(8, columns),
    )
    outputs["all"] = {
        "path": combined.relative_to(root).as_posix(),
        "rows": len(all_rows),
        "size_px": list(Image.open(combined).size),
    }
    return outputs


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Dataset package root (default: parent of scripts/).",
    )
    parser.add_argument("--columns", type=int, default=6)
    return parser


def main() -> None:
    args = _parser().parse_args()
    outputs = render_release_galleries(args.root, columns=args.columns)
    for name, record in outputs.items():
        print(f"{name}: {record['rows']} rows -> {record['path']}")


if __name__ == "__main__":
    main()
