"""Render Figure 4: source-panel standardization into target renders.

The publication source crops and their hashes live in
``fig_extraction_assets/manifest.json``. Frozen output masks are reused from
Figure 3's audited target assets so the two figures cannot silently drift.

Run from the repository root:
    python arxiv/scripts/make_fig_extraction.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle
from PIL import Image


REPO = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__file__).with_name("fig_extraction_assets")
SOURCE_MANIFEST = ASSET_DIR / "manifest.json"
TARGET_DIR = Path(__file__).with_name("fig_target_assets")
TARGET_MANIFEST = TARGET_DIR / "manifest.json"
FIGURE_DIR = REPO / "arxiv" / "figures"

INK = "#17191c"
RULE = "#17191c"
HEADER_HEIGHT_FIGURE = 0.072

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": [
            "Iowan Old Style",
            "STIX Two Text",
            "STIXGeneral",
            "Times New Roman",
        ],
        "mathtext.fontset": "stix",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.facecolor": "white",
        "savefig.bbox": None,
    }
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _center_foreground(image: np.ndarray, bbox: list[int]) -> np.ndarray:
    """Match Figure 3's presentation-only foreground centering."""

    h, w = image.shape
    x0, y0, x1, y1 = bbox
    shift_x = round(w / 2 - (x0 + x1) / 2)
    shift_y = round(h / 2 - (y0 + y1) / 2)
    centered = np.full_like(image, 255)

    source_x0 = max(0, -shift_x)
    source_x1 = min(w, w - shift_x)
    source_y0 = max(0, -shift_y)
    source_y1 = min(h, h - shift_y)
    target_x0 = source_x0 + shift_x
    target_x1 = source_x1 + shift_x
    target_y0 = source_y0 + shift_y
    target_y1 = source_y1 + shift_y
    centered[target_y0:target_y1, target_x0:target_x1] = image[
        source_y0:source_y1, source_x0:source_x1
    ]
    return centered


def _load_examples() -> list[dict]:
    source_specification = json.loads(SOURCE_MANIFEST.read_text())
    target_specification = json.loads(TARGET_MANIFEST.read_text())
    targets = {
        target["id"]: target for target in target_specification["targets"]
    }

    examples = []
    for example in source_specification["examples"]:
        source_path = ASSET_DIR / example["source_asset"]
        if _sha256(source_path) != example["asset_sha256"]:
            raise ValueError(f"Hash mismatch for {source_path}.")

        target = targets[example["id"]]
        target_path = TARGET_DIR / target["asset"]
        if _sha256(target_path) != target["asset_sha256"]:
            raise ValueError(f"Hash mismatch for {target_path}.")

        examples.append(
            {
                **example,
                "source_image": np.asarray(Image.open(source_path).convert("RGB")),
                "target_image": _center_foreground(
                    np.asarray(Image.open(target_path).convert("L")),
                    target["calibration_bbox_px"],
                ),
                "footprint_um": target["footprint_um"],
            }
        )
    return examples


def _format_extent(value: float) -> str:
    if value == int(value):
        return f"{int(value)}"
    return f"{value:g}"


def _add_card(
    fig: plt.Figure,
    rect: tuple[float, float, float, float],
    image: np.ndarray,
    left_label: str,
    right_label: str | None,
    *,
    binary: bool = False,
) -> None:
    card = fig.add_axes(rect)
    card.set_xlim(0, 1)
    card.set_ylim(0, 1)
    card.axis("off")
    card.add_patch(
        Rectangle(
            (0.006, 0.008),
            0.988,
            0.984,
            facecolor="white",
            edgecolor=RULE,
            linewidth=0.72,
        )
    )

    header_y = 1.0 - HEADER_HEIGHT_FIGURE / rect[3]
    header_center_y = (1.0 + header_y) / 2.0
    card.plot(
        [0.006, 0.994],
        [header_y, header_y],
        color=RULE,
        linewidth=0.72,
        solid_capstyle="butt",
    )
    card.text(
        0.04,
        header_center_y,
        left_label,
        ha="left",
        va="center",
        fontsize=15.2,
        fontweight="normal",
        color=INK,
    )
    if right_label:
        card.text(
            0.96,
            header_center_y,
            right_label,
            ha="right",
            va="center",
            fontsize=14.0,
            color=INK,
        )

    image_ax = card.inset_axes([0.035, 0.045, 0.93, header_y - 0.085])
    if binary:
        image_ax.imshow(
            image,
            cmap="gray",
            vmin=0,
            vmax=255,
            interpolation="antialiased",
            aspect="equal",
        )
    else:
        image_ax.imshow(image, interpolation="antialiased", aspect="equal")
    image_ax.set_xticks([])
    image_ax.set_yticks([])
    for spine in image_ax.spines.values():
        spine.set_visible(False)


def _add_process_arrow(
    fig: plt.Figure,
    *,
    y: float,
) -> None:
    overlay = fig.add_axes([0, 0, 1, 1])
    overlay.set_xlim(0, 1)
    overlay.set_ylim(0, 1)
    overlay.axis("off")
    overlay.add_patch(
        FancyArrowPatch(
            (0.455, y),
            (0.545, y),
            arrowstyle="-|>",
            mutation_scale=14,
            linewidth=1.15,
            color=INK,
            shrinkA=0,
            shrinkB=0,
        )
    )


def main() -> None:
    examples = {example["id"]: example for example in _load_examples()}
    fig = plt.figure(figsize=(6.45, 4.5), facecolor="white")

    rows = {
        "F5": (0.57, 0.40),
        "F2": (0.035, 0.49),
    }
    for target_id in ("F5", "F2"):
        example = examples[target_id]
        y, height = rows[target_id]
        width, target_height = example["footprint_um"]
        footprint = (
            rf"${_format_extent(width)}\times{_format_extent(target_height)}"
            r"\,\mathrm{\mu m}$"
        )
        _add_card(
            fig,
            (0.015, y, 0.425, height),
            example["source_image"],
            target_id,
            None,
        )
        _add_process_arrow(
            fig,
            y=y + height / 2,
        )
        _add_card(
            fig,
            (0.56, y, 0.425, height),
            example["target_image"],
            "target render",
            footprint,
            binary=True,
        )

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    output = FIGURE_DIR / "fig_extraction.pdf"
    fig.savefig(output, dpi=600, facecolor="white")
    print(f"wrote {output}")
    plt.close(fig)


if __name__ == "__main__":
    main()
