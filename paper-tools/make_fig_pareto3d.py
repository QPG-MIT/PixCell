"""fig_pareto: 3D cost x time x capability economics figure.

Volume: the 13 agent configs at (cost/device, median wall-min, expected usable
IoU) -- all three coordinates measured from the archived transcripts.
Back wall (cost x capability plane): the June chatbot models as hollow
circles plus the agent projections and the Pareto staircase -- the June
pipeline has no per-device wall-time comparable to a single agent run, so
those points carry no time coordinate and stay on the wall.

June costs are order-of-magnitude estimates: pipeline call count x public
per-token rates (same values as the committed 2D predecessor).

Run: .venv/bin/python paper-tools/make_fig_pareto3d.py
"""
import json
from math import log10
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

REPO = Path(__file__).resolve().parents[2]
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

C_ANTH, C_OAI, C_JUNE = "#c15f3c", "#3c7ec1", "#8a8a8a"
C_FRONTIER = "#327162"

AGENTS = json.loads((FIG / "agent_table.json").read_text())

JUNE_CAP = {m["model"]: m["expected_usable_iou"]
            for m in json.loads((REPO / "benchmark_results/real_success_data.json").read_text())}
# order-of-magnitude per-device cost: ~40 pipeline calls x public rates
JUNE_COST = {
    "Gemini-2.0-Flash": 0.034, "Qwen-VL-Instruct": 0.14, "Gemini-2.5-Flash": 0.18,
    "Gemini-3-Flash": 0.23, "Gemini-2.5-Pro": 0.70, "Gemini-3-Pro": 0.92,
    "Grok-4": 1.20, "Claude-Sonnet-4.5": 1.30, "Claude-Opus-4.5": 6.0,
}

# axes (log10 space for cost and minutes)
XLIM = (log10(0.02), log10(120))
YLIM = (log10(6), log10(150))
ZLIM = (0.0, 1.0)
YWALL = YLIM[1]          # June points + projections live on this plane
CHATBOT_CEIL = 0.36

fig = plt.figure(figsize=(5.7, 4.1))
ax = fig.add_subplot(111, projection="3d")
ax.view_init(elev=18, azim=-58)
try:
    ax.set_box_aspect((1.45, 1.0, 0.85))
except AttributeError:
    pass

# ---- panes / grid ------------------------------------------------------
ax.xaxis.pane.set_facecolor((1, 1, 1, 0))
ax.zaxis.pane.set_facecolor((1, 1, 1, 0))
ax.yaxis.pane.set_facecolor((0.97, 0.97, 0.97, 0.45))   # the "wall"
for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
    axis._axinfo["grid"].update(color=(0.867, 0.867, 0.867, 1.0), linewidth=0.5)
    axis.line.set_linewidth(0.7)

# ---- chatbot-regime band on the wall ----------------------------------
band = Poly3DCollection(
    [[(XLIM[0], YWALL, 0), (XLIM[1], YWALL, 0),
      (XLIM[1], YWALL, CHATBOT_CEIL), (XLIM[0], YWALL, CHATBOT_CEIL)]],
    facecolors=(0.55, 0.55, 0.55, 0.10), edgecolors="none", zorder=1)
ax.add_collection3d(band)
ax.plot(list(XLIM), [YWALL, YWALL], [CHATBOT_CEIL, CHATBOT_CEIL],
        color=C_JUNE, lw=0.8, ls=":", zorder=2)

# ---- June chatbots on the wall -----------------------------------------
jx = [log10(JUNE_COST[m]) for m in JUNE_COST]
jz = [JUNE_CAP[m] for m in JUNE_COST]
ax.scatter(jx, jz, zs=YWALL, zdir="y", s=22, facecolors="none",
           edgecolors=C_JUNE, linewidths=0.9, depthshade=False, zorder=3)

# ---- agent projections + Pareto staircase on the wall ------------------
for a in AGENTS:
    col = C_ANTH if a["vendor"] == "anthropic" else C_OAI
    ax.scatter([log10(a["median_api_equiv_cost_usd"])], [a["usable_iou"]],
               zs=YWALL, zdir="y", s=7, color=col, alpha=0.3,
               depthshade=False, zorder=3)

frontier = [(0.87, 0.645), (1.48, 0.802), (2.01, 0.910)]
fx, fz = [], []
for i, (c, u) in enumerate(frontier):
    if i:
        fx += [log10(c)]
        fz += [frontier[i - 1][1]]
    fx += [log10(c)]
    fz += [u]
