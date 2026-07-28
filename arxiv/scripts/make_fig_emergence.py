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
# Left-gutter geometry, in axis-fraction units of the score axis.
FAMILY_LABEL_X = -0.62
EFFORT_LABEL_X = -0.085
GENERATION_TICK_X = -0.038

# A single-hue sequential ramp: IoU is one ordered quantity, so a multi-hue
# scale would imply categories that do not exist and reads as decoration.
MATRIX_CMAP = LinearSegmentedColormap.from_list(
    "pixcell_score",
    (
        (0.00, "#f7f4f2"),
        (0.30, "#dee6e1"),
        (0.55, "#b6cbc0"),
        (0.75, "#87ab98"),
        (0.88, "#548a6f"),
        (1.00, "#1d5240"),
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


# Base model names appear once in the hierarchical row labels; effort labels
# distinguish repeated configurations without repeating the model name. Families
# are ordered by their best configuration, and configurations within a family by
# score, so the vertical axis reads as a capability ranking. The fifth field
# marks the generation: "original" for the first sweep, "extension" for the
# later one run under the same protocol.
BENCHMARK_CONFIGS = [
    ("Fable 5", "max", "fable5max", "anthropic", "extension"),
    ("Fable 5", "med", "fable5m", "anthropic", "extension"),
    ("Opus 5", "max", "opus5max", "anthropic", "extension"),
    ("Opus 5", "med", "opus5m", "anthropic", "extension"),
    ("GPT-5.6 sol", "ultra", "codex56solu", "openai", "extension"),
    ("GPT-5.6 sol", "xhigh", "codex56solx", "openai", "extension"),
    ("GPT-5.6 sol", "med", "codex56solm", "openai", "extension"),
    ("GPT-5.5", "xhigh", "codex55x", "openai", "original"),
    ("GPT-5.5", "high", "codex55h", "openai", "original"),
    ("GPT-5.5", "med", "codex55m", "openai", "original"),
    ("Opus 4.8", "med", "opus48m", "anthropic", "original"),
    ("Opus 4.8", "max", "opus48max", "anthropic", "original"),
    ("GPT-5.6 terra", "xhigh", "codex56terrax", "openai", "extension"),
    ("GPT-5.6 terra", "ultra", "codex56terrau", "openai", "extension"),
    ("GPT-5.6 terra", "med", "codex56terram", "openai", "extension"),
    ("GPT-5.6 luna", "ultra", "codex56lunau", "openai", "extension"),
    ("GPT-5.6 luna", "xhigh", "codex56lunax", "openai", "extension"),
    ("GPT-5.6 luna", "med", "codex56lunam", "openai", "extension"),
    ("GPT-5.4", "", "codex54m", "openai", "original"),
    ("Sonnet 5", "", "sonnet5m", "anthropic", "original"),
    ("GPT-5.3 spark", "", "codexspark", "openai", "original"),
    ("GPT-5.4-mini", "", "codex54mini", "openai", "original"),
    ("Opus 4.5", "", "opus45m", "anthropic", "original"),
    ("Haiku 4.5", "high", "haiku45h", "anthropic", "original"),
    ("Haiku 4.5", "med", "haiku45m", "anthropic", "original"),
    ("Sonnet 4.5", "", "sonnet45m", "anthropic", "original"),
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
        configuration for _, _, configuration, _, _ in BENCHMARK_CONFIGS
    }
    if set(economics_by_configuration) != expected_configurations:
        raise ValueError(
            "The configuration economics record does not match the benchmark "
            f"contract: {sorted(economics_by_configuration)}."
        )

    benchmark = []
    for model, effort, configuration, provider, generation in BENCHMARK_CONFIGS:
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
        raw_cost = economics.get("median_api_equiv_cost_usd")
        # A configuration whose model has no published per-token price carries
        # no cost. That is recorded as an absence and drawn as one, never as a
        # zero and never as an estimate.
        cost = float(raw_cost) if raw_cost is not None else float("nan")
        if raw_cost is not None and (not np.isfinite(cost) or cost <= 0):
            raise ValueError(f"Invalid median cost for {configuration}: {cost}.")

        benchmark.append(
            {
                "model": model,
                "effort": effort,
                "configuration": configuration,
                "provider": provider,
                "generation": generation,
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
        0.972,
        letter,
        ha="left",
        va="center",
        fontsize=9.8,
        color=INK,
    )
    figure.text(
        x + 0.035,
        0.972,
        title,
        ha="left",
        va="center",
        fontsize=9.8,
        color=INK,
    )
    figure.add_artist(
        Line2D(
            [x, rule_end],
            [0.949, 0.949],
            transform=figure.transFigure,
            color=RULE,
            linewidth=0.68,
        )
    )


def _provider_legend(figure: plt.Figure) -> None:
    """Vendor colour, the only encoded categorical variable."""
    handles = [
        Line2D([], [], marker="o", linestyle="none", markersize=4.0,
               markerfacecolor=color, markeredgecolor=color, label=label)
        for label, color in (
            ("OpenAI", PROVIDER_COLORS["openai"]),
            ("Anthropic", PROVIDER_COLORS["anthropic"]),
        )
    ] + [
    ]
    figure.legend(
        handles=handles,
        loc="upper right",
        bbox_to_anchor=(0.600, 0.995),
        ncol=2,
        frameon=False,
        fontsize=5.9,
        handletextpad=0.35,
        columnspacing=0.9,
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
    """Family names and effort labels occupy separate, non-overlapping columns.

    The family name is left-aligned in its own gutter and the effort label sits
    in a narrow column immediately left of the axis, so a long family name can
    never run into the effort of the row beside it.
    """
    separators = []
    transform = axes.get_yaxis_transform()
    for model, start, end in _groups(benchmark):
        center = 0.5 * (start + end)
        axes.text(
            FAMILY_LABEL_X,
            center,
            model,
            transform=transform,
            ha="left",
            va="center",
            fontsize=6.4,
            color=INK,
            clip_on=False,
        )
        for row_index in range(start, end + 1):
            effort = benchmark[row_index]["effort"]
            if effort:
                axes.text(
                    EFFORT_LABEL_X,
                    row_index,
                    effort,
                    transform=transform,
                    ha="right",
                    va="center",
                    fontsize=5.6,
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
        s=20,
        facecolor=colors,
        edgecolor="white",
        linewidth=0.35,
        zorder=3,
    )

    priced = [(index, row) for index, row in enumerate(benchmark)
              if np.isfinite(row["cost"])]
    cost_axes.scatter(
        [row["cost"] for _, row in priced],
        [index for index, _ in priced],
        s=20,
        facecolor=[PROVIDER_COLORS[row["provider"]] for _, row in priced],
        edgecolor="white",
        linewidth=0.35,
        zorder=3,
    )

    _style_evaluation_axis(score_axes, row_count=len(benchmark))
    _style_evaluation_axis(cost_axes, row_count=len(benchmark))
    score_axes.set_xlim(0, 1.04)
    score_axes.set_xticks([0, 0.5, 1.0])
    score_axes.set_xticklabels(["0", "0.5", "1.0"])
    score_axes.set_title(r"Visual score $U$", fontsize=7.25, color=INK, pad=6)
    cost_axes.set_xscale("log")
    cost_axes.set_xlim(0.2, 130)
    cost_axes.set_xticks([1, 10, 100])
    cost_axes.set_xticklabels(["$1", "$10", "$100"])
    cost_axes.minorticks_off()
    cost_axes.set_title("Median cost per target", fontsize=7.25, color=INK, pad=6)


    separators = _draw_model_labels(score_axes, benchmark)
    for separator in separators:
        score_axes.axhline(separator, color=GROUP_RULE, linewidth=0.45, zorder=1)
        cost_axes.axhline(separator, color=GROUP_RULE, linewidth=0.45, zorder=1)
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

    figure = plt.figure(figsize=(7.40, 6.30), facecolor="white")
    # Model names begin on the same left anchor as panel A. The two
    # quantitative axes then use the remaining panel width instead of being
    # compressed behind a large invisible label gutter.
    score_axes = figure.add_axes((0.205, 0.075, 0.235, 0.845))
    cost_axes = figure.add_axes((0.478, 0.075, 0.112, 0.845))
    # Panel B starts at the same horizontal anchor as its heading. Give the
    # benchmark cells the full panel width and reserve only a narrow outer
    # strip for the IoU scale.
    matrix_axes = figure.add_axes((0.632, 0.075, 0.315, 0.845))
    colorbar_axes = figure.add_axes((0.958, 0.075, 0.009, 0.845))

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
