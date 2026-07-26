"""Best-of-eight gallery for the fully re-scored draw of the paper checkpoint.

The archived attempts aggregate to eval@1=0.254 and best@8=0.466, matching
``benchmark_eval_bridge2_g.json`` and the per-device values in Table IV.

Each target/reconstruction pair uses the paper's diff-map convention (maroon =
correct material, pink = spurious, black = missed).

Attempts come from the archived k=8 eval dump (rl/reports/benchmark_attempts_
bridge2.jsonl); the best attempt per device is re-executed through the same
rasterization path that grades it (rl/reports/make_gallery.render_code), so every
pixel shown is conductor-gate arithmetic, not a worker-reported image.

Run from the repo root with the repo venv:
  .venv/bin/python arxiv/scripts/make_fig_rl_gallery.py
"""
import json
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
os.chdir(REPO)  # render_code + attempts sample_dir paths are repo-relative
sys.path.insert(0, str(REPO / "rl/reports"))
sys.path.insert(0, str(REPO / "src"))
from make_gallery import render_code  # noqa: E402

ARXIV = REPO / "arxiv/figures"
FIGD = REPO / "arxiv/figures"
ATTEMPTS = REPO / "rl/reports/benchmark_attempts_bridge2.jsonl"

plt.rcParams.update({"font.family": "serif", "savefig.bbox": "tight"})

TP, FP, FN = (0x66, 0x00, 0x00), (0xFF, 0x99, 0x99), (0x00, 0x00, 0x00)
ASPECT = 0.62


def mask_of(img):
    return np.array(img.convert("L")) < 128


def composite(target, render):
    t, r = mask_of(target), mask_of(render)
    out = np.full((*t.shape, 3), 255, dtype=np.uint8)
    out[t & ~r] = FN
    out[r & ~t] = FP
    out[t & r] = TP
    return out


def pad_to_aspect(img, aspect=ASPECT):
    h, w = img.shape[:2]
    if h / w < aspect:
        H, W = int(round(w * aspect)), w
    else:
        H, W = h, int(round(h / aspect))
    out = np.full((H, W, 3), 255, dtype=np.uint8)
    y0, x0 = (H - h) // 2, (W - w) // 2
    out[y0:y0 + h, x0:x0 + w] = img
    return out


def to_rgb(img):
    a = np.array(img.convert("L"))
    return np.stack([a, a, a], axis=-1)


def main():
    best, all_attempts = {}, {}
    for line in open(ATTEMPTS):
        w = json.loads(line)
        all_attempts.setdefault(w["figure"], []).append(w)
        if w["figure"] not in best or w["iou"] > best[w["figure"]]["iou"]:
            best[w["figure"]] = w

    fids = sorted(best)
    # Two four-device blocks keep all labels legible at the paper's final width.
    fig, axes = plt.subplots(4, 4, figsize=(7.0, 3.55))
    for i, fid in enumerate(fids):
        w = best[fid]
        target = Image.open(REPO / w["sample_dir"] / "device_bw.png")
        block, col = divmod(i, 4)
        row = 2 * block
        col_t, col_c = axes[row][col], axes[row + 1][col]
        col_t.imshow(pad_to_aspect(to_rgb(target)))
        if w["iou"] > 0:
            render = render_code(w["code"], w["sample_dir"])
            comp = composite(target, render)
        else:
            comp = np.full((100, 160, 3), 255, dtype=np.uint8)
        col_c.imshow(pad_to_aspect(comp))
        n = fid.replace("final_", "F")
        executable = sum(1 for a in all_attempts[fid] if a.get("gds_ok"))
        col_t.set_title(n, fontsize=8, pad=2)
        col_c.set_title(
            f"best IoU {w['iou']:.2f}; {executable}/8 executable",
            fontsize=6.2,
            pad=1.5,
        )
        for ax in (col_t, col_c):
            ax.set_xticks([])
            ax.set_yticks([])
            for s in ax.spines.values():
                s.set_visible(False)
    for row in (0, 2):
        axes[row][0].set_ylabel("target", fontsize=7.5)
        axes[row + 1][0].set_ylabel("best of 8", fontsize=7.5)
    for row in axes:
        row[0].yaxis.set_visible(True)
        row[0].set_yticks([])
    fig.tight_layout(h_pad=0.25, w_pad=0.35)
    for out in (ARXIV / "fig_rl_gallery.pdf", FIGD / "fig_rl_gallery.png"):
        fig.savefig(out)
        print("wrote", out)


if __name__ == "__main__":
    main()
