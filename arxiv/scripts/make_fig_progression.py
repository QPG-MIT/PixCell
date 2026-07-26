"""fig_progression: "Where the intelligence lives" — agent-logged IoU through
the self-run measure->refine loop.

Data: data/agents/paper_swap/final*/output/recreation_<cfg>/recreation_log.json
(the agents' own iteration logs, archived per cell). Six configurations
spanning frontier / mid / weak; per-config mean line (final value carried
forward where a cell's loop ended early, truncated at the 6-iteration brief
cap) over faint individual-cell traces.

Output: PDF -> arxiv/figures/fig_progression.pdf
        PNG -> arxiv/figures/fig_progression.png

Run: .venv/bin/python arxiv/scripts/make_fig_progression.py
"""
import json
from pathlib import Path
from statistics import mean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
PSW = REPO / "data/agents/paper_swap"
FIG = REPO / "arxiv/figures"
ARXIV = REPO / "arxiv/figures"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix", "pdf.fonttype": 42, "font.size": 8.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.7, "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "savefig.bbox": "tight", "figure.dpi": 200,
})

MAX_ITER = 6  # the brief's cap on IoU iterations

# (config, label, line color, label dy in points) — shades of the vendor hues
CONFIGS = [
    ("opus48m",    "Opus 4.8",      "#8f4527", 0),
    ("codex55h",   "GPT-5.5 high",  "#2a5c94", 0),
    ("sonnet5m",   "Sonnet 5",      "#c15f3c", 0),
    ("codexspark", "GPT-5.3 spark", "#3c7ec1", 0),
    ("sonnet45m",  "Sonnet 4.5",    "#d68a6a", 2.5),
    ("haiku45m",   "Haiku 4.5",     "#e0a878", -2.5),
]
FAINT = {"opus48m": "#c15f3c", "sonnet5m": "#c15f3c", "sonnet45m": "#c15f3c",
         "haiku45m": "#c15f3c", "codex55h": "#3c7ec1", "codexspark": "#3c7ec1"}


def traces(cfg):
    """Per-cell IoU sequences, forward-filled over nulls, capped at MAX_ITER.

    Cells whose loop never iterated (a single logged measurement) carry no
    trajectory and are excluded — the figure is about motion through the loop.
    """
    out = []
    for dev in sorted(PSW.glob("final*")):
        log = dev / "output" / f"recreation_{cfg}" / "recreation_log.json"
        if not log.exists():
            continue
        seq, last = [], None
        for it in json.loads(log.read_text()).get("iterations", []):
            v = it.get("iou")
            if v is None:
                v = last
            if v is None:
                continue
            seq.append(v)
            last = v
        if len(seq) >= 2:
            out.append(seq[:MAX_ITER])
    return out


def mean_line(seqs):
    """Mean over cells at each iteration, final value carried forward."""
    return [mean(s[min(i, len(s) - 1)] for s in seqs) for i in range(MAX_ITER)]


fig, ax = plt.subplots(figsize=(3.4, 2.55))
ax.grid(axis="y", color="#dddddd", lw=0.5, zorder=0)
xs = range(1, MAX_ITER + 1)

for cfg, label, color, dy in CONFIGS:
    seqs = traces(cfg)
    for s in seqs:  # individual cells, faint
        ax.plot(range(1, len(s) + 1), s, color=FAINT[cfg], lw=0.5,
                alpha=0.15, zorder=1)
    m = mean_line(seqs)
    ax.plot(xs, m, color=color, lw=1.1, zorder=3,
            solid_capstyle="round")
    ax.annotate(f"{label} ($n$={len(seqs)})", (MAX_ITER, m[-1]),
                textcoords="offset points", xytext=(4, dy), fontsize=6,
                color=color, ha="left", va="center", zorder=4)

ax.set_xlim(0.85, MAX_ITER + 2.3)
ax.set_ylim(0, 1.0)
ax.set_xticks(list(xs))
ax.tick_params(labelsize=7)
ax.set_xlabel("iteration of the self-run measure–refine loop", fontsize=7.5)
ax.set_ylabel("IoU (agent-logged, mean per config)", fontsize=7.5)
ax.spines["bottom"].set_bounds(1, MAX_ITER)

fig.savefig(ARXIV / "fig_progression.pdf")
fig.savefig(FIG / "fig_progression.png")
print("wrote", ARXIV / "fig_progression.pdf")
