"""Render Figure 9: model evaluation and the complete benchmark matrix.

The panels share one configuration order. Panel A shows visual score and
median API-equivalent cost on aligned axes; panel B shows the target-level
IoU matrix. The generator verifies its frozen inputs and recomputes both raw
and source-compliant scores from the cell-level sweep before plotting.

Run from the repository root:
    python arxiv/scripts/make_fig_emergence.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import mean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D


REPO = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__file__).with_name("fig_emergence_assets")
MANIFEST = ASSET_DIR / "manifest.json"
FIGURE_DIR = REPO / "arxiv" / "figures"

INK = "#17191c"
SOFT_INK = "#555a60"
RULE = "#17191c"
GRID = "#e2e4e6"
GROUP_RULE = "#cfd2d5"
CRIMSON = "#a31f34"
VERIFIED = "#267c5a"
DIFF_BLUE = "#315e9f"
PROVIDER_COLORS = {
    "openai": DIFF_BLUE,
    "anthropic": CRIMSON,
}
MATRIX_CMAP = LinearSegmentedColormap.from_list(
    "pixcell_rgb",
    (
        (0.00, "#f5dadd"),
        (0.22, "#d78a99"),
        (0.50, "#8ea9cc"),
        (0.68, DIFF_BLUE),
        (0.84, "#5e9a80"),
        (1.00, "#174f3b"),
    ),
)

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


# Base model names appear once in the hierarchical row labels. Effort labels
# distinguish repeated configurations without repeating the full model name.
BENCHMARK_CONFIGS = [
    ("GPT-5.5", "xhigh", "codex55x", "openai"),
    ("GPT-5.5", "high", "codex55h", "openai"),
    ("GPT-5.5", "med", "codex55m", "openai"),
    ("Opus 4.8", "med", "opus48m", "anthropic"),
    ("Opus 4.8", "max", "opus48max", "anthropic"),
    ("GPT-5.4", "", "codex54m", "openai"),
    ("Sonnet 5", "", "sonnet5m", "anthropic"),
    ("GPT-5.3 spark", "", "codexspark", "openai"),
    ("GPT-5.4-mini", "", "codex54mini", "openai"),
    ("Opus 4.5", "", "opus45m", "anthropic"),
    ("Haiku 4.5", "high", "haiku45h", "anthropic"),
    ("Haiku 4.5", "med", "haiku45m", "anthropic"),
    ("Sonnet 4.5", "", "sonnet45m", "anthropic"),
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verified_json(asset: str, expected_sha256: str):
    path = (ASSET_DIR / asset).resolve()
    actual = _sha256(path)
    if actual != expected_sha256:
        raise ValueError(
            f"Hash mismatch for {path}: expected {expected_sha256}, got {actual}."
        )
    return json.loads(path.read_text())


def _load_benchmark() -> list[dict]:
    specification = json.loads(MANIFEST.read_text())
    sweep_specification = specification["coding_agent_sweep"]
    sweep_source = _verified_json(
        sweep_specification["asset"],
        sweep_specification["sha256"],
    )["cells"]
    economics_specification = specification["configuration_economics"]
    economics_source = _verified_json(
        economics_specification["asset"],
        economics_specification["sha256"],
    )

    expected_targets = int(sweep_specification["expected_targets_per_configuration"])
    target_names = [f"final{index}" for index in range(1, expected_targets + 1)]
    economics_by_configuration = {
        row["config"]: row for row in economics_source
    }
    expected_configurations = {
        configuration for _, _, configuration, _ in BENCHMARK_CONFIGS
    }
    if set(economics_by_configuration) != expected_configurations:
        raise ValueError(
            "The configuration economics record does not match the benchmark "
            f"contract: {sorted(economics_by_configuration)}."
        )

    benchmark = []
    for model, effort, configuration, provider in BENCHMARK_CONFIGS:
        cells = [cell for cell in sweep_source if cell["config"] == configuration]
        if len(cells) != expected_targets:
            raise ValueError(
                f"Expected {expected_targets} cells for {configuration}, got {len(cells)}."
            )
        by_target = {cell["device"]: cell for cell in cells}
        if set(by_target) != set(target_names):
            raise ValueError(
                f"Unexpected target set for {configuration}: {sorted(by_target)}."
            )

        values = [
            float(by_target[target]["iou"])
            if by_target[target]["iou"] is not None
            else float("nan")
            for target in target_names
        ]
        violations = [
            bool(by_target[target]["purity_violation"])
            for target in target_names
        ]
        raw_score = float(np.nanmean(values))
        usable_terms = [
            0.0 if violation or np.isnan(value) else value
            for value, violation in zip(values, violations)
        ]
        usable_score = mean(usable_terms)

        economics = economics_by_configuration[configuration]
        if int(economics["n"]) != expected_targets:
            raise ValueError(f"Unexpected economics n for {configuration}.")
        if int(economics["violations"]) != sum(violations):
            raise ValueError(f"Violation count does not reconcile for {configuration}.")
        if not np.isclose(raw_score, float(economics["mean_iou"]), atol=5.1e-4):
            raise ValueError(f"Raw IoU does not reconcile for {configuration}.")
        if not np.isclose(
            usable_score,
            float(economics["usable_iou"]),
            atol=5.1e-4,
        ):
            raise ValueError(f"Usable IoU does not reconcile for {configuration}.")
        cost = float(economics["median_api_equiv_cost_usd"])
        if not np.isfinite(cost) or cost <= 0:
            raise ValueError(f"Invalid median cost for {configuration}: {cost}.")

        benchmark.append(
            {
                "model": model,
                "effort": effort,
                "configuration": configuration,
                "provider": provider,
                "values": values,
                "violations": violations,
                "raw_score": raw_score,
                "usable_score": usable_score,
                "cost": cost,
            }
        )

    return benchmark


def _groups(benchmark: list[dict]) -> list[tuple[str, int, int]]:
    groups = []
    start = 0
    while start < len(benchmark):
        model = benchmark[start]["model"]
        end = start
        while end + 1 < len(benchmark) and benchmark[end + 1]["model"] == model:
            end += 1
        groups.append((model, start, end))
        start = end + 1
    return groups


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


def _provider_legend(figure: plt.Figure) -> None:
    handles = [
        Line2D(
            [],
            [],
            marker="o",
            linestyle="none",
            markersize=4.0,
            markerfacecolor=color,
            markeredgecolor=color,
            label=label,
        )
        for label, color in (
            ("OpenAI", PROVIDER_COLORS["openai"]),
            ("Anthropic", PROVIDER_COLORS["anthropic"]),
        )
    ]
    figure.legend(
        handles=handles,
        loc="upper right",
        bbox_to_anchor=(0.592, 0.988),
        ncol=2,
        frameon=False,
        fontsize=5.9,
        handletextpad=0.35,
        columnspacing=0.8,
        borderaxespad=0,
    )


def _style_evaluation_axis(
    axes: plt.Axes,
    *,
    row_count: int,
) -> None:
    axes.set_ylim(row_count - 0.5, -0.5)
    axes.set_yticks([])
    axes.grid(axis="x", color=GRID, linewidth=0.5, zorder=0)
    axes.tick_params(
        axis="x",
        length=2.8,
        width=0.6,
        color=SOFT_INK,
        labelcolor=SOFT_INK,
        labelsize=6.2,
        pad=2,
    )
    for side in ("top", "right", "left"):
        axes.spines[side].set_visible(False)
    axes.spines["bottom"].set_color(SOFT_INK)
    axes.spines["bottom"].set_linewidth(0.6)
    axes.set_facecolor("white")


def _draw_model_labels(
    axes: plt.Axes,
    benchmark: list[dict],
) -> list[float]:
    separators = []
    for model, start, end in _groups(benchmark):
        center = 0.5 * (start + end)
        axes.text(
            -0.340,
            center,
            model,
            transform=axes.get_yaxis_transform(),
            ha="left",
            va="center",
            fontsize=6.3,
            color=INK,
            clip_on=False,
        )
        for row_index in range(start, end + 1):
            effort = benchmark[row_index]["effort"]
            if effort:
                axes.text(
                    -0.034,
                    row_index,
                    effort,
                    transform=axes.get_yaxis_transform(),
                    ha="right",
                    va="center",
                    fontsize=5.75,
                    color=SOFT_INK,
                    clip_on=False,
                )
        if end < len(benchmark) - 1:
            separators.append(end + 0.5)
    return separators


def _draw_model_evaluation(
    score_axes: plt.Axes,
    cost_axes: plt.Axes,
    benchmark: list[dict],
) -> list[float]:
    rows = np.arange(len(benchmark))
    colors = [PROVIDER_COLORS[row["provider"]] for row in benchmark]
    score_axes.scatter(
        [row["usable_score"] for row in benchmark],
        rows,
        s=25,
        facecolor=colors,
        edgecolor="white",
        linewidth=0.35,
        zorder=3,
    )
    cost_axes.scatter(
        [row["cost"] for row in benchmark],
        rows,
        s=25,
        facecolor=colors,
        edgecolor="white",
        linewidth=0.35,
        zorder=3,
    )

    _style_evaluation_axis(score_axes, row_count=len(benchmark))
    _style_evaluation_axis(cost_axes, row_count=len(benchmark))
    score_axes.set_xlim(0, 1.01)
    score_axes.set_xticks([0, 0.5, 1.0])
    score_axes.set_xticklabels(["0", "0.5", "1.0"])
    score_axes.set_title(
        r"Visual score $U$",
        fontsize=7.25,
        color=INK,
        pad=5,
    )
    cost_axes.set_xscale("log")
    cost_axes.set_xlim(0.65, 100)
    cost_axes.set_xticks([1, 10, 100])
    cost_axes.set_xticklabels(["$1", "$10", "$100"])
    cost_axes.minorticks_off()
    cost_axes.set_title(
        "Median cost",
        fontsize=7.25,
        color=INK,
        pad=5,
    )

    separators = _draw_model_labels(score_axes, benchmark)
    for separator in separators:
        score_axes.axhline(separator, color=GROUP_RULE, linewidth=0.55, zorder=1)
        cost_axes.axhline(separator, color=GROUP_RULE, linewidth=0.55, zorder=1)
    return separators


def _draw_benchmark_matrix(
    figure: plt.Figure,
    axes: plt.Axes,
    colorbar_axes: plt.Axes,
    benchmark: list[dict],
    separators: list[float],
) -> None:
    values = np.asarray([row["values"] for row in benchmark])
    image = axes.imshow(
        values,
        cmap=MATRIX_CMAP,
        vmin=0,
        vmax=1,
        aspect="auto",
        interpolation="nearest",
    )
    axes.set_xticks(range(8))
    axes.set_xticklabels([f"F{index}" for index in range(1, 9)], fontsize=6.4)
    axes.set_yticks([])
    axes.set_xticks(np.arange(0.5, 7.5, 1), minor=True)
    axes.set_yticks(np.arange(0.5, len(benchmark) - 0.5, 1), minor=True)
    axes.grid(which="minor", color="white", linewidth=0.55)
    axes.tick_params(which="minor", length=0)
    axes.tick_params(axis="x", length=0)
    axes.set_xlabel("Target device", fontsize=7.2, labelpad=3, color=INK)

    for row_index, row in enumerate(benchmark):
        for column_index, is_violation in enumerate(row["violations"]):
            if not is_violation:
                continue
            value = row["values"][column_index]
            red, green, blue, _ = image.cmap(image.norm(value))
            luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
            axes.text(
                column_index,
                row_index,
                r"$\times$",
                ha="center",
                va="center",
                fontsize=6.4,
                color="white" if luminance < 0.54 else INK,
            )
    for separator in separators:
        axes.axhline(separator, color="white", linewidth=1.15, zorder=3)
    for spine in axes.spines.values():
        spine.set_visible(False)

    colorbar = figure.colorbar(
        image,
        cax=colorbar_axes,
        ticks=[0, 0.5, 1.0],
    )
    colorbar.set_label("IoU", fontsize=7.0, labelpad=3)
    colorbar.ax.tick_params(labelsize=6.1, length=2.5, width=0.55)
    colorbar.outline.set_visible(False)


def main() -> None:
    benchmark = _load_benchmark()

    figure = plt.figure(figsize=(7.40, 3.30), facecolor="white")
    # Model names begin on the same left anchor as panel A. The two
    # quantitative axes then use the remaining panel width instead of being
    # compressed behind a large invisible label gutter.
    score_axes = figure.add_axes((0.120, 0.145, 0.295, 0.715))
    cost_axes = figure.add_axes((0.438, 0.145, 0.142, 0.715))
    # Panel B starts at the same horizontal anchor as its heading. Give the
    # benchmark cells the full panel width and reserve only a narrow outer
    # strip for the IoU scale.
    matrix_axes = figure.add_axes((0.615, 0.145, 0.330, 0.715))
    colorbar_axes = figure.add_axes((0.958, 0.145, 0.010, 0.715))

    separators = _draw_model_evaluation(
        score_axes,
        cost_axes,
        benchmark,
    )
    _draw_benchmark_matrix(
        figure,
        matrix_axes,
        colorbar_axes,
        benchmark,
        separators,
    )
    _panel_heading(
        figure,
        x=0.018,
        letter="A",
        title="Model evaluation",
        rule_end=0.595,
    )
    _panel_heading(
        figure,
        x=0.615,
        letter="B",
        title="Benchmark matrix",
        rule_end=0.980,
    )
    _provider_legend(figure)

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    output = FIGURE_DIR / "fig1_emergence.pdf"
    figure.savefig(output, dpi=600, facecolor="white", bbox_inches=None)
    print(f"wrote {output}")
    plt.close(figure)


if __name__ == "__main__":
    main()
