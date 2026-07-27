#!/usr/bin/env python3
"""Render deterministic review galleries for the PixCell depth-v1 release."""

from __future__ import annotations

import argparse
import io
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from PIL import Image, ImageDraw, ImageFont, ImageOps

from schema import (
    ANCHOR_ONLY_PARENT_IDS,
    APPROVED_REPRESENTATION_COUNT,
    DEPTH_ELIGIBLE_COUNT,
    GEOMETRY_STATE_COUNT,
)

LEVELS = ("L0", "L1", "L2", "L3", "L4")
STATE_SLOTS = tuple(range(GEOMETRY_STATE_COUNT))
PAGE_ROWS = 12
CELL_WIDTH = 160
CELL_HEIGHT = 164
IMAGE_BOX = 138
HEADER_HEIGHT = 54


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    del bold
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10 compatibility for downstream users.
        return ImageFont.load_default()


def _image(value: Any) -> Image.Image:
    if not isinstance(value, dict) or not value.get("bytes"):
        raise ValueError("gallery row does not contain embedded image bytes")
    with Image.open(io.BytesIO(bytes(value["bytes"]))) as opened:
        return opened.convert("L")


def _thumbnail(value: Any, size: int = IMAGE_BOX) -> Image.Image:
    image = _image(value)
    fitted = ImageOps.contain(image, (size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("L", (size, size), 255)
    canvas.paste(
        fitted,
        ((size - fitted.width) // 2, (size - fitted.height) // 2),
    )
    return canvas


def _load_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split in ("train", "validation"):
        for path in sorted((root / "data").glob(f"{split}-*.parquet")):
            rows.extend(pq.read_table(path).to_pylist())
    if not rows:
        raise ValueError(f"no depth-v1 Parquet shards found below {root / 'data'}")
    return rows


def _state_rows(
    rows: list[dict[str, Any]],
) -> dict[str, dict[int, dict[str, Any]]]:
    grouped: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        slot = int(row["realization_slot"])
        if slot in STATE_SLOTS:
            grammar_id = str(row["grammar_id"])
            if slot in grouped[grammar_id]:
                raise ValueError(f"duplicate gallery state: {grammar_id}/{slot}")
            grouped[grammar_id][slot] = row
    expected_complete_slots = set(STATE_SLOTS)
    anchor_only_observed: set[str] = set()
    invalid: dict[str, dict[str, Any]] = {}
    for grammar_id, states in grouped.items():
        anchor = states.get(0)
        if anchor is None:
            invalid[grammar_id] = {
                "expected": sorted(expected_complete_slots),
                "observed": sorted(states),
                "reason": "missing anchor",
            }
            continue
        parent_id = str(anchor.get("parent_core_id", ""))
        expected = {0} if parent_id in ANCHOR_ONLY_PARENT_IDS else expected_complete_slots
        if set(states) != expected:
            invalid[grammar_id] = {
                "expected": sorted(expected),
                "observed": sorted(states),
                "reason": "state schedule differs",
            }
        if set(states) == {0}:
            anchor_only_observed.add(parent_id)
    if invalid:
        first = next(iter(sorted(invalid.items())))
        raise ValueError(f"invalid gallery state schedule: {first}")
    if anchor_only_observed != set(ANCHOR_ONLY_PARENT_IDS):
        raise ValueError(
            "anchor-only gallery inventory differs: "
            f"observed={sorted(anchor_only_observed)}, "
            f"expected={sorted(ANCHOR_ONLY_PARENT_IDS)}"
        )
    return dict(grouped)


def _draw_progression_page(
    records: list[tuple[str, dict[int, dict[str, Any]]]],
    *,
    level: str,
    page_number: int,
    page_count: int,
) -> Image.Image:
    width = len(STATE_SLOTS) * CELL_WIDTH
    height = HEADER_HEIGHT + len(records) * CELL_HEIGHT
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    title_font = _font(16, bold=True)
    label_font = _font(11)
    small_font = _font(9)
    draw.text(
        (10, 8),
        f"PixCell depth-v1 · {level} · page {page_number}/{page_count}",
        fill="black",
        font=title_font,
    )
    for column, slot in enumerate(STATE_SLOTS):
        draw.text(
            (column * CELL_WIDTH + 8, 33),
            f"r{slot:02d}",
            fill=(70, 70, 70),
            font=label_font,
        )
    for row_index, (grammar_id, states) in enumerate(records):
        y0 = HEADER_HEIGHT + row_index * CELL_HEIGHT
        for column, slot in enumerate(STATE_SLOTS):
            record = states[slot]
            x0 = column * CELL_WIDTH
            thumb = _thumbnail(record["image"])
            canvas.paste(thumb.convert("RGB"), (x0 + 11, y0 + 2))
            label = str(record["label"]) if column == 0 else str(
                record["transform_kind"]
            )
            label = label.replace("\n", " ")
            if len(label) > 25:
                label = label[:24] + "…"
            draw.text(
                (x0 + 5, y0 + IMAGE_BOX + 4),
                label,
                fill=(25, 25, 25),
                font=small_font,
            )
            draw.rectangle(
                (x0, y0, x0 + CELL_WIDTH - 1, y0 + CELL_HEIGHT - 1),
                outline=(220, 220, 220),
                width=1,
            )
        draw.text(
            (5, y0 + 5),
            grammar_id[:18],
            fill=(85, 85, 85),
            font=small_font,
        )
    return canvas


def _draw_overview(
    grouped: dict[str, dict[int, dict[str, Any]]],
) -> Image.Image:
    anchors = [
        states[0]
        for _grammar_id, states in sorted(grouped.items())
    ]
    columns = 16
    cell_width = 150
    cell_height = 164
    rows = (len(anchors) + columns - 1) // columns
    canvas = Image.new(
        "RGB",
        (columns * cell_width, HEADER_HEIGHT + rows * cell_height),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (10, 8),
        "PixCell depth-v1 · 547 approved representation anchors",
        fill="black",
        font=_font(18, bold=True),
    )
    draw.text(
        (10, 32),
        (
            f"{DEPTH_ELIGIBLE_COUNT} anchors have seven controlled geometry "
            "descendants in the progression pages."
        ),
        fill=(70, 70, 70),
        font=_font(11),
    )
    for index, record in enumerate(anchors):
        column = index % columns
        row = index // columns
        x0 = column * cell_width
        y0 = HEADER_HEIGHT + row * cell_height
        thumb = _thumbnail(record["image"], size=128)
        canvas.paste(thumb.convert("RGB"), (x0 + 11, y0 + 2))
        label = str(record["label"]).replace("\n", " ")
        if len(label) > 23:
            label = label[:22] + "…"
        draw.text(
            (x0 + 5, y0 + 134),
            f"{record['level']} · {label}",
            fill=(25, 25, 25),
            font=_font(9),
        )
        draw.rectangle(
            (x0, y0, x0 + cell_width - 1, y0 + cell_height - 1),
            outline=(225, 225, 225),
            width=1,
        )
    return canvas


def render_galleries(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    rows = _load_rows(root)
    grouped = _state_rows(rows)
    if len(grouped) != APPROVED_REPRESENTATION_COUNT:
        raise ValueError(
            f"expected {APPROVED_REPRESENTATION_COUNT} representation anchors, "
            f"got {len(grouped)}"
        )
    progressions = {
        grammar_id: states
        for grammar_id, states in grouped.items()
        if str(states[0]["parent_core_id"]) not in ANCHOR_ONLY_PARENT_IDS
    }
    if len(progressions) != DEPTH_ELIGIBLE_COUNT:
        raise ValueError(
            f"expected {DEPTH_ELIGIBLE_COUNT} complete progressions, "
            f"got {len(progressions)}"
        )

    galleries = root / "galleries"
    pages_root = galleries / "progressions"
    pages_root.mkdir(parents=True, exist_ok=True)
    overview = _draw_overview(grouped)
    overview_path = galleries / "overview.png"
    overview.save(overview_path, format="PNG", optimize=False, compress_level=9)

    records: list[dict[str, Any]] = []
    for level in LEVELS:
        level_records = [
            (grammar_id, states)
            for grammar_id, states in sorted(progressions.items())
            if states[0]["level"] == level
        ]
        page_count = (len(level_records) + PAGE_ROWS - 1) // PAGE_ROWS
        for page_index in range(page_count):
            chunk = level_records[
                page_index * PAGE_ROWS : (page_index + 1) * PAGE_ROWS
            ]
            image = _draw_progression_page(
                chunk,
                level=level,
                page_number=page_index + 1,
                page_count=page_count,
            )
            relative = (
                Path("galleries")
                / "progressions"
                / f"{level.lower()}-{page_index + 1:02d}.png"
            )
            target = root / relative
            image.save(target, format="PNG", optimize=False, compress_level=9)
            records.append(
                {
                    "level": level,
                    "page": page_index + 1,
                    "path": relative.as_posix(),
                    "representation_ids": [grammar_id for grammar_id, _ in chunk],
                }
            )

    manifest = {
        "overview": "galleries/overview.png",
        "anchor_representation_count": len(grouped),
        "progression_representation_count": len(progressions),
        "anchor_only_parent_ids": sorted(ANCHOR_ONLY_PARENT_IDS),
        "progression_page_count": len(records),
        "state_slots": [f"r{slot:02d}" for slot in STATE_SLOTS],
        "pages": records,
    }
    metadata = root / "metadata"
    metadata.mkdir(parents=True, exist_ok=True)
    (metadata / "gallery_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    print(json.dumps(render_galleries(args.root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
