#!/usr/bin/env python3
"""fig_training_telemetry: the RL lineage's climb, straight from the run telemetry.

One panel, 95 GRPO steps across the three lineage stages (trunk -> bridge-1 ->
bridge-2). Blue: verified IoU on the training diet (raw per-step behind a 5-step
rolling mean). Green: fraction of sampled programs that execute to a GDS.
Maroon open circles: the held-out eight-figure benchmark, single attempt,
evaluated in-training every ten steps.

Data: rl/reports/runs_ledger/<run>/metrics.jsonl (tracked; the same series the
W&B dashboards showed live).

Run: .venv/bin/python paper-tools/make_fig_training_telemetry.py
Writes arxiv/figures/ and website/static/images/paper/.
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
LEDGER = REPO / "rl/reports/runs_ledger"
OUT_FIG = HERE.parents[1] / "figures"
OUT_WEB = REPO / "website/static/images/paper"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix", "pdf.fonttype": 42, "font.size": 8.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.7, "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "savefig.bbox": "tight", "figure.dpi": 200,
})
C_IOU, C_COMPILE, C_BENCH, INK = "#3c7ec1", "#1f8a5f", "#A31F34", "#16161d"

STAGES = [  # (label, run dir, step offset)
    ("trunk", "pixcell-Qwen-Qwen3.6-35B-A3B-8g-8b-lr1e-05-20260708-0953", 0),
    ("bridge-1", "pixcell-Qwen-Qwen3.6-35B-A3B-8g-8b-lr1e-05-20260708-1043", 30),
    ("bridge-2", "pixcell-Qwen-Qwen3.6-35B-A3B-8g-8b-lr1e-05-20260708-1209", 65),
]

steps, iou, compile_ok, bench = [], [], [], []
seams = []
for label, d, off in STAGES:
    if off:
        seams.append(off)
    for line in open(LEDGER / d / "metrics.jsonl"):
        r = json.loads(line)
        s = r["step"] + off
        if "env/all/iou" in r:
            steps.append(s)
            iou.append(r["env/all/iou"])
            compile_ok.append(r.get("env/all/gds_ok"))
        if "test/env/all/iou" in r:
            bench.append((s, r["test/env/all/iou"]))


def rolling(xs, w=5):
    out = []
    for i in range(len(xs)):
        window = [x for x in xs[max(0, i - w + 1): i + 1] if x is not None]
        out.append(sum(window) / len(window) if window else None)
    return out


fig, ax = plt.subplots(figsize=(7.0, 2.7))

for x in seams:
    ax.axvline(x, color="#cccccc", lw=0.7, ls=(0, (2, 3)), zorder=1)
for (label, _, off), end in zip(STAGES, seams + [max(steps)]):
    ax.text((off + end) / 2, 1.035, label, ha="center", va="bottom",
            fontsize=7.5, color="#8a8a8a", style="italic")

ax.plot(steps, iou, color=C_IOU, lw=0.7, alpha=0.25, zorder=2)
ax.plot(steps, rolling(iou), color=C_IOU, lw=1.6, zorder=4,
        label="verified IoU, training diet")
ax.plot(steps, rolling(compile_ok), color=C_COMPILE, lw=1.4, zorder=3,
        label="programs that execute")
bx, by = zip(*bench)
ax.plot(bx, by, "o", mfc="white", mec=C_BENCH, mew=1.2, ms=5, zorder=5,
        label="held-out benchmark, one attempt")
ax.plot(bx, by, color=C_BENCH, lw=0.8, ls=(0, (1, 2)), zorder=3, alpha=0.7)

# direct labels at the line ends (secondary encoding on top of the legend)
ax.annotate("execute", (steps[-1], rolling(compile_ok)[-1]),
            textcoords="offset points", xytext=(5, 2), fontsize=7,
            color=C_COMPILE, va="center")
ax.annotate("train IoU", (steps[-1], rolling(iou)[-1]),
            textcoords="offset points", xytext=(5, 0), fontsize=7,
            color=C_IOU, va="center")
ax.annotate("benchmark", (bx[-1], by[-1]),
            textcoords="offset points", xytext=(5, -4), fontsize=7,
            color=C_BENCH, va="top")

ax.set_xlim(0, max(steps) + 12)
ax.set_ylim(0, 1.0)
ax.set_xlabel("GRPO step (lineage-cumulative)", fontsize=8)
ax.set_ylabel("fraction / verified IoU", fontsize=8)
ax.tick_params(labelsize=7.5)
ax.grid(axis="y", color="#eeeeee", lw=0.5, zorder=0)
ax.legend(fontsize=7, frameon=False, loc="lower right", handlelength=1.6)

OUT_WEB.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_FIG / "fig_training_telemetry.png")
fig.savefig(OUT_WEB / "fig_training_telemetry.png")
print("wrote", OUT_WEB / "fig_training_telemetry.png")
