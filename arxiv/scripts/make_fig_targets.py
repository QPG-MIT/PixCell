"""Render Figure 3: the eight frozen PixCell benchmark inputs.

The masks are data, not illustrations. The tracked render assets are exact
one-bit versions of the archived ``device_bw.png`` files at the archived
white threshold (245); ``manifest.json`` records both source and asset hashes.
All framing, typography, and rules remain vector artwork in the PDF.

Run from the repository root:
    python arxiv/scripts/make_fig_targets.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from PIL import Image


REPO = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__file__).with_name("fig_target_assets")
MANIFEST = ASSET_DIR / "manifest.json"
FIGURE_DIR = REPO / "arxiv" / "figures"

INK = "#1b1b1b"
RULE = "#242424"
DISPLAY_ASPECT = 0.53  # height / width of the common image-space viewport

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.facecolor": "white",
        "savefig.bbox": None,
    }
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_targets() -> list[tuple[dict, np.ndarray]]:
    specification = json.loads(MANIFEST.read_text())
    targets = specification["targets"]
    if [target["id"] for target in targets] != [f"F{i}" for i in range(1, 9)]:
        raise ValueError("Figure 3 manifest must contain ordered targets F1--F8.")

    loaded = []
    for target in targets:
        path = ASSET_DIR / target["asset"]
        if _sha256(path) != target["asset_sha256"]:
            raise ValueError(f"Hash mismatch for {path}.")
        image = np.asarray(Image.open(path).convert("L"))
        if not set(np.unique(image)).issubset({0, 255}):
            raise ValueError(f"{path} is not a binary publication asset.")
        loaded.append((target, image))
    return loaded


def _center_foreground(image: np.ndarray, bbox: list[int]) -> np.ndarray:
    """Center the calibrated foreground for display without rescaling it."""

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


def _panel_image(
    image: np.ndarray, bbox: list[int], margin: float = 0.025
) -> np.ndarray:
    """Place a foreground-centered input raster in a common viewport."""

    image = _center_foreground(image, bbox)
    h, w = image.shape
    pad_y = max(1, round(h * margin))
    pad_x = max(1, round(w * margin))
    image = np.pad(
        image,
        ((pad_y, pad_y), (pad_x, pad_x)),
        mode="constant",
        constant_values=255,
    )

    h, w = image.shape
    if h / w < DISPLAY_ASPECT:
        out_h, out_w = round(w * DISPLAY_ASPECT), w
    else:
        out_h, out_w = h, round(h / DISPLAY_ASPECT)
    viewport = np.full((out_h, out_w), 255, dtype=np.uint8)
    y0 = (out_h - h) // 2
    x0 = (out_w - w) // 2
    viewport[y0 : y0 + h, x0 : x0 + w] = image
    return viewport


def _format_extent(value: float) -> str:
    if value == int(value):
        return f"{int(value)}"
    return f"{value:g}"


def _draw_card(ax: plt.Axes, target: dict, image: np.ndarray) -> None:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.add_patch(
        Rectangle(
            (0.006, 0.008),
            0.988,
            0.984,
            facecolor="white",
            edgecolor=RULE,
            linewidth=0.72,
            clip_on=False,
        )
    )
    header_y = 0.814
    ax.plot(
        [0.006, 0.994],
        [header_y, header_y],
        color=RULE,
        linewidth=0.62,
        solid_capstyle="butt",
    )
    ax.text(
        0.04,
        0.902,
        target["id"],
        ha="left",
        va="center",
        fontsize=10.2,
        fontweight="bold",
        color=INK,
    )
    width, height = target["footprint_um"]
    extent = (
        rf"${_format_extent(width)}\times{_format_extent(height)}"
        r"\,\mathrm{\mu m}$"
    )
    ax.text(
        0.96,
        0.902,
        extent,
        ha="right",
        va="center",
        fontsize=9.0,
        color=INK,
    )

    image_ax = ax.inset_axes([0.026, 0.035, 0.948, 0.745])
    image_ax.imshow(
        _panel_image(image, target["calibration_bbox_px"]),
        cmap="gray",
        vmin=0,
        vmax=255,
        interpolation="antialiased",
        aspect="equal",
    )
    image_ax.set_xticks([])
    image_ax.set_yticks([])
    for spine in image_ax.spines.values():
        spine.set_visible(False)


def main() -> None:
    targets = _load_targets()
    fig, axes = plt.subplots(2, 4, figsize=(10.0, 2.58))
    fig.patch.set_facecolor("white")
    fig.subplots_adjust(
        left=0.008,
        right=0.992,
        top=0.985,
        bottom=0.015,
        wspace=0.036,
        hspace=0.075,
    )

    for ax, (target, image) in zip(axes.flat, targets):
        _draw_card(ax, target, image)

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    output = FIGURE_DIR / "fig_targets.pdf"
    fig.savefig(output, dpi=600, facecolor="white")
    print(f"wrote {output}")
    plt.close(fig)


if __name__ == "__main__":
    main()
