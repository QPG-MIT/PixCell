"""Archived seed and turn examples from the June-2026 iterative API run.

Panel (a): seed diversity — one model (Gemini-3-Pro), one device (FINAL_4),
ten parallel seeds; six representative overlays spanning IoU 0.44-0.87.
Panel (b): turn iteration — one seed (FINAL_6, Gemini-3-Pro run 006) through
five propose->verify->diff turns, IoU 0.72 -> 0.63 -> 0.57 -> 0.80 -> 0.975.
Data: data/chatbots/figure_panels/panels/ (overlays + summary.json files,
frozen from the June 21 2026 benchmark).

Run: .venv/bin/python paper-tools/make_fig_june_seeds.py
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]                       # .../PixCell-running
ASSETS = REPO / "data/chatbots/figure_panels/panels"
OUT_FIG = HERE.parents[1] / "figures"
OUT_ARXIV = HERE.parents[1] / "figures"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix", "pdf.fonttype": 42, "font.size": 8.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.7, "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "savefig.bbox": "tight", "figure.dpi": 200,
})
C_ACC = "#c15f3c"
INK = "#16161d"


def autocrop(img, thr=245 / 255, pad=0.04):
    """Crop white margins; ignore single-pixel speckle rows/cols."""
    gray = img[..., :3].min(axis=2)
    mask = gray < thr
    rows = np.where(mask.sum(axis=1) > 3)[0]
    cols = np.where(mask.sum(axis=0) > 3)[0]
    if len(rows) == 0 or len(cols) == 0:
        return img
    r0, r1, c0, c1 = rows[0], rows[-1], cols[0], cols[-1]
    pr, pc = int((r1 - r0) * pad) + 2, int((c1 - c0) * pad) + 2
    r0, r1 = max(0, r0 - pr), min(img.shape[0], r1 + pr)
    c0, c1 = max(0, c0 - pc), min(img.shape[1], c1 + pc)
    return img[r0:r1, c0:c1]


SEED_DIR = ASSETS / "seed_diversity/FINAL_4_gemini3pro_10seeds"
SEEDS = [  # (file stem, iou, rank label) — IoUs are the archived turn-2 metrics.json values
    ("worst_run_001_iou0.437_overlay.png", 0.437, "worst"),
    ("very-low_run_004_iou0.503_overlay.png", 0.503, ""),
    ("low_run_010_iou0.610_overlay.png", 0.610, ""),
    ("3rd_run_006_iou0.780_overlay.png", 0.780, ""),
    ("2nd_run_007_iou0.826_overlay.png", 0.826, ""),
    ("best_run_000_iou0.868_overlay.png", 0.868, "best of 11"),
]
TURN_DIR = ASSETS / "turn_improvement/FINAL_6_gemini3pro_run006"
TURNS = json.loads((TURN_DIR / "summary.json").read_text())["ious"]  # 5 turns

fig = plt.figure(figsize=(7.0, 2.75))
gs = fig.add_gridspec(2, 12, hspace=0.9, wspace=0.12,
                      height_ratios=[0.55, 1.55])

# ---- (a) seeds: 6 tiles across the top row
for i, (fname, iou, rank) in enumerate(SEEDS):
    ax = fig.add_subplot(gs[0, i * 2:i * 2 + 2])
    ax.imshow(autocrop(plt.imread(SEED_DIR / fname)))
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(True); s.set_color("#dddddd"); s.set_linewidth(0.5)
    ax.set_title(f"{iou:.2f}", fontsize=8, pad=2, color=INK,
                 fontweight="bold" if rank == "best of 11" else "normal")
    if rank:
        ax.set_xlabel(rank, fontsize=7, labelpad=1.5, color="#8a8a8a")
fig.text(0.005, 0.99, "(a)", fontsize=10, fontweight="bold", va="top")

# ---- (b) turns: 5 centered tiles across the bottom row
for t in range(5):
    ax = fig.add_subplot(gs[1, t * 2 + 1:t * 2 + 3])
    ax.imshow(autocrop(plt.imread(TURN_DIR / f"turn{t+1}_overlay.png")))
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(True); s.set_color("#dddddd"); s.set_linewidth(0.5)
    best = t == 4
    ax.set_title(f"{TURNS[t]:.2f}" if not best else f"{TURNS[t]:.3f}",
                 fontsize=8, pad=2, fontweight="bold" if best else "normal",
                 color=C_ACC if best else INK)
    ax.set_xlabel(f"turn {t+1}", fontsize=7, labelpad=1.5, color="#8a8a8a")
fig.text(0.005, 0.58, "(b)", fontsize=10, fontweight="bold", va="top")

for out in (OUT_FIG, OUT_ARXIV):
    fig.savefig(out / "fig_june_seeds.pdf")
fig.savefig(OUT_FIG / "fig_june_seeds.png")
print("wrote", OUT_FIG / "fig_june_seeds.pdf", "(paper figures dir)")