fx += [XLIM[1]]
fz += [frontier[-1][1]]
ax.plot(fx, [YWALL] * len(fx), fz, color=C_FRONTIER, lw=1.1, ls="--", zorder=4)

# ---- agent points in the volume ----------------------------------------
for a in AGENTS:
    col = C_ANTH if a["vendor"] == "anthropic" else C_OAI
    x = log10(a["median_api_equiv_cost_usd"])
    y = log10(a["median_wall_min"])
    z = a["usable_iou"]
    ax.plot([x, x], [y, y], [0, z], color=col, lw=0.6, alpha=0.3, zorder=5)
    ax.scatter([x], [y], [0], s=8, color=col, alpha=0.22, depthshade=False, zorder=5)
    ax.scatter([x], [y], [z], s=38, color=col, edgecolor="white",
               linewidth=0.7, depthshade=False, zorder=8)

# ---- labels (sparse, nudged by hand) -----------------------------------
LAB = {
    "codex54mini": ("5.4-mini", (-0.10, 0, 0.09), "right"),
    "codex54m": ("5.4", (-0.07, 0, -0.03), "right"),
    "codex55h": ("5.5-high", (-0.09, 0, 0.08), "right"),
    "codex55x": ("5.5-xhigh", (0.10, 0, 0.11), "left"),
    "codexspark": ("5.3-spark", (0.09, 0, -0.09), "left"),
    "sonnet5m": ("Sonnet 5", (0.08, 0, 0.05), "left"),
    "opus48m": ("Opus 4.8", (-0.09, 0, 0.10), "right"),
    "opus48max": ("Opus 4.8 max", (-0.07, 0, -0.14), "right"),
    "opus45m": ("Opus 4.5", (0.08, 0, 0.02), "left"),
    "haiku45h": ("Haiku 4.5 / Sonnet 4.5", (0.10, 0, 0.04), "left"),
}
by_cfg = {a["config"]: a for a in AGENTS}
for cfg, (txt, (dx, dy, dz), ha) in LAB.items():
    a = by_cfg[cfg]
    x = log10(a["median_api_equiv_cost_usd"]) + dx
    y = log10(a["median_wall_min"]) + dy
    z = a["usable_iou"] + dz
    ax.text(x, y, z, txt, fontsize=6, ha=ha, color="#444444", zorder=9)

# g3-pro: the June best, on the wall
ax.text(log10(0.92) + 0.12, YWALL, 0.354 - 0.03, "g3-pro (June best)",
        fontsize=6, ha="left", color="#8a8a8a", zorder=9)

# ---- axes cosmetics -----------------------------------------------------
ax.set_xlim(*XLIM)
ax.set_ylim(*YLIM)
ax.set_zlim(*ZLIM)
xticks = [0.1, 1, 10, 100]
ax.set_xticks([log10(v) for v in xticks])
ax.set_xticklabels([f"${v:g}" for v in xticks])
yticks = [10, 30, 100]
ax.set_yticks([log10(v) for v in yticks])
ax.set_yticklabels([f"{v:g}" for v in yticks])
ax.set_zticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
ax.set_xlabel("cost per device (USD, log)", labelpad=2, fontsize=7.5)
ax.set_ylabel("wall-clock (min, log)", labelpad=2, fontsize=7.5)
# mpl's tight bbox drops a real 3D z-label — draw it as figure text instead
fig.text(0.90, 0.60, "expected usable IoU", rotation=90, fontsize=7.5,
         ha="center", va="center")
ax.tick_params(labelsize=6.5, pad=0)

# ---- legend --------------------------------------------------------------
from matplotlib.lines import Line2D

handles = [
    Line2D([], [], marker="o", ls="", ms=5, mfc=C_OAI, mec="white", mew=0.6,
           label="agent — OpenAI"),
    Line2D([], [], marker="o", ls="", ms=5, mfc=C_ANTH, mec="white", mew=0.6,
           label="agent — Anthropic"),
    Line2D([], [], marker="o", ls="", ms=4.5, mfc="none", mec=C_JUNE, mew=0.9,
           label="chatbot pipeline, June (on wall)"),
    Line2D([], [], color=C_FRONTIER, ls="--", lw=1.1,
           label="agent Pareto frontier (on wall)"),
]
fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.11, 0.93),
           frameon=False, fontsize=6.5, handletextpad=0.4, labelspacing=0.35)

fig.savefig(ARXIV / "fig_pareto.pdf")
fig.savefig(FIG / "fig_pareto.png")
print("wrote", ARXIV / "fig_pareto.pdf")
