"""Render the frozen PixCell representation curriculum.

The figure reuses the card, typography, and viewport system of Figure 3.
Its images are exact model-view PNGs embedded in the tracked core Parquet
shards. The manifest fixes the selected rows and every source and payload hash.

Run from the repository root:
    uv run python arxiv/scripts/make_fig_dataset_curriculum.py
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pyarrow.parquet as pq
from PIL import Image

from make_fig_targets import FIGURE_DIR, _draw_card


REPO = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__file__).with_name("fig_dataset_curriculum_assets")
MANIFEST = ASSET_DIR / "manifest.json"
CORE_FREEZE = REPO / "dataset" / "factory" / "core-v1" / "freeze.json"
EXPECTED_PANEL_ORDER = [f"L{level}" for level in range(5)] * 2
ROW_FIELDS = (
    "id",
    "level",
    "curriculum_order",
    "label",
    "family",
    "representation_id",
    "footprint_um",
    "image",
    "image_sha256",
    "code_sha256",
    "view_policy",
    "source_dataset_digest_sha256",
    "source_generator_version",
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _resolve_source(relative: str) -> Path:
    path = (REPO / relative).resolve()
    try:
        path.relative_to(REPO)
    except ValueError as exc:
        raise ValueError(f"Curriculum source escapes the repository: {relative}") from exc
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _row_lookup(path: Path) -> dict[str, dict[str, Any]]:
    table = pq.read_table(path, columns=list(ROW_FIELDS))
    rows = table.to_pylist()
    lookup = {str(row["id"]): row for row in rows}
    if len(lookup) != len(rows):
        raise ValueError(f"Duplicate row IDs in {path}.")
    return lookup


def _image_payload(row_id: str, value: Any) -> bytes:
    if not isinstance(value, dict) or not value.get("bytes"):
        raise ValueError(f"{row_id}: embedded image payload is missing.")
    return bytes(value["bytes"])


def _load_panels() -> list[tuple[dict[str, Any], np.ndarray]]:
    specification = json.loads(MANIFEST.read_text())
    freeze = json.loads(CORE_FREEZE.read_text())
    if (
        freeze["release_digest_sha256"]
        != specification["core_release_digest_sha256"]
    ):
        raise ValueError("The curriculum manifest does not match the frozen core release.")

    panels = specification["panels"]
    if [panel["panel_id"] for panel in panels] != EXPECTED_PANEL_ORDER:
        raise ValueError("Curriculum manifest must contain ordered L0--L4 rows.")

    rows_by_level: dict[str, dict[str, dict[str, Any]]] = {}
    for level, source in specification["sources"].items():
        path = _resolve_source(source["path"])
        if _sha256_path(path) != source["sha256"]:
            raise ValueError(f"Hash mismatch for {path}.")
        freeze_path = str(path.relative_to(REPO / "dataset"))
        if freeze["reference_artifacts"].get(freeze_path) != source["sha256"]:
            raise ValueError(f"{path} is not the shard recorded by the core freeze.")
        rows_by_level[level] = _row_lookup(path)

    loaded: list[tuple[dict[str, Any], np.ndarray]] = []
    for panel in panels:
        level = panel["source_level"]
        row_id = panel["row_id"]
        row = rows_by_level[level].get(row_id)
        if row is None:
            raise ValueError(f"{row_id}: row is absent from the frozen {level} shard.")

        expected_fields = (
            "curriculum_order",
            "label",
            "family",
            "representation_id",
            "image_sha256",
            "code_sha256",
            "view_policy",
            "source_dataset_digest_sha256",
            "source_generator_version",
        )
        for field in expected_fields:
            if row[field] != panel[field]:
                raise ValueError(f"{row_id}: manifest mismatch for {field}.")
        if row["level"] != panel["panel_id"]:
            raise ValueError(f"{row_id}: level does not match its panel.")

        footprint = [float(value) for value in row["footprint_um"]]
        if footprint != panel["footprint_um"]:
            raise ValueError(f"{row_id}: footprint differs from the manifest.")

        payload = _image_payload(row_id, row["image"])
        if _sha256_bytes(payload) != panel["image_sha256"]:
            raise ValueError(f"{row_id}: embedded image hash mismatch.")
        image = np.asarray(Image.open(io.BytesIO(payload)).convert("L"))
        if image.min() == image.max():
            raise ValueError(f"{row_id}: embedded image is blank.")

        height, width = image.shape
        target = {
            "id": panel["panel_id"],
            "footprint_um": footprint,
            "calibration_bbox_px": [0, 0, width, height],
        }
        loaded.append((target, image))
    return loaded


def main() -> None:
    panels = _load_panels()
    fig, axes = plt.subplots(2, 5, figsize=(10.0, 2.58))
    fig.patch.set_facecolor("white")
    fig.subplots_adjust(
        left=0.008,
        right=0.992,
        top=0.985,
        bottom=0.015,
        wspace=0.036,
        hspace=0.075,
    )

    for ax, (target, image) in zip(axes.flat, panels, strict=True):
        _draw_card(ax, target, image)

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    output = FIGURE_DIR / "fig_dataset_curriculum.pdf"
    fig.savefig(output, dpi=600, facecolor="white")
    print(f"wrote {output}")
    plt.close(fig)


if __name__ == "__main__":
    main()
