"""Render Figure 9: two contextual evaluation records.

The panels share a 0--1 compliance-weighted IoU axis but deliberately remain
separate: the iterative API record uses a legacy source audit and uneven
target coverage, whereas the coding-agent record uses the current gate and
one retained run on each of eight targets.  Accent styling identifies only
model-version names present in both records; it does not encode a controlled
or causal comparison.

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
from matplotlib.lines import Line2D
import numpy as np


REPO = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__file__).with_name("fig_emergence_assets")
MANIFEST = ASSET_DIR / "manifest.json"
FIGURE_DIR = REPO / "arxiv" / "figures"

INK = "#17191c"
SOFT_INK = "#555a60"
RULE = "#17191c"
TRACK = "#c9ccd0"
MATCHED = "#800000"

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

MATCHED_NAMES = {"Opus 4.5", "Sonnet 4.5"}


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


def _panel_heading(
    figure: plt.Figure,
    *,
    x: float,
    letter: str,
    title: str,
    subtitle: str,
) -> None:
    figure.text(
        x,
        0.960,
        letter,
        ha="left",
        va="center",
        fontsize=10.5,
        fontweight="normal",
        color=INK,
    )
    figure.text(
        x + 0.036,
        0.960,
        title,
        ha="left",
        va="center",
        fontsize=10.5,
        fontweight="normal",
        color=INK,
    )
    figure.text(
        x + 0.036,
        0.905,
        subtitle,
        ha="left",
        va="center",
        fontsize=6.7,
        color=SOFT_INK,
    )
    figure.add_artist(
        Line2D(
            [x, x + 0.460],
            [0.870, 0.870],
            transform=figure.transFigure,
            color=RULE,
            linewidth=0.72,
        )
    )


def _draw_record(
    axes: plt.Axes,
    rows: list[tuple[str, float]],
) -> None:
    y = np.arange(len(rows))
    labels = [name for name, _ in rows]
    values = np.asarray([value for _, value in rows])
    colors = [MATCHED if name in MATCHED_NAMES else INK for name in labels]

    for index, (name, value, color) in enumerate(zip(labels, values, colors)):
        axes.hlines(
            index,
            0,
            value,
            color=MATCHED if name in MATCHED_NAMES else TRACK,
            linewidth=1.25,
            zorder=1,
        )
        axes.scatter(
            [value],
            [index],
            s=27,
            facecolor=color,
            edgecolor="white",
            linewidth=0.45,
            zorder=3,
        )
        axes.text(
            min(value + 0.025, 1.025),
            index,
            f"{value:.3f}",
            ha="left",
            va="center",
            fontsize=7.7,
            fontweight="bold" if name in MATCHED_NAMES else "normal",
            color=color,
        )

    axes.set_xlim(0, 1.08)
    axes.set_ylim(len(rows) - 0.45, -0.55)
    axes.set_yticks(y)
    axes.set_yticklabels(labels, fontsize=8.2, color=INK)
    for tick, name in zip(axes.get_yticklabels(), labels):
        tick.set_fontweight("bold" if name in MATCHED_NAMES else "normal")
        tick.set_color(MATCHED if name in MATCHED_NAMES else INK)

    axes.set_xticks([0, 0.25, 0.50, 0.75, 1.00])
    axes.set_xticklabels(["0", "0.25", "0.50", "0.75", "1.00"], fontsize=7.4)
    axes.tick_params(
        axis="x",
        length=3.4,
        width=0.65,
        color=SOFT_INK,
        labelcolor=SOFT_INK,
        pad=3,
    )
    axes.tick_params(axis="y", length=0, pad=6)

    for side in ("top", "right", "left"):
        axes.spines[side].set_visible(False)
    axes.spines["bottom"].set_color(SOFT_INK)
    axes.spines["bottom"].set_linewidth(0.65)
    axes.set_facecolor("white")


def main() -> None:
    legacy, coding_agent = _load_records()

    figure = plt.figure(figsize=(7.40, 2.72), facecolor="white")
    _panel_heading(
        figure,
        x=0.020,
        letter="A",
        title="Iterative API record",
        subtitle="Legacy audit · pooled turns · uneven target coverage",
    )
    _panel_heading(
        figure,
        x=0.520,
        letter="B",
        title="Coding-agent record",
        subtitle="Current gate · default/medium effort · one run × 8 targets",
    )

    legacy_axes = figure.add_axes((0.155, 0.145, 0.330, 0.680))
    coding_axes = figure.add_axes((0.655, 0.145, 0.330, 0.680))
    _draw_record(legacy_axes, legacy)
    _draw_record(coding_axes, coding_agent)

    figure.text(
        0.570,
        0.035,
        r"Compliance-weighted IoU $U$",
        ha="center",
        va="center",
        fontsize=8.1,
        color=INK,
    )

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    output = FIGURE_DIR / "fig1_emergence.pdf"
    figure.savefig(output, dpi=600, facecolor="white", bbox_inches=None)
    print(f"wrote {output}")
    plt.close(figure)


if __name__ == "__main__":
    main()
