#!/usr/bin/env python3
"""Convert canonical PixCell rows to OpenAI-style multimodal messages JSONL."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from _shared import LEVELS, ReleaseError


def _parquet_paths(root: Path, level: str) -> list[Path]:
    levels = LEVELS if level == "all" else (level,)
    paths: list[Path] = []
    for item in levels:
        matches = sorted((root / "data" / item).glob("train-*.parquet"))
        if len(matches) != 1:
            raise ReleaseError(
                f"{item}: expected one Parquet shard, found {len(matches)}"
            )
        paths.extend(matches)
    return paths


def _image_reference(
    row: dict[str, Any],
    *,
    image_mode: str,
    output_path: Path,
    assets_dir: Path | None,
) -> str:
    value = row["image"]
    if not isinstance(value, dict) or not value.get("bytes"):
        raise ReleaseError(f"{row['id']}: image is not embedded")
    payload = bytes(value["bytes"])
    if image_mode == "data-uri":
        return f"data:image/png;base64,{base64.b64encode(payload).decode('ascii')}"
    if assets_dir is None:
        raise AssertionError("relative-path mode requires an assets directory")
    image_path = assets_dir / f"{row['id']}.png"
    image_path.write_bytes(payload)
    return image_path.relative_to(output_path.parent).as_posix()


def convert(
    *,
    root: Path,
    level: str,
    output_path: Path,
    image_mode: str,
) -> int:
    root = root.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    assets_dir: Path | None = None
    if image_mode == "relative-path":
        assets_dir = output_path.parent / f"{output_path.stem}_images"
        assets_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for parquet_path in _parquet_paths(root, level):
            table = pq.read_table(
                parquet_path,
                columns=[
                    "id",
                    "level",
                    "family",
                    "representation_id",
                    "leakage_group_id",
                    "image",
                    "instruction",
                    "code",
                ],
            )
            for row in table.to_pylist():
                image_url = _image_reference(
                    row,
                    image_mode=image_mode,
                    output_path=output_path,
                    assets_dir=assets_dir,
                )
                result = {
                    "id": row["id"],
                    "level": row["level"],
                    "family": row["family"],
                    "representation_id": row["representation_id"],
                    "leakage_group_id": row["leakage_group_id"],
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": image_url},
                                },
                                {
                                    "type": "text",
                                    "text": row["instruction"],
                                },
                            ],
                        },
                        {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "text",
                                    "text": row["code"],
                                }
                            ],
                        },
                    ],
                }
                handle.write(
                    json.dumps(
                        result,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
                count += 1
    return count


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Dataset package root (default: parent of scripts/).",
    )
    parser.add_argument(
        "--level",
        choices=("all", *LEVELS),
        default="all",
        help="Curriculum level/configuration to convert.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--image-mode",
        choices=("data-uri", "relative-path"),
        default="data-uri",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    count = convert(
        root=args.root,
        level=args.level,
        output_path=args.output,
        image_mode=args.image_mode,
    )
    print(f"wrote {count} examples to {args.output}")


if __name__ == "__main__":
    main()
