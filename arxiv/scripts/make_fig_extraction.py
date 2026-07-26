"""fig_extraction: input standardization, before/after. Two devices: the source
figure panel as published (left) and the standardized device-only B&W silhouette
the system produces from it (right). Row 1 is benchmark device F5 (its silhouette
is byte-identical to the benchmark file); row 2 is the TFLN directional coupler
(a color panel).

Run: .venv/bin/python arxiv/scripts/make_fig_extraction.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
ARXIV = REPO / "arxiv/figures"
FIGD = REPO / "arxiv/figures"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["STIXGeneral", "Times New Roman",
                                          "DejaVu Serif"],
    "mathtext.fontset": "stix", "pdf.fonttype": 42, "savefig.bbox": "tight",
})

ROWS = [
    (REPO / "projects/paper_5/extracted_figure.png",
     REPO / "projects/paper_5/device_bw.png",
     "F5"),
    (REPO / "projects/paper_2/extracted_images/page2_img2.png",
     REPO / "database/bw/benchmark/final_2/device_bw.png",
     "F2"),
]


ASPECT = 0.78


def pad(a, aspect=ASPECT):
    h, w = a.shape[:2]
    if h / w < aspect:
        H, W = int(round(w * aspect)), w
    else:
        H, W = h, int(round(h / aspect))
    if a.ndim == 3:
        out = np.full((H, W, 3), 255, dtype=np.uint8)
    else:
        out = np.full((H, W), 255, dtype=np.uint8)
    y0, x0 = (H - h) // 2, (W - w) // 2
    out[y0:y0 + h, x0:x0 + w] = a
    return out


def main():
    fig, axes = plt.subplots(2, 2, figsize=(6.4, 4.6))
    for i, (src, out, label) in enumerate(ROWS):
        a_src = pad(np.array(Image.open(src).convert("RGB")))
        a_out = pad(np.array(Image.open(out).convert("L")))
        axes[i][0].imshow(a_src)
        axes[i][1].imshow(a_out, cmap="gray", vmin=0, vmax=255)
        axes[i][0].set_ylabel(label, fontsize=9)
        for ax in axes[i]:
            ax.set_xticks([])
            ax.set_yticks([])
            for s in ax.spines.values():
                s.set_visible(False)
        axes[i][0].yaxis.set_visible(True)
        axes[i][0].set_yticks([])
    axes[0][0].set_title("source figure panel", fontsize=9, pad=4)
    axes[0][1].set_title("standardized input", fontsize=9, pad=4)
    fig.tight_layout(h_pad=0.6, w_pad=0.6)
    for outp in (ARXIV / "fig_extraction.pdf", FIGD / "fig_extraction.png"):
        fig.savefig(outp)
        print("wrote", outp)


if __name__ == "__main__":
    main()
