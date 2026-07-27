"""Render Figure 9: two evaluation records on one shared axis.

The upper cluster contains the current multimodal-agent record and the lower
cluster contains the iterative API record. Restrained color and marker shape
distinguish the records without implying a controlled or causal comparison.

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


REPO = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__file__).with_name("fig_emergence_assets")
MANIFEST = ASSET_DIR / "manifest.json"
FIGURE_DIR = REPO / "arxiv" / "figures"

INK = "#17191c"
SOFT_INK = "#555a60"
RULE = "#17191c"
GRID = "#e2e4e6"
MULTIMODAL_BLUE = "#2f5f9e"
ITERATIVE_GREEN = "#267a5a"

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


LEGACY_NAMES = {
    "Gemini-3-Pro": "Gemini 3 Pro",
    "Gemini-3-Flash": "Gemini 3 Flash",
    "Grok-4": "Grok 4",
    "Gemini-2.5-Flash": "Gemini 2.5 Flash",
    "Gemini-2.5-Pro": "Gemini 2.5 Pro",
    "Qwen-VL-Instruct": "Qwen-VL Instruct",
    "Claude-Opus-4.5": "Opus 4.5",
    "Gemini-2.0-Flash": "Gemini 2.0 Flash",
    "Claude-Sonnet-4.5": "Sonnet 4.5",
}

CODING_AGENT_CONFIGS = [
    ("GPT-5.5", "codex55m"),
    ("Opus 4.8", "opus48m"),
    ("GPT-5.4", "codex54m"),
    ("Sonnet 5", "sonnet5m"),
    ("GPT-5.3 spark", "codexspark"),
    ("GPT-5.4 mini", "codex54mini"),
    ("Opus 4.5", "opus45m"),
    ("Sonnet 4.5", "sonnet45m"),
    ("Haiku 4.5", "haiku45m"),
]

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verified_json(asset: str, expected_sha256: str):
    path = ASSET_DIR / asset
    actual = _sha256(path)
    if actual != expected_sha256:
        raise ValueError(
            f"Hash mismatch for {path}: expected {expected_sha256}, got {actual}."
        )
    return json.loads(path.read_text())


def _load_records() -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    specification = json.loads(MANIFEST.read_text())
    legacy_specification = specification["iterative_api_record"]
    legacy_source = _verified_json(
        legacy_specification["asset"],
        legacy_specification["sha256"],
    )
    legacy = []
    for row in legacy_source:
        measured_score = float(row["primitive_rate"]) * float(
            row["avg_iou_primitives"]
        )
        if not np.isclose(
            measured_score,
            float(row["expected_usable_iou"]),
            atol=1e-12,
        ):
            raise ValueError(
                f"Legacy U does not reconcile for {row['model']}: "
                f"computed {measured_score}, stored {row['expected_usable_iou']}."
            )
        legacy.append((LEGACY_NAMES[row["model"]], measured_score))
    legacy.sort(key=lambda item: -item[1])
    if len(legacy) != 9 or len({name for name, _ in legacy}) != 9:
        raise ValueError("The iterative API record must contain nine models.")

    sweep_specification = specification["coding_agent_sweep"]
    sweep_source = _verified_json(
        sweep_specification["asset"],
        sweep_specification["sha256"],
    )["cells"]
    expected_targets = int(sweep_specification["expected_targets_per_configuration"])
    coding_agent = []
    for name, configuration in CODING_AGENT_CONFIGS:
        cells = [cell for cell in sweep_source if cell["config"] == configuration]
        if len(cells) != expected_targets:
            raise ValueError(
                f"Expected {expected_targets} cells for {configuration}, got {len(cells)}."
            )
        usable_scores = [
            float(cell["iou"])
            for cell in cells
            if cell["iou"] is not None and not cell["purity_violation"]
        ]
        score = (
            len(usable_scores) / len(cells) * mean(usable_scores)
            if usable_scores
            else 0.0
        )
        coding_agent.append((name, score))
    coding_agent.sort(key=lambda item: -item[1])

    return legacy, coding_agent


def _draw_group_heading(
    axes: plt.Axes,
    *,
    y: float,
    title: str,
    marker: str,
    filled: bool,
    color: str,
) -> None:
    axes.scatter(
        [0],
        [y],
        s=31,
        marker=marker,
        facecolor=color if filled else "white",
        edgecolor=color,
        linewidth=1.05,
        zorder=3,
        clip_on=False,
    )
    axes.text(
        0.035,
        y,
        title,
        ha="left",
        va="center",
        fontsize=9.2,
        fontweight="normal",
        color=INK,
    )
    axes.hlines(
        y + 0.68,
        0,
        1.065,
        color=RULE,
        linewidth=0.68,
        zorder=2,
    )


def _draw_record(
    axes: plt.Axes,
    rows: list[tuple[str, float]],
    *,
    y: np.ndarray,
    marker: str,
    filled: bool,
    color: str,
) -> tuple[list[str], np.ndarray]:
    labels = [name for name, _ in rows]
    values = np.asarray([value for _, value in rows])

    axes.scatter(
        values,
        y,
        s=29,
        marker=marker,
        facecolor=color if filled else "white",
        edgecolor=color,
        linewidth=1.05,
        zorder=3,
    )
    for row_y, value in zip(y, values):
        axes.text(
            min(value + 0.018, 1.025),
            row_y,
            f"{value:.3f}",
            ha="left",
            va="center",
            fontsize=7.5,
            fontweight="normal",
            color=INK,
        )

    return labels, values


def _style_axes(
    axes: plt.Axes,
    *,
    positions: np.ndarray,
    labels: list[str],
) -> None:
    axes.set_xlim(0, 1.08)
    axes.set_ylim(21.55, -0.75)
    axes.set_yticks(positions)
    axes.set_yticklabels(labels, fontsize=7.9, color=INK)
    axes.set_xticks([0, 0.25, 0.50, 0.75, 1.00])
    axes.set_xticklabels(["0", "0.25", "0.50", "0.75", "1.00"], fontsize=7.4)
    axes.grid(
        axis="x",
        color=GRID,
        linewidth=0.55,
        linestyle="-",
        zorder=0,
    )
    axes.tick_params(
        axis="x",
        length=3.4,
        width=0.65,
        color=SOFT_INK,
        labelcolor=SOFT_INK,
        pad=3,
    )
    axes.tick_params(axis="y", length=0, pad=7)

    for side in ("top", "right", "left"):
        axes.spines[side].set_visible(False)
    axes.spines["bottom"].set_color(SOFT_INK)
    axes.spines["bottom"].set_linewidth(0.65)
    axes.set_xlabel(
        r"Compliance-weighted IoU $U$",
        fontsize=8.1,
        color=INK,
        labelpad=5,
    )
    axes.set_facecolor("white")


def main() -> None:
    legacy, coding_agent = _load_records()

    figure = plt.figure(figsize=(7.40, 3.55), facecolor="white")
    axes = figure.add_axes((0.215, 0.115, 0.755, 0.845))

    multimodal_y = np.arange(1.45, 10.45)
    iterative_y = np.arange(12.75, 21.75)
    multimodal_labels, _ = _draw_record(
        axes,
        coding_agent,
        y=multimodal_y,
        marker="o",
        filled=True,
        color=MULTIMODAL_BLUE,
    )
    iterative_labels, _ = _draw_record(
        axes,
        legacy,
        y=iterative_y,
        marker="D",
        filled=False,
        color=ITERATIVE_GREEN,
    )

    _draw_group_heading(
        axes,
        y=0,
        title="Multimodal agents",
        marker="o",
        filled=True,
        color=MULTIMODAL_BLUE,
    )
    _draw_group_heading(
        axes,
        y=11.25,
        title="Iterative API record",
        marker="D",
        filled=False,
        color=ITERATIVE_GREEN,
    )
    positions = np.concatenate([multimodal_y, iterative_y])
    labels = multimodal_labels + iterative_labels
    _style_axes(
        axes,
        positions=positions,
        labels=labels,
    )

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    output = FIGURE_DIR / "fig1_emergence.pdf"
    figure.savefig(output, dpi=600, facecolor="white", bbox_inches=None)
    print(f"wrote {output}")
    plt.close(figure)


if __name__ == "__main__":
    main()
