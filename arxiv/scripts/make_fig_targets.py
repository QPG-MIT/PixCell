"""fig_targets: the eight-device benchmark target set (FINAL_1-8), one tile per
device: the calibrated B&W silhouette with its stated footprint.

Run: .venv/bin/python arxiv/scripts/make_fig_targets.py
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
BENCH = REPO / "database/bw/benchmark"
ARXIV = REPO / "arxiv/figures"
FIGD = REPO / "arxiv/figures"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["STIXGeneral", "Times New Roman",
                                          "DejaVu Serif"],
    "mathtext.fontset": "stix", "pdf.fonttype": 42, "savefig.bbox": "tight",
})

ASPECT = 0.55


def pad_to_aspect(a, aspect=ASPECT):
    h, w = a.shape[:2]
    if h / w < aspect:
        H, W = int(round(w * aspect)), w
    else:
        H, W = h, int(round(h / aspect))
    out = np.full((H, W), 255, dtype=np.uint8)
    y0, x0 = (H - h) // 2, (W - w) // 2
    out[y0:y0 + h, x0:x0 + w] = a
    return out


def main():
    dirs = sorted(BENCH.glob("final_*"), key=lambda p: int(p.name.split("_")[1]))
    assert len(dirs) == 8, dirs
    fig, axes = plt.subplots(2, 4, figsize=(9.6, 3.4))
    for ax, d in zip(axes.flat, dirs):
        img = np.array(Image.open(d / "device_bw.png").convert("L"))
        fp = json.load(open(d / "footprint.json"))["footprint_um"]
        ax.imshow(pad_to_aspect(img), cmap="gray", vmin=0, vmax=255)
        n = d.name.replace("final_", "F")
        ax.set_title(f"{n}   ({fp[0]:g}$\\times${fp[1]:g} $\\mu$m)", fontsize=9, pad=3)
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
    fig.tight_layout(h_pad=0.8, w_pad=0.5)
    for out in (ARXIV / "fig_targets.pdf", FIGD / "fig_targets.png"):
        fig.savefig(out)
        print("wrote", out)


if __name__ == "__main__":
    main()
