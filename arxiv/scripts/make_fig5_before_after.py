"""fig5_before_after: selected outputs from two evaluation harnesses.

Rows: selected lower-scoring API output / selected higher-scoring API output /
July single-run coding-agent output.
Columns: FINAL_1 (adiabatic coupler), FINAL_7 (ring/MZI hybrid), FINAL_8
(sub-wavelength grating). Every cell is composited from the archived target
mask and the run's archived raster: TP maroon, FP pink, FN black. IoU values
are the archived (independently recomputed) run metrics.

FINAL_7's best-effort cell comes from the paper_10 project -- the same device
image benchmarked under its original paper numbering (device_bw pixel-identical
to FINAL_7's).

Run: .venv/bin/python arxiv/scripts/make_fig5_before_after.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
GIR = REPO / "projects/gemini_images_run"
P10 = REPO / "projects/paper_10"
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

INK = "#16161d"
TP, FP, FN = (0x66, 0x00, 0x00), (0xFF, 0x99, 0x99), (0x00, 0x00, 0x00)
ROW_COLORS = ["#8a8a8a", "#5f5f5f", "#327162"]
ROW_LABELS = ["iterative API\nlower-scoring example",
              "iterative API\nhigher-scoring example",
              "coding agent\nsingle run"]


def mask(path):
    return np.array(Image.open(path).convert("L")) < 128


def composite(target_path, raster_path):
    t, r = mask(target_path), mask(raster_path)
    out = np.full((*t.shape, 3), 255, dtype=np.uint8)
    out[t & ~r] = FN
    out[r & ~t] = FP
    out[t & r] = TP
    return out


ASPECT = 0.58  # uniform cell canvas (h/w) so titles and captions align


def pad_to_aspect(img, aspect=ASPECT):
    h, w = img.shape[:2]
    if h / w < aspect:          # too flat: pad top/bottom
        H, W = int(round(w * aspect)), w
    else:                       # too tall: pad left/right
        H, W = h, int(round(h / aspect))
    out = np.full((H, W, 3), 255, dtype=np.uint8)
    y0, x0 = (H - h) // 2, (W - w) // 2
    out[y0:y0 + h, x0:x0 + w] = img
    return out


COLS = [
    {
        "title": "F1 · adiabatic coupler",
        "june_target": GIR / "FINAL_1/device_bw.png",
        "agent_target": PSW / "final1/device_bw.png",
        "cells": [
            (GIR / "FINAL_1/benchmark_gemini_gemini-2.0-flash/phase1/benchmark_gemini-2-0-flash/run_003/turn2/raster.png",
             "Gemini-2.0-Flash · IoU 0.066"),
            (GIR / "FINAL_1/benchmark_gemini_gemini-3.1-pro-preview/phase1/benchmark_gemini-3-1-pro-preview/run_009/turn2/raster.png",
             "Gemini-3.1-Pro · IoU 0.682"),
            (PSW / "final1/output/recreation_codex55m/raster.png",
             "GPT-5.5 · IoU 0.987"),
        ],
    },
    {
        "title": "F7 · ring/MZI hybrid",
        "june_target": GIR / "FINAL_7/device_bw.png",
        "agent_target": PSW / "final7/device_bw.png",
        "best_target": P10 / "device_bw.png",
        "cells": [
            (GIR / "FINAL_7/benchmark_qwen_qwen3-vl-235b-a22b-instruct/phase1/benchmark_qwen3-vl-235b-a22b-instruct/run_002/turn2/raster.png",
             "Qwen3-VL · IoU 0.229"),
            (P10 / "benchmark_gemini_gemini-3-pro-preview/phase1/run_016/turn2/raster.png",
             "Gemini-3-Pro · IoU 0.537"),
            (PSW / "final7/output/recreation_codex55m/raster_iter5.png",
             "GPT-5.5 · IoU 0.958"),
        ],
    },
    {
        "title": "F8 · sub-wavelength grating",
        "june_target": GIR / "FINAL_8/device_bw.png",
        "agent_target": PSW / "final8/device_bw.png",
        "cells": [
            (GIR / "FINAL_8/benchmark_gemini_gemini-2.0-flash/phase1/benchmark_gemini-2-0-flash/run_002/turn2/raster.png",
             "Gemini-2.0-Flash · IoU 0.278"),
            (GIR / "FINAL_8/benchmark_gemini_gemini-3-flash-preview/phase1/benchmark_gemini-3-flash-preview/run_001/turn2/raster.png",
             "Gemini-3-Flash · IoU 0.507"),
            (PSW / "final8/output/recreation_opus48m/raster.png",
             "Opus 4.8 · IoU 0.900"),
        ],
    },
]

fig, axes = plt.subplots(3, 3, figsize=(6.4, 4.0))
for j, col in enumerate(COLS):
    for i, (raster, caption) in enumerate(col["cells"]):
        ax = axes[i][j]
        if i == 2:
            target = col["agent_target"]
        elif i == 1:
            target = col.get("best_target", col["june_target"])
        else:
            target = col["june_target"]
        ax.imshow(pad_to_aspect(composite(target, raster)),
                  interpolation="antialiased")
        ax.set_axis_off()
        if i == 0:
            ax.set_title(col["title"], fontsize=8, color=INK, pad=6)
        ax.text(0.5, -0.07, caption, transform=ax.transAxes, ha="center",
                va="top", fontsize=6.8, color=ROW_COLORS[i])

for i, (lab, c) in enumerate(zip(ROW_LABELS, ROW_COLORS)):
    axes[i][0].text(-0.07, 0.5, lab, transform=axes[i][0].transAxes,
                    ha="right", va="center", fontsize=7.5, color=c,
                    style="italic", rotation=0, linespacing=1.4)

fig.subplots_adjust(left=0.13, right=0.995, top=0.92, bottom=0.05,
                    hspace=0.34, wspace=0.06)
fig.savefig(ARXIV / "fig5_before_after.pdf")
fig.savefig(FIG / "fig5_before_after.png", dpi=200)
print("wrote", ARXIV / "fig5_before_after.pdf")
