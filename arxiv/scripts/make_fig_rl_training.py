"""Render Figure 12 from the frozen RL telemetry record.

Panel A shows scheduled synthetic evaluations for tiers L0--L3. Panel B
compares the recorded L4 training trace with the training-excluded benchmark
and the final best-of-eight draw. The compact source record is hash-locked in
``fig_rl_assets/manifest.json``.

Run from the repository root:
    python arxiv/scripts/make_fig_rl_training.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


REPO = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__file__).with_name("fig_rl_assets")
MANIFEST = ASSET_DIR / "manifest.json"
FIGURE_DIR = REPO / "arxiv" / "figures"

INK = "#17191c"
SOFT_INK = "#555a60"
RULE = "#17191c"
GRID = "#e2e4e6"
CRIMSON = "#a31f34"
VERIFIED = "#267c5a"
DIFF_BLUE = "#315e9f"
TIER_STYLE = {
    "L0": (DIFF_BLUE, "o", "-"),
    "L1": (CRIMSON, "s", "-"),
    "L2": (VERIFIED, "^", "-"),
    "L3": (INK, "D", (0, (4.0, 2.0))),
}

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
    path = ASSET_DIR / "training_telemetry.json"
    expected = manifest["assets"][path.name]["sha256"]
    actual = _sha256(path)
    if actual != expected:
        raise ValueError(
            f"Hash mismatch for {path}: expected {expected}, got {actual}."
        )
    data = json.loads(path.read_text())
    if len(data["evaluations"]) != 10:
        raise ValueError("Figure 12 requires ten scheduled evaluation checkpoints.")
    if [stage["start_step"] for stage in data["stages"]] != [0, 30, 65]:
        raise ValueError("Figure 12 stage boundaries do not match the paper record.")
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
        x + 0.035,
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


def _style_axis(axes: plt.Axes) -> None:
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
    axes.set_xlim(-2, 100)
    axes.set_ylim(0, 1.02)
    axes.set_xticks((0, 20, 40, 60, 80, 100))
    axes.set_yticks((0, 0.25, 0.5, 0.75, 1.0))
    axes.set_xlabel("Cumulative GRPO step", fontsize=8.0, labelpad=3.5)
    axes.set_ylabel("IoU", fontsize=8.0, labelpad=3.5)


def _draw_stages(axes: plt.Axes, stages: list[dict]) -> None:
    for boundary in (30, 65):
        axes.axvline(
            boundary,
            color="#aeb3b7",
            linewidth=0.65,
            linestyle=(0, (2.0, 2.5)),
            zorder=1,
        )
    boundaries = [stage["start_step"] for stage in stages] + [100]
    for stage, end in zip(stages, boundaries[1:]):
        axes.text(
            0.5 * (stage["start_step"] + end),
            0.975,
            stage["label"],
            transform=axes.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=6.25,
            color=SOFT_INK,
        )


def _rolling_mean(values: list[float], window: int = 5) -> list[float]:
    return [
        sum(values[max(0, index - window + 1) : index + 1])
        / len(values[max(0, index - window + 1) : index + 1])
        for index in range(len(values))
    ]


def _draw_synthetic(axes: plt.Axes, data: dict) -> None:
    evaluations = data["evaluations"]
    steps = [record["step"] for record in evaluations]
    for tier, (color, marker, line_style) in TIER_STYLE.items():
        axes.plot(
            steps,
            [record[tier] for record in evaluations],
            color=color,
            marker=marker,
            linestyle=line_style,
            linewidth=1.15,
            markersize=3.2,
            markeredgewidth=0.5,
            label=tier,
            zorder=3,
        )
    _style_axis(axes)
    _draw_stages(axes, data["stages"])
    axes.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.015),
        ncol=4,
        frameon=False,
        fontsize=6.7,
        handlelength=1.55,
        handletextpad=0.35,
        columnspacing=0.9,
        borderaxespad=0.0,
    )


def _draw_transfer(axes: plt.Axes, data: dict) -> None:
    training = data["training"]
    train_steps = [record["step"] for record in training]
    train_values = [record["iou"] for record in training]
    axes.plot(
        train_steps,
        train_values,
        color=CRIMSON,
        linewidth=0.55,
        alpha=0.20,
        zorder=2,
    )
    training_line = axes.plot(
        train_steps,
        _rolling_mean(train_values),
        color=CRIMSON,
        linewidth=1.35,
        label="L4 training · 5-step mean",
        zorder=3,
    )[0]

    evaluations = [
        record
        for record in data["evaluations"]
        if record["benchmark"] is not None
    ]
    benchmark_line = axes.plot(
        [record["step"] for record in evaluations],
        [record["benchmark"] for record in evaluations],
        color=DIFF_BLUE,
        marker="o",
        markerfacecolor="white",
        markeredgecolor=DIFF_BLUE,
        markeredgewidth=0.8,
        linewidth=0.95,
        markersize=3.3,
        label="Training-excluded benchmark",
        zorder=4,
    )[0]

    final = data["final_draw"]
    axes.plot(
        [95],
        [final["eval_at_1"]],
        marker="o",
        color=VERIFIED,
        markersize=4.3,
        zorder=5,
    )
    axes.plot(
        [95],
        [final["best_at_8"]],
        marker="D",
        markerfacecolor="white",
        markeredgecolor=VERIFIED,
        markeredgewidth=1.0,
        markersize=4.4,
        zorder=5,
    )
    axes.text(
        92.5,
        final["best_at_8"] + 0.035,
        f"best@8 {final['best_at_8']:.3f}",
        ha="right",
        va="bottom",
        fontsize=6.5,
        color=INK,
    )
    axes.text(
        92.5,
        final["eval_at_1"] - 0.035,
        f"eval@1 {final['eval_at_1']:.3f}",
        ha="right",
        va="top",
        fontsize=6.5,
        color=INK,
    )

    _style_axis(axes)
    _draw_stages(axes, data["stages"])
    endpoint_handle = Line2D(
        [],
        [],
        color=VERIFIED,
        marker="D",
        markerfacecolor="white",
        linewidth=0,
        markersize=3.8,
        label=r"Final $k{=}8$",
    )
    axes.legend(
        handles=(training_line, benchmark_line, endpoint_handle),
        loc="lower center",
        bbox_to_anchor=(0.5, 1.015),
        ncol=3,
        frameon=False,
        fontsize=6.35,
        handlelength=1.45,
        handletextpad=0.35,
        columnspacing=0.72,
        borderaxespad=0.0,
    )


def main() -> None:
    data = _load_data()
    figure = plt.figure(figsize=(7.40, 2.88), facecolor="white")
    synthetic_axes = figure.add_axes((0.070, 0.170, 0.405, 0.650))
    transfer_axes = figure.add_axes((0.565, 0.170, 0.405, 0.650))

    _panel_heading(
        figure,
        x=0.020,
        letter="A",
        title="Synthetic evaluation by tier",
        rule_end=0.490,
    )
    _panel_heading(
        figure,
        x=0.510,
        letter="B",
        title="Real-figure transfer",
        rule_end=0.980,
    )
    _draw_synthetic(synthetic_axes, data)
    _draw_transfer(transfer_axes, data)

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = FIGURE_DIR / "fig_rl_training.pdf"
    png_path = FIGURE_DIR / "fig_rl_training.png"
    figure.savefig(pdf_path, dpi=600, facecolor="white", bbox_inches=None)
    figure.savefig(png_path, dpi=300, facecolor="white", bbox_inches=None)
    plt.close(figure)
    print(f"wrote {pdf_path}")
    print(f"wrote {png_path}")


if __name__ == "__main__":
    main()
