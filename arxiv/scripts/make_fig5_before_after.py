"""Render Figure 8: selected reconstructions from the two evaluation records.

The target masks are the hash-locked publication assets shared with Figure 3.
The nine displayed candidate rasters and their source hashes are recorded in
``fig_before_after_assets/manifest.json``.  This generator evaluates both the
pixel classes and the displayed IoUs at the archived white threshold of 245.

Run from the repository root:
    python arxiv/scripts/make_fig5_before_after.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import numpy as np
from PIL import Image


REPO = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__file__).with_name("fig_before_after_assets")
MANIFEST = ASSET_DIR / "manifest.json"
FIGURE_DIR = REPO / "arxiv" / "figures"

# Shared white-page publication system.
INK = "#17191c"
RULE = "#17191c"
OVERLAP = "#800000"
CANDIDATE_ONLY = "#ff9299"
TARGET_ONLY = INK
DISPLAY_ASPECT = 0.46

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


def _load_inputs() -> list[dict]:
    specification = json.loads(MANIFEST.read_text())
    threshold = int(specification["white_threshold"])
    targets = specification["targets"]
    if [target["id"] for target in targets] != ["F1", "F7", "F8"]:
        raise ValueError("Figure 8 manifest must contain ordered targets F1, F7, F8.")

    loaded_targets = []
    for target in targets:
        expected_width, expected_height = target["image_size_px"]
        target_path = _verified_path(
            target["target_asset"],
            target["target_sha256"],
        )
        target_image = np.asarray(Image.open(target_path).convert("L"))
        if target_image.shape != (expected_height, expected_width):
            raise ValueError(f"Target size mismatch for {target_path}.")
        if not set(np.unique(target_image)).issubset({0, 255}):
            raise ValueError(f"Target publication asset is not binary: {target_path}.")
        target_mask = target_image < 128

        cases = []
        for case in target["cases"]:
            raster_path = _verified_path(
                case["raster_asset"],
                case["raster_sha256"],
            )
            raster_image = np.asarray(Image.open(raster_path).convert("L"))
            if raster_image.shape != target_image.shape:
                raise ValueError(f"Raster size mismatch for {raster_path}.")
            candidate_mask = raster_image < threshold
            intersection = np.logical_and(target_mask, candidate_mask).sum()
            union = np.logical_or(target_mask, candidate_mask).sum()
            measured_iou = float(intersection / union)
            if not np.isclose(measured_iou, case["iou"], atol=1e-12):
                raise ValueError(
                    f"IoU mismatch for {target['id']} {case['row']}: "
                    f"measured {measured_iou}, expected {case['iou']}."
                )
            cases.append({**case, "candidate": candidate_mask})

        loaded_targets.append(
            {
                **target,
                "target": target_mask,
                "cases": cases,
            }
        )
    return loaded_targets


def _comparison_image(target: np.ndarray, candidate: np.ndarray) -> np.ndarray:
    image = np.full((*target.shape, 3), 255, dtype=np.uint8)
    overlap = np.logical_and(target, candidate)
    candidate_only = np.logical_and(candidate, ~target)
    target_only = np.logical_and(target, ~candidate)
    image[overlap] = (128, 0, 0)
    image[candidate_only] = (255, 146, 153)
    image[target_only] = (23, 25, 28)
    return image


def _shared_crop(target: dict, margin: float = 0.035) -> tuple[slice, slice]:
    union = target["target"].copy()
    for case in target["cases"]:
        union |= case["candidate"]
    rows, columns = np.where(union)
    row_min, row_max = int(rows.min()), int(rows.max())
    column_min, column_max = int(columns.min()), int(columns.max())
    row_pad = int((row_max - row_min) * margin) + 2
    column_pad = int((column_max - column_min) * margin) + 2
    return (
        slice(max(0, row_min - row_pad), min(union.shape[0], row_max + row_pad + 1)),
        slice(
            max(0, column_min - column_pad),
            min(union.shape[1], column_max + column_pad + 1),
        ),
    )


def _pad_to_aspect(image: np.ndarray, aspect: float = DISPLAY_ASPECT) -> np.ndarray:
    height, width = image.shape[:2]
    if height / width < aspect:
        output_height, output_width = round(width * aspect), width
    else:
        output_height, output_width = height, round(height / aspect)
    output = np.full((output_height, output_width, 3), 255, dtype=np.uint8)
    y = (output_height - height) // 2
    x = (output_width - width) // 2
    output[y : y + height, x : x + width] = image
    return output


def _section_title(
    figure: plt.Figure,
    letter: str,
    title: str,
    *,
    y: float,
) -> None:
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
    *,
    model: str,
    iou: float,
    image: np.ndarray,
) -> None:
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
    card.plot(
        [0.004, 0.996],
        [0.725, 0.725],
        color=RULE,
        linewidth=0.58,
        solid_capstyle="butt",
    )
    card.text(
        0.035,
        0.855,
        model,
        ha="left",
        va="center",
        fontsize=7.7,
        fontweight="normal",
        color=INK,
    )
    card.text(
        0.965,
        0.855,
        rf"$\mathrm{{IoU}}={iou:.3f}$",
        ha="right",
        va="center",
        fontsize=7.7,
        fontweight="normal",
        color=INK,
    )
    image_axes = card.inset_axes((0.025, 0.030, 0.950, 0.665))
    image_axes.imshow(image, interpolation="antialiased", aspect="equal")
    image_axes.set_xticks([])
    image_axes.set_yticks([])
    for spine in image_axes.spines.values():
        spine.set_visible(False)


def _row_label(figure: plt.Figure, text: str, *, y: float) -> None:
    figure.text(
        0.145,
        y,
        text,
        ha="right",
        va="center",
        fontsize=7.8,
        fontweight="normal",
        linespacing=1.12,
        color=INK,
    )


def main() -> None:
    targets = _load_inputs()
    rows = ("lower", "higher", "agent")
    row_y = {"lower": 0.645, "higher": 0.425, "agent": 0.060}
    row_height = {"lower": 0.190, "higher": 0.190, "agent": 0.220}

    left = 0.165
    right = 0.980
    gap = 0.015
    width = (right - left - 2 * gap) / 3

    figure = plt.figure(figsize=(7.40, 3.25), facecolor="white")
    _section_title(figure, "A", "Selected iterative API outputs", y=0.965)

    for column, target in enumerate(targets):
        center = left + column * (width + gap) + width / 2
        figure.text(
            center,
            0.895,
            f"{target['id']}  {target['title']}",
            ha="center",
            va="center",
            fontsize=8.4,
            fontweight="normal",
            color=INK,
        )

    _row_label(figure, "Lower-scoring\nselected output", y=0.740)
    _row_label(figure, "Higher-scoring\nselected output", y=0.520)

    prepared: dict[tuple[str, str], np.ndarray] = {}
    for target in targets:
        crop = _shared_crop(target)
        for case in target["cases"]:
            comparison = _comparison_image(target["target"], case["candidate"])
            prepared[(target["id"], case["row"])] = _pad_to_aspect(comparison[crop])

    for column, target in enumerate(targets):
        x = left + column * (width + gap)
        cases_by_row = {case["row"]: case for case in target["cases"]}
        for row in rows[:2]:
            case = cases_by_row[row]
            _card(
                figure,
                (x, row_y[row], width, row_height[row]),
                model=case["model"],
                iou=case["iou"],
                image=prepared[(target["id"], row)],
            )

    figure.add_artist(
        Line2D(
            [0.020, 0.980],
            [0.360, 0.360],
            transform=figure.transFigure,
            color=RULE,
            linewidth=0.72,
        )
    )
    _section_title(
        figure,
        "B",
        "Current-gate outputs from multimodal agents",
        y=0.315,
    )
    _row_label(figure, "Single retained\nrun", y=0.170)

    for column, target in enumerate(targets):
        x = left + column * (width + gap)
        case = next(case for case in target["cases"] if case["row"] == "agent")
        _card(
            figure,
            (x, row_y["agent"], width, row_height["agent"]),
            model=case["model"],
            iou=case["iou"],
            image=prepared[(target["id"], "agent")],
        )

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    output = FIGURE_DIR / "fig5_before_after.pdf"
    figure.savefig(output, dpi=600, facecolor="white", bbox_inches=None)
    print(f"wrote {output}")
    plt.close(figure)


if __name__ == "__main__":
    main()
