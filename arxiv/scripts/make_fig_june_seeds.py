"""Render Figure 7: sampling diversity and feedback-guided revision.

The eleven displayed overlays are archived outputs from the June-2026
iterative API campaign.  ``fig_june_seeds_assets/manifest.json`` records their
provenance and hashes.  This generator verifies every image and cross-checks
every displayed IoU against the archived campaign summaries before drawing the
figure.

Run from the repository root:
    python arxiv/scripts/make_fig_june_seeds.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, Rectangle
import numpy as np
from PIL import Image


REPO = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__file__).with_name("fig_june_seeds_assets")
MANIFEST = ASSET_DIR / "manifest.json"
FIGURE_DIR = REPO / "arxiv" / "figures"

# Match the white-page Iowan/STIX publication system used by Figures 1--6.
INK = "#17191c"
RULE = "#17191c"

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


def _verified_path(asset: str, expected_sha256: str) -> Path:
    path = (ASSET_DIR / asset).resolve()
    actual = _sha256(path)
    if actual != expected_sha256:
        raise ValueError(
            f"Hash mismatch for {path}: expected {expected_sha256}, got {actual}."
        )
    return path


def _load_rgb(
    asset: str,
    expected_sha256: str,
    expected_size: list[int],
) -> np.ndarray:
    path = _verified_path(asset, expected_sha256)
    image = np.asarray(Image.open(path).convert("RGB"))
    expected_width, expected_height = expected_size
    if image.shape[:2] != (expected_height, expected_width):
        raise ValueError(
            f"Image size mismatch for {path}: got {image.shape[1]}×{image.shape[0]}, "
            f"expected {expected_width}×{expected_height}."
        )
    return image


def _autocrop(image: np.ndarray, *, pad: float) -> np.ndarray:
    """Remove only uniform white canvas around an archived overlay."""
    foreground = image.min(axis=2) < 245
    rows = np.where(foreground.sum(axis=1) > 3)[0]
    columns = np.where(foreground.sum(axis=0) > 3)[0]
    if len(rows) == 0 or len(columns) == 0:
        return image
    row_min, row_max = rows[0], rows[-1]
    column_min, column_max = columns[0], columns[-1]
    row_pad = int((row_max - row_min) * pad) + 2
    column_pad = int((column_max - column_min) * pad) + 2
    return image[
        max(0, row_min - row_pad) : min(image.shape[0], row_max + row_pad + 1),
        max(0, column_min - column_pad) : min(
            image.shape[1], column_max + column_pad + 1
        ),
    ]


def _load_inputs() -> tuple[list[dict], list[dict]]:
    manifest = json.loads(MANIFEST.read_text())

    seed_specification = manifest["seed_diversity"]
    seed_summary_path = _verified_path(
        seed_specification["summary_asset"],
        seed_specification["summary_sha256"],
    )
    seed_summary = json.loads(seed_summary_path.read_text())
    seed_metrics = {
        entry["run"].removeprefix("run_"): float(entry["iou"])
        for entry in seed_summary["seeds"]
    }
    seed_examples = []
    for example in seed_specification["examples"]:
        run = example["run"]
        if run not in seed_metrics or not np.isclose(
            example["iou"], seed_metrics[run], atol=1e-12
        ):
            raise ValueError(f"Seed IoU mismatch for run {run}.")
        seed_examples.append(
            {
                **example,
                "image": _load_rgb(
                    example["asset"],
                    example["sha256"],
                    seed_specification["image_size_px"],
                ),
            }
        )

    turn_specification = manifest["turn_revision"]
    turn_summary_path = _verified_path(
        turn_specification["summary_asset"],
        turn_specification["summary_sha256"],
    )
    turn_ious = json.loads(turn_summary_path.read_text())["ious"]
    turn_examples = []
    for example in turn_specification["turns"]:
        turn_index = example["turn"] - 1
        if turn_index >= len(turn_ious) or not np.isclose(
            example["iou"], turn_ious[turn_index], atol=1e-12
        ):
            raise ValueError(f"Turn IoU mismatch for turn {example['turn']}.")
        turn_examples.append(
            {
                **example,
                "image": _load_rgb(
                    example["asset"],
                    example["sha256"],
                    turn_specification["image_size_px"],
                ),
            }
        )

    return seed_examples, turn_examples


def _section_title(
    figure: plt.Figure,
    letter: str,
    title: str,
    *,
    y: float,
) -> None:
    """Draw the shared publication panel heading used by Figure 5."""
    figure.text(
        0.020,
        y,
        letter,
        ha="left",
        va="center",
        fontsize=10.5,
        fontweight="normal",
        color=INK,
    )
    figure.text(
        0.056,
        y,
        title,
        ha="left",
        va="center",
        fontsize=10.5,
        fontweight="normal",
        color=INK,
    )


def _card(
    figure: plt.Figure,
    rect: tuple[float, float, float, float],
    title: str,
    metric: str,
) -> plt.Axes:
    card = figure.add_axes(rect)
    card.set_xlim(0, 1)
    card.set_ylim(0, 1)
    card.axis("off")
    card.add_patch(
        Rectangle(
            (0.004, 0.008),
            0.992,
            0.984,
            facecolor="white",
            edgecolor=RULE,
            linewidth=0.72,
        )
    )
    card.text(
        0.045,
        0.875,
        title,
        ha="left",
        va="center",
        fontsize=7.5,
        fontweight="bold",
        color=INK,
    )
    card.text(
        0.955,
        0.875,
        metric,
        ha="right",
        va="center",
        fontsize=7.2,
        fontweight="semibold",
        color=INK,
    )
    return card


def _image_axes(
    card: plt.Axes,
    image: np.ndarray,
    *,
    bounds: tuple[float, float, float, float],
) -> None:
    image_axes = card.inset_axes(bounds)
    image_axes.imshow(image, interpolation="antialiased", aspect="equal")
    image_axes.set_xticks([])
    image_axes.set_yticks([])
    for spine in image_axes.spines.values():
        spine.set_visible(False)


def _seed_row(figure: plt.Figure, examples: list[dict]) -> None:
    left = 0.020
    width = 0.153
    gap = 0.008
    for index, example in enumerate(examples):
        card = _card(
            figure,
            (left + index * (width + gap), 0.655, width, 0.245),
            f"Run {example['run']}",
            rf"$\mathrm{{IoU}}={example['iou']:.3f}$",
        )
        _image_axes(
            card,
            _autocrop(example["image"], pad=0.025),
            bounds=(0.035, 0.105, 0.930, 0.625),
        )


def _turn_row(figure: plt.Figure, examples: list[dict]) -> None:
    left = 0.020
    width = 0.170
    gap = 0.028
    y = 0.060
    height = 0.355
    for index, example in enumerate(examples):
        x = left + index * (width + gap)
        card = _card(
            figure,
            (x, y, width, height),
            f"Turn {example['turn']}",
            rf"$\mathrm{{IoU}}={example['iou']:.3f}$",
        )
        _image_axes(
            card,
            _autocrop(example["image"], pad=0.035),
            bounds=(0.075, 0.055, 0.850, 0.735),
        )
        if index < len(examples) - 1:
            figure.add_artist(
                FancyArrowPatch(
                    (x + width + 0.003, y + 0.190),
                    (x + width + gap - 0.003, y + 0.190),
                    transform=figure.transFigure,
                    arrowstyle="-|>",
                    mutation_scale=8,
                    linewidth=0.82,
                    color=INK,
                    shrinkA=0,
                    shrinkB=0,
                )
            )


def main() -> None:
    seed_examples, turn_examples = _load_inputs()

    figure = plt.figure(figsize=(7.40, 3.15), facecolor="white")
    _section_title(
        figure,
        "A",
        "Independent seeds at fixed prompt and target",
        y=0.965,
    )
    _seed_row(figure, seed_examples)

    figure.add_artist(
        Line2D(
            [0.020, 0.980],
            [0.535, 0.535],
            transform=figure.transFigure,
            color=RULE,
            linewidth=0.72,
        )
    )
    _section_title(
        figure,
        "B",
        "One seed across feedback-guided turns",
        y=0.470,
    )
    _turn_row(figure, turn_examples)

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    output = FIGURE_DIR / "fig_june_seeds.pdf"
    figure.savefig(output, dpi=600, facecolor="white", bbox_inches=None)
    print(f"wrote {output}")
    plt.close(figure)


if __name__ == "__main__":
    main()
