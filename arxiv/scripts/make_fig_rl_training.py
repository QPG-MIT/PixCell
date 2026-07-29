"""Render the Run B curriculum-training figure from its frozen record.

Panel A follows the 150 GRPO updates through L0--L4. Panel B evaluates the
same six checkpoints on one fixed 80-task probe, with 16 held-out parameter
settings at each representation level.

Run from the repository root:
    uv run python arxiv/scripts/make_fig_rl_training.py
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D


REPO = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__file__).with_name("fig_rl_assets")
MANIFEST = ASSET_DIR / "manifest.json"
TELEMETRY = ASSET_DIR / "training_telemetry.json"
FIGURE_DIR = REPO / "arxiv" / "figures"

INK = "#17191c"
SOFT_INK = "#555a60"
RULE = "#17191c"
GRID = "#e2e4e6"
CRIMSON = "#a31f34"
DIFF_BLUE = "#315e9f"
STAGE_FILL = ("#f4f6f8", "#ffffff")
LEVELS = tuple(f"L{index}" for index in range(5))
CHECKPOINT_LABELS = ("Base", "+L0", "+L1", "+L2", "+L3", "+L4")

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
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.facecolor": "white",
        "savefig.bbox": None,
    }
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_data() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    expected = manifest["assets"][TELEMETRY.name]["sha256"]
    actual = _sha256(TELEMETRY)
    if actual != expected:
        raise ValueError(
            f"Hash mismatch for {TELEMETRY}: expected {expected}, got {actual}."
        )
    data = json.loads(TELEMETRY.read_text())
    if data["levels"] != list(LEVELS):
        raise ValueError("Run B telemetry does not contain the ordered L0--L4 levels.")
    training = data["training"]
    if len(training) != 150:
        raise ValueError("Run B figure requires exactly 150 training steps.")
    if [record["step"] for record in training] != list(range(1, 151)):
        raise ValueError("Run B training steps must be contiguous.")
    if len(data["probes"]) != 6:
        raise ValueError("Run B figure requires base plus five post-stage probes.")
    for probe in data["probes"]:
        if any(probe["per_level"][level]["n"] != 16 for level in LEVELS):
            raise ValueError("Every fixed-probe cell must contain 16 tasks.")
    return data


def _panel_heading(
    figure: plt.Figure,
    *,
    x: float,
    letter: str,
    title: str,
    rule_end: float,
) -> None:
    figure.text(
        x,
        0.965,
        letter,
        ha="left",
        va="center",
        fontsize=9.8,
        color=INK,
    )
    figure.text(
        x + 0.034,
        0.965,
        title,
        ha="left",
        va="center",
        fontsize=9.8,
        color=INK,
    )
    figure.add_artist(
        Line2D(
            [x, rule_end],
            [0.925, 0.925],
            transform=figure.transFigure,
            color=RULE,
            linewidth=0.68,
        )
    )


def _rolling(values: list[float], window: int = 5) -> list[float]:
    return [
        sum(values[max(0, index - window + 1) : index + 1])
        / len(values[max(0, index - window + 1) : index + 1])
        for index in range(len(values))
    ]


def _style_training_axis(axes: plt.Axes) -> None:
    axes.spines["top"].set_visible(False)
    axes.spines["right"].set_visible(False)
    axes.spines["left"].set_linewidth(0.68)
    axes.spines["bottom"].set_linewidth(0.68)
    axes.tick_params(
        axis="both",
        labelsize=7.1,
        width=0.6,
        length=3.0,
        pad=2.5,
        color=SOFT_INK,
        labelcolor=INK,
    )
    axes.grid(axis="y", color=GRID, linewidth=0.52, zorder=0)
    axes.set_axisbelow(True)
    axes.set_xlim(0.5, 150.5)
    axes.set_ylim(0.0, 0.52)
    axes.set_xticks((1, 30, 60, 90, 120, 150))
    axes.set_yticks(np.arange(0.0, 0.51, 0.1))
    axes.set_xlabel("Cumulative GRPO step", fontsize=8.0, labelpad=3.5)
    axes.set_ylabel("Mean score", fontsize=8.0, labelpad=3.5)


def _draw_training(axes: plt.Axes, data: dict) -> None:
    records = data["training"]
    steps = np.asarray([record["step"] for record in records])
    iou = np.asarray([record["mean_iou"] for record in records])
    shaped = np.asarray([record["mean_shaped"] for record in records])

    for level_index, level in enumerate(LEVELS):
        start = level_index * 30 + 0.5
        end = (level_index + 1) * 30 + 0.5
        axes.axvspan(
            start,
            end,
            color=STAGE_FILL[level_index % 2],
            linewidth=0,
            zorder=-2,
        )
        axes.text(
            0.5 * (start + end),
            0.985,
            level,
            transform=axes.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=6.8,
            color=SOFT_INK,
        )
        if level_index:
            axes.axvline(
                start,
                color="#aeb3b7",
                linewidth=0.65,
                linestyle=(0, (2.0, 2.5)),
                zorder=1,
            )

    axes.scatter(
        steps,
        iou,
        s=5.0,
        color=DIFF_BLUE,
        alpha=0.16,
        linewidths=0,
        zorder=2,
    )
    axes.scatter(
        steps,
        shaped,
        s=5.0,
        color=CRIMSON,
        alpha=0.14,
        linewidths=0,
        zorder=2,
    )

    iou_handle = None
    shaped_handle = None
    for level_index in range(5):
        start = level_index * 30
        end = start + 30
        segment_steps = steps[start:end]
        current_iou = axes.plot(
            segment_steps,
            _rolling(iou[start:end].tolist()),
            color=DIFF_BLUE,
            linewidth=1.35,
            zorder=3,
        )[0]
        current_shaped = axes.plot(
            segment_steps,
            _rolling(shaped[start:end].tolist()),
            color=CRIMSON,
            linewidth=1.25,
            zorder=3,
        )[0]
        if iou_handle is None:
            iou_handle = current_iou
        if shaped_handle is None:
            shaped_handle = current_shaped

    _style_training_axis(axes)
    axes.legend(
        handles=(iou_handle, shaped_handle),
        labels=("Batch IoU · 5-step mean", "Shaped reward · 5-step mean"),
        loc="lower center",
        bbox_to_anchor=(0.5, 1.015),
        ncol=2,
        frameon=False,
        fontsize=6.7,
        handlelength=1.65,
        handletextpad=0.38,
        columnspacing=0.9,
        borderaxespad=0.0,
    )


def _draw_probe(axes: plt.Axes, data: dict, figure: plt.Figure) -> None:
    row_labels = (*LEVELS, "All")
    checkpoint_labels = [
        f"{label}*" if probe["condition"] == "evaluation_contention" else label
        for label, probe in zip(CHECKPOINT_LABELS, data["probes"])
    ]
    matrix = np.asarray(
        [
            [
                (
                    probe["overall"]["mean_iou"]
                    if level == "All"
                    else probe["per_level"][level]["mean_iou"]
                )
                for probe in data["probes"]
            ]
            for level in row_labels
        ],
        dtype=float,
    )
    if not np.isfinite(matrix).all() or matrix.min() < 0.0 or matrix.max() > 1.0:
        raise ValueError("Fixed-probe IoU matrix is invalid.")

    upper = max(0.35, math.ceil(float(matrix.max()) * 20.0) / 20.0)
    cmap = LinearSegmentedColormap.from_list(
        "pixcell_probe",
        ("#f7f9fc", "#dbe4f1", "#91a9c9", DIFF_BLUE),
    )
    image = axes.imshow(
        matrix,
        cmap=cmap,
        vmin=0.0,
        vmax=upper,
        interpolation="nearest",
        aspect="auto",
    )
    axes.set_xticks(range(6), labels=checkpoint_labels)
    axes.set_yticks(range(6), labels=row_labels)
    axes.tick_params(
        axis="both",
        which="major",
        length=0,
        labelsize=7.0,
        pad=3.0,
        colors=INK,
    )
    axes.set_xlabel("Checkpoint", fontsize=8.0, labelpad=4.0)
    axes.set_ylabel("Probe level", fontsize=8.0, labelpad=4.0)
    axes.set_xticks(np.arange(-0.5, 6.0, 1.0), minor=True)
    axes.set_yticks(np.arange(-0.5, 6.0, 1.0), minor=True)
    axes.grid(which="minor", color="white", linewidth=1.1)
    axes.tick_params(which="minor", bottom=False, left=False)
    axes.axhline(4.5, color=INK, linewidth=0.72)
    for spine in axes.spines.values():
        spine.set_visible(False)

    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            value = matrix[row, column]
            axes.text(
                column,
                row,
                f"{value:.2f}",
                ha="center",
                va="center",
                fontsize=6.8,
                color="white" if value >= 0.62 * upper else INK,
            )

    bounds = axes.get_position()
    color_axes = figure.add_axes(
        (
            bounds.x1 + 0.012,
            bounds.y0 + 0.014,
            0.010,
            bounds.height - 0.028,
        )
    )
    colorbar = figure.colorbar(image, cax=color_axes)
    colorbar.outline.set_linewidth(0.55)
    colorbar.set_ticks((0.0, upper))
    colorbar.ax.tick_params(
        labelsize=6.4,
        width=0.5,
        length=2.0,
        pad=2.0,
        colors=INK,
    )
    colorbar.set_label("Mean IoU", fontsize=7.1, labelpad=2.5)


def main() -> None:
    data = _load_data()
    figure = plt.figure(figsize=(7.40, 2.88), facecolor="white")
    training_axes = figure.add_axes((0.070, 0.175, 0.500, 0.640))
    probe_axes = figure.add_axes((0.630, 0.175, 0.292, 0.640))

    _panel_heading(
        figure,
        x=0.020,
        letter="A",
        title="Run B curriculum optimization",
        rule_end=0.590,
    )
    _panel_heading(
        figure,
        x=0.605,
        letter="B",
        title="Fixed cross-level probe",
        rule_end=0.980,
    )
    _draw_training(training_axes, data)
    _draw_probe(probe_axes, data, figure)

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    output = FIGURE_DIR / "fig_rl_training.pdf"
    figure.savefig(output, dpi=600, facecolor="white", bbox_inches=None)
    plt.close(figure)
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
