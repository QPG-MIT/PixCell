"""Render Figure 5: absolute-scale verification and feedback for F4.

The figure is derived from the archived GPT-5.5 medium reconstruction of
benchmark target F4.  Audited candidate rasters, calibration, and record-grade
metrics are stored in ``fig_verification_assets``; the target render is shared
with Figure 3.  Every advertised score is recomputed from the archived pixels
before the figure is written.

Run from the repository root:
    python arxiv/scripts/make_fig_verification.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, Rectangle
import numpy as np
from PIL import Image


REPO = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__file__).with_name("fig_verification_assets")
MANIFEST = ASSET_DIR / "manifest.json"
FIGURE_DIR = REPO / "arxiv" / "figures"

# Match the white-page publication system used by Figures 1 and 2.
INK = "#17191c"
MUTED = "#424549"
RULE = "#17191c"
CRIMSON = "#a31f34"
VERIFIED = "#267c5a"
DIFF_BLUE = "#315e9f"

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


def _verified_path(base: Path, asset: str, expected_sha256: str) -> Path:
    path = (base / asset).resolve()
    actual = _sha256(path)
    if actual != expected_sha256:
        raise ValueError(
            f"Hash mismatch for {path}: expected {expected_sha256}, got {actual}."
        )
    return path


def _measure(candidate: np.ndarray, target: np.ndarray) -> dict[str, float]:
    overlap = np.logical_and(candidate, target).sum()
    candidate_only = np.logical_and(candidate, ~target).sum()
    target_only = np.logical_and(target, ~candidate).sum()
    union = overlap + candidate_only + target_only
    return {
        "IoU": float(overlap / union),
        "Dice": float(2 * overlap / (2 * overlap + candidate_only + target_only)),
        "SSE": float(candidate_only + target_only),
    }


def _foreground_bbox(mask: np.ndarray) -> list[int]:
    ys, xs = np.where(mask)
    return [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]


def _load_inputs() -> dict:
    specification = json.loads(MANIFEST.read_text())
    target_specification = specification["target"]
    target_path = _verified_path(
        ASSET_DIR,
        target_specification["asset"],
        target_specification["asset_sha256"],
    )
    calibration_specification = specification["calibration"]
    calibration_path = _verified_path(
        ASSET_DIR,
        calibration_specification["asset"],
        calibration_specification["asset_sha256"],
    )
    calibration = json.loads(calibration_path.read_text())
    threshold = calibration["white_threshold"]

    target_image = np.asarray(Image.open(target_path).convert("L"))
    target = target_image < threshold
    width_px, height_px = calibration["image_size_px"]
    if target.shape != (height_px, width_px):
        raise ValueError(
            f"Target shape {target.shape} does not match stored image size "
            f"{(height_px, width_px)}."
        )
    if _foreground_bbox(target) != calibration["bbox"]:
        raise ValueError("Target foreground bounds do not match calibration.json.")

    bbox_width, bbox_height = calibration["bbox_size_px"]
    footprint_width, footprint_height = calibration["footprint_um"]
    expected_scale = [
        bbox_width / footprint_width,
        bbox_height / footprint_height,
    ]
    if not np.allclose(expected_scale, calibration["scale_px_per_um"]):
        raise ValueError("Stored pixels-per-micron calibration is inconsistent.")

    iterations = []
    for iteration_specification in specification["iterations"]:
        raster_path = _verified_path(
            ASSET_DIR,
            iteration_specification["raster_asset"],
            iteration_specification["raster_sha256"],
        )
        metrics_path = _verified_path(
            ASSET_DIR,
            iteration_specification["metrics_asset"],
            iteration_specification["metrics_sha256"],
        )
        raster_image = np.asarray(Image.open(raster_path).convert("L"))
        if raster_image.shape != target.shape:
            raise ValueError(f"Raster shape mismatch for {raster_path}.")
        candidate = raster_image < threshold
        stored_metrics = json.loads(metrics_path.read_text())
        measured = _measure(candidate, target)
        for key in ("IoU", "Dice", "SSE"):
            if not np.isclose(measured[key], stored_metrics[key], atol=1e-12):
                raise ValueError(
                    f"{key} mismatch for iteration "
                    f"{iteration_specification['iteration']}."
                )
        iterations.append(
            {
                "iteration": iteration_specification["iteration"],
                "candidate": candidate,
                "metrics": stored_metrics,
            }
        )

    return {
        "target": target,
        "calibration": calibration,
        "iterations": iterations,
    }


def _rgb_mask(mask: np.ndarray, color: str) -> np.ndarray:
    image = np.full((*mask.shape, 3), 255, dtype=np.uint8)
    image[mask] = np.rint(np.asarray(to_rgb(color)) * 255).astype(np.uint8)
    return image


def _comparison_image(target: np.ndarray, candidate: np.ndarray) -> np.ndarray:
    image = np.full((*target.shape, 3), 255, dtype=np.uint8)
    overlap = np.logical_and(target, candidate)
    candidate_only = np.logical_and(candidate, ~target)
    target_only = np.logical_and(target, ~candidate)
    image[overlap] = np.rint(np.asarray(to_rgb(INK)) * 255).astype(np.uint8)
    image[candidate_only] = np.rint(
        np.asarray(to_rgb(CRIMSON)) * 255
    ).astype(np.uint8)
    image[target_only] = np.rint(
        np.asarray(to_rgb(DIFF_BLUE)) * 255
    ).astype(np.uint8)
    return image


def _difference_image(target: np.ndarray, candidate: np.ndarray) -> np.ndarray:
    image = np.full((*target.shape, 3), 255, dtype=np.uint8)
    candidate_only = np.logical_and(candidate, ~target)
    target_only = np.logical_and(target, ~candidate)
    image[candidate_only] = np.rint(
        np.asarray(to_rgb(CRIMSON)) * 255
    ).astype(np.uint8)
    image[target_only] = np.rint(
        np.asarray(to_rgb(DIFF_BLUE)) * 255
    ).astype(np.uint8)
    return image


def _section_title(
    fig: plt.Figure,
    letter: str,
    title: str,
    *,
    y: float,
) -> None:
    fig.text(
        0.020,
        y,
        letter,
        ha="left",
        va="center",
        fontsize=10.5,
        fontweight="bold",
        color=INK,
    )
    fig.text(
        0.056,
        y,
        title,
        ha="left",
        va="center",
        fontsize=10.5,
        fontweight="semibold",
        color=INK,
    )


def _card(
    fig: plt.Figure,
    rect: tuple[float, float, float, float],
    title: str,
    meta: str | None = None,
    *,
    meta_color: str = INK,
) -> plt.Axes:
    card = fig.add_axes(rect)
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
        0.035,
        0.905,
        title,
        ha="left",
        va="center",
        fontsize=8.7,
        fontweight="bold",
        color=INK,
    )
    if meta:
        card.text(
            0.965,
            0.905,
            meta,
            ha="right",
            va="center",
            fontsize=8.0,
            fontweight="semibold",
            color=meta_color,
        )
    return card


def _image_axes(
    card: plt.Axes,
    image: np.ndarray,
    *,
    bounds: tuple[float, float, float, float] = (0.035, 0.12, 0.93, 0.67),
) -> plt.Axes:
    image_axes = card.inset_axes(bounds)
    image_axes.imshow(image, interpolation="antialiased", aspect="equal")
    image_axes.set_xticks([])
    image_axes.set_yticks([])
    for spine in image_axes.spines.values():
        spine.set_visible(False)
    return image_axes


def _target_card(
    fig: plt.Figure,
    rect: tuple[float, float, float, float],
    target: np.ndarray,
    calibration: dict,
) -> None:
    footprint_width, footprint_height = calibration["footprint_um"]
    card = _card(
        fig,
        rect,
        r"Target $y$",
        rf"${footprint_width:g}\times{footprint_height:g}\,\mathrm{{\mu m}}$",
    )
    image = _rgb_mask(target, INK)
    image_axes = _image_axes(card, image, bounds=(0.035, 0.105, 0.91, 0.70))

    x0, y0, x1, y1 = calibration["bbox"]
    width_px, height_px = calibration["image_size_px"]
    image_axes.set_xlim(-16, width_px + 74)
    image_axes.set_ylim(height_px + 18, -18)
    image_axes.add_patch(
        Rectangle(
            (x0, y0),
            x1 - x0,
            y1 - y0,
            fill=False,
            edgecolor=VERIFIED,
            linewidth=1.15,
            zorder=4,
        )
    )
    arrow = {
        "arrowstyle": "<->",
        "color": VERIFIED,
        "linewidth": 0.72,
        "shrinkA": 0,
        "shrinkB": 0,
    }
    dimension_y = y1 + 68
    image_axes.annotate(
        "",
        xy=(x0, dimension_y),
        xytext=(x1, dimension_y),
        arrowprops=arrow,
        annotation_clip=False,
    )
    image_axes.text(
        (x0 + x1) / 2,
        dimension_y + 20,
        f"{x1 - x0} px",
        ha="center",
        va="top",
        fontsize=6.7,
        color=VERIFIED,
    )
    dimension_x = width_px + 34
    image_axes.annotate(
        "",
        xy=(dimension_x, y0),
        xytext=(dimension_x, y1),
        arrowprops=arrow,
        annotation_clip=False,
    )
    image_axes.text(
        dimension_x + 20,
        (y0 + y1) / 2,
        f"{y1 - y0} px",
        ha="center",
        va="center",
        rotation=90,
        fontsize=6.7,
        color=VERIFIED,
    )


def _candidate_card(
    fig: plt.Figure,
    rect: tuple[float, float, float, float],
    candidate: np.ndarray,
    metrics: dict,
) -> None:
    card = _card(
        fig,
        rect,
        r"Candidate render $\hat{y}_1$",
        "Iteration 1",
    )
    _image_axes(
        card,
        _rgb_mask(candidate, DIFF_BLUE),
        bounds=(0.035, 0.17, 0.93, 0.61),
    )
    gds_width, gds_height = metrics["gds_size_um"]
    card.text(
        0.5,
        0.075,
        rf"Output ${gds_width:.2f}\times{gds_height:.2f}\,\mathrm{{\mu m}}$",
        ha="center",
        va="center",
        fontsize=7.3,
        color=MUTED,
    )


def _calibration_operator(
    fig: plt.Figure,
    rect: tuple[float, float, float, float],
    calibration: dict,
) -> None:
    axes = fig.add_axes(rect)
    axes.set_xlim(0, 1)
    axes.set_ylim(0, 1)
    axes.axis("off")
    bbox_width, bbox_height = calibration["bbox_size_px"]
    footprint_width, footprint_height = calibration["footprint_um"]
    scale_x, scale_y = calibration["scale_px_per_um"]
    axes.text(
        0.5,
        0.88,
        "Fixed calibration",
        ha="center",
        va="center",
        fontsize=8.7,
        fontweight="bold",
        color=VERIFIED,
    )
    axes.text(
        0.5,
        0.67,
        rf"$\kappa_x={bbox_width}\,\mathrm{{px}}/"
        rf"{footprint_width:g}\,\mathrm{{\mu m}}"
        rf"={scale_x:g}\,\mathrm{{px/\mu m}}$",
        ha="center",
        va="center",
        fontsize=8.1,
        color=INK,
    )
    axes.text(
        0.5,
        0.50,
        rf"$\kappa_y={bbox_height}\,\mathrm{{px}}/"
        rf"{footprint_height:g}\,\mathrm{{\mu m}}"
        rf"={scale_y:g}\,\mathrm{{px/\mu m}}$",
        ha="center",
        va="center",
        fontsize=8.1,
        color=INK,
    )
    axes.add_patch(
        FancyArrowPatch(
            (0.08, 0.25),
            (0.92, 0.25),
            arrowstyle="-|>",
            mutation_scale=11,
            linewidth=0.92,
            color=INK,
            shrinkA=0,
            shrinkB=0,
        )
    )
    axes.text(
        0.5,
        0.31,
        r"Render at $\kappa$",
        ha="center",
        va="bottom",
        fontsize=7.5,
        color=INK,
    )
    axes.text(
        0.5,
        0.07,
        "No fit-to-target rescaling",
        ha="center",
        va="center",
        fontsize=7.1,
        color=MUTED,
    )


def _diagnostic_card(
    fig: plt.Figure,
    rect: tuple[float, float, float, float],
    title: str,
    image: np.ndarray,
    meta: str | None = None,
    *,
    meta_color: str = INK,
) -> None:
    card = _card(fig, rect, title, meta, meta_color=meta_color)
    _image_axes(card, image, bounds=(0.035, 0.095, 0.93, 0.69))


def _feedback_operator(
    fig: plt.Figure,
    rect: tuple[float, float, float, float],
    delta_iou: float,
) -> None:
    axes = fig.add_axes(rect)
    axes.set_xlim(0, 1)
    axes.set_ylim(0, 1)
    axes.axis("off")
    axes.text(
        0.5,
        0.72,
        "feedback-guided\nrevision",
        ha="center",
        va="center",
        fontsize=7.3,
        linespacing=1.15,
        color=VERIFIED,
        fontweight="semibold",
    )
    axes.add_patch(
        FancyArrowPatch(
            (0.06, 0.50),
            (0.94, 0.50),
            arrowstyle="-|>",
            mutation_scale=11,
            linewidth=1.0,
            color=VERIFIED,
            shrinkA=0,
            shrinkB=0,
        )
    )
    axes.text(
        0.5,
        0.28,
        rf"$\Delta\mathrm{{IoU}}=+{delta_iou:.3f}$",
        ha="center",
        va="center",
        fontsize=7.4,
        color=VERIFIED,
        fontweight="semibold",
    )


def _legend(fig: plt.Figure) -> None:
    fig.text(
        0.205,
        0.035,
        "Pixel classes:",
        ha="right",
        va="center",
        fontsize=7.3,
        color=MUTED,
    )
    entries = (
        (0.222, INK, "overlap"),
        (0.372, CRIMSON, "spurious (candidate only)"),
        (0.665, DIFF_BLUE, "missing (target only)"),
    )
    for x, color, label in entries:
        fig.add_artist(
            Rectangle(
                (x, 0.026),
                0.010,
                0.018,
                transform=fig.transFigure,
                facecolor=color,
                edgecolor="none",
            )
        )
        fig.text(
            x + 0.016,
            0.035,
            label,
            ha="left",
            va="center",
            fontsize=7.3,
            color=INK,
        )


def main() -> None:
    inputs = _load_inputs()
    target = inputs["target"]
    calibration = inputs["calibration"]
    first, second = inputs["iterations"]
    candidate_first = first["candidate"]
    candidate_second = second["candidate"]
    metrics_first = first["metrics"]
    metrics_second = second["metrics"]

    fig = plt.figure(figsize=(7.40, 2.75), facecolor="white")

    _section_title(fig, "A", "Fixed-calibration rendering", y=0.965)
    _target_card(fig, (0.020, 0.575, 0.310, 0.345), target, calibration)
    _calibration_operator(fig, (0.350, 0.605, 0.300, 0.270), calibration)
    _candidate_card(
        fig,
        (0.670, 0.575, 0.310, 0.345),
        candidate_first,
        metrics_first,
    )

    fig.add_artist(
        Line2D(
            [0.020, 0.980],
            [0.535, 0.535],
            transform=fig.transFigure,
            color=RULE,
            linewidth=0.72,
        )
    )
    _section_title(
        fig,
        "B",
        "Deterministic comparison and feedback",
        y=0.495,
    )

    _diagnostic_card(
        fig,
        (0.020, 0.080, 0.270, 0.355),
        "Pixelwise overlay",
        _comparison_image(target, candidate_first),
        "Iteration 1",
    )
    _diagnostic_card(
        fig,
        (0.310, 0.080, 0.270, 0.355),
        "Signed difference",
        _difference_image(target, candidate_first),
        rf"$\mathrm{{IoU}}={metrics_first['IoU']:.3f}$",
    )
    delta_iou = metrics_second["IoU"] - metrics_first["IoU"]
    _feedback_operator(fig, (0.595, 0.115, 0.120, 0.270), delta_iou)
    _diagnostic_card(
        fig,
        (0.730, 0.080, 0.250, 0.355),
        "Residual difference",
        _difference_image(target, candidate_second),
        rf"$\mathrm{{IoU}}={metrics_second['IoU']:.3f}$",
        meta_color=VERIFIED,
    )
    _legend(fig)

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    output = FIGURE_DIR / "fig_verification.pdf"
    fig.savefig(output, dpi=600, facecolor="white", bbox_inches=None)
    print(f"wrote {output}")
    plt.close(fig)


if __name__ == "__main__":
    main()
