"""fig_verification: the verification mechanics of Sec. 2.2 (Verification), shown
on one real matrix cell. Device F4 (18 x 3 um directional coupler,
data/agents/paper_swap/final4), worker recreation_codex55m -- chosen because it
stored per-iteration artifacts: an instructive imperfect first attempt
(IoU 0.708) and the refined second attempt (IoU 0.921).

Five panels, left to right, are the grading path itself:
  (a) target silhouette + fixed-boundary calibration (non-white bbox; the stated
      footprint divides the box per axis into a stored px/um scale);
  (b) the candidate program's rendering at the STORED calibration -- left-aligned,
      vertically centered, never rescaled (render_gds_absolute);
  (c) overlay: candidate (red) on target (make_overlay_image);
  (d) signed diff: red = spurious material (FP), blue = missing (FN)
      (make_diff_image), with the IoU of record;
  (e) the residual diff after one refinement, IoU 0.708 -> 0.921.

All images are the stored conductor-gate artifacts; the IoU values are
re-derivable from them via michaelangelo.core.compare_absolute.compute_metrics
(this script asserts that they match the stored metrics_iter*.json).

Run: .venv/bin/python paper-tools/make_fig_verification.py
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from michaelangelo.core.compare_absolute import compute_metrics  # noqa: E402

ARXIV = REPO / "arxiv/figures"
FIGD = REPO / "arxiv/figures"

CELL = REPO / "data/agents/paper_swap/final4"
RUN = CELL / "output/recreation_codex55m"

BLUE = "#3c7ec1"  # calibration annotation color
GRAY = "0.25"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "pdf.fonttype": 42,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.bbox": "tight",
})


def load_inputs():
    calib = json.loads((RUN / "calibration.json").read_text())
    m1 = json.loads((RUN / "metrics_iter1.json").read_text())
    m2 = json.loads((RUN / "metrics_iter2.json").read_text())

    target = Image.open(CELL / "device_bw.png").convert("L")
    raster1 = Image.open(RUN / "raster_iter1.png").convert("L")
    raster2 = Image.open(RUN / "raster_iter2.png").convert("L")
    overlay1 = Image.open(RUN / "overlay_iter1.png").convert("RGB")
    diff1 = Image.open(RUN / "diff_iter1.png").convert("RGB")
    diff2 = Image.open(RUN / "diff_iter2.png").convert("RGB")

    # Honesty check: the stored rasters re-score to the stored metrics through
    # the actual grading path (compare_absolute.compute_metrics).
    thr = calib.get("white_threshold", 245)
    for raster, m in ((raster1, m1), (raster2, m2)):
        iou = compute_metrics(raster, target, thr)["IoU"]
        assert abs(iou - m["IoU"]) < 1e-9, (iou, m["IoU"])

    return calib, m1, m2, target, raster1, overlay1, diff1, diff2


def style_image_axes(ax, W, H, pad=10):
    ax.set_xlim(-pad, W + pad)
    ax.set_ylim(H + pad, -pad)
    ax.set_xticks([])
    ax.set_yticks([])
    for side, s in ax.spines.items():
        s.set_visible(True)
        s.set_color("0.75")
        s.set_linewidth(0.6)


def main():
    calib, m1, m2, target, raster1, overlay1, diff1, diff2 = load_inputs()

    W, H = calib["image_size_px"]
    x0, y0, x1, y1 = calib["bbox"]
    bw_px, bh_px = calib["bbox_size_px"]
    L_um, W_um = calib["footprint_um"]
    sx, sy = calib["scale_px_per_um"]
    gds_l1, gds_w1 = m1["gds_size_um"]

    fig = plt.figure(figsize=(10.6, 1.72))
    # image col | calib spacer | image | image | image | refine spacer | image
    gs = fig.add_gridspec(
        1, 7, width_ratios=[1, 0.34, 1, 1, 1, 0.30, 1], wspace=0.06,
        left=0.004, right=0.996, top=0.80, bottom=0.235,
    )
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 2])
    ax_c = fig.add_subplot(gs[0, 3])
    ax_d = fig.add_subplot(gs[0, 4])
    ax_e = fig.add_subplot(gs[0, 6])
    axes = [ax_a, ax_b, ax_c, ax_d, ax_e]

    ax_a.imshow(np.array(target), cmap="gray", vmin=0, vmax=255)
    ax_b.imshow(np.array(raster1), cmap="gray", vmin=0, vmax=255)
    ax_c.imshow(np.array(overlay1))
    ax_d.imshow(np.array(diff1))
    ax_e.imshow(np.array(diff2))
    for ax in axes:
        style_image_axes(ax, W, H)

    ts = dict(fontsize=8.5, pad=3)
    ax_a.set_title("(a) target $y$ — fixed-boundary calibration", **ts)
    ax_b.set_title("(b) candidate $\\hat{y}$, iteration 1", **ts)
    ax_c.set_title("(c) overlay on target", **ts)
    ax_d.set_title(f"(d) signed diff — IoU = {m1['IoU']:.3f}", **ts)
    ax_e.set_title(
        f"(e) after one refinement — IoU {m1['IoU']:.3f} $\\rightarrow$ {m2['IoU']:.3f}",
        **ts,
    )

    # ---- (a) calibration annotations -------------------------------------
    ax_a.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False,
                             edgecolor=BLUE, linewidth=1.0, zorder=5))

    # horizontal dimension arrow (below the axes) + per-axis scale equations
    ar = dict(arrowstyle="<->", color=BLUE, linewidth=0.8, shrinkA=0, shrinkB=0)
    ax_a.annotate("", xy=(0.0, -0.12), xytext=(1.0, -0.12),
                  xycoords="axes fraction", arrowprops=ar,
                  annotation_clip=False)
    ax_a.text(0.5, -0.26,
              f"x:  {bw_px} px / {L_um:g} µm = {sx:g} px/µm\n"
              f"y:  {bh_px} px / {W_um:g} µm = {sy:g} px/µm",
              transform=ax_a.transAxes, ha="center", va="top", ma="left",
              fontsize=7.5, color=BLUE, linespacing=1.35)

    # vertical dimension arrow (in the spacer column), short label
    pad = 10
    fy0 = (H + pad - y1) / (H + 2 * pad)   # bbox bottom, axes fraction
    fy1 = (H + pad - y0) / (H + 2 * pad)   # bbox top, axes fraction
    ax_a.annotate("", xy=(1.035, fy0), xytext=(1.035, fy1),
                  xycoords="axes fraction", arrowprops=ar,
                  annotation_clip=False)
    ax_a.text(1.075, (fy0 + fy1) / 2, f"{W_um:g} µm",
              transform=ax_a.transAxes, ha="left", va="center",
              rotation=90, fontsize=7.5, color=BLUE)

    # ---- sub-captions -----------------------------------------------------
    sub = dict(ha="center", va="top", fontsize=7, color=GRAY, linespacing=1.35)
    ax_b.text(0.5, -0.14,
              "rendered at the stored calibration,\n"
              f"never rescaled — output {gds_l1:.2f} × {gds_w1:.2f} µm",
              transform=ax_b.transAxes, **sub)
    ax_c.text(0.5, -0.14,
              "pink = candidate only\nblack = target only",
              transform=ax_c.transAxes, **sub)
    ax_d.text(0.5, -0.14,
              "red = spurious material (FP)\nblue = missing material (FN)",
              transform=ax_d.transAxes, **sub)
    ax_e.text(0.5, -0.14, "residual diff, iteration 2",
              transform=ax_e.transAxes, **sub)

    # ---- refine arrow between (d) and (e) ---------------------------------
    ax_e.annotate("", xy=(-0.045, 0.5), xytext=(-0.245, 0.5),
                  xycoords="axes fraction",
                  arrowprops=dict(arrowstyle="->", color="0.35",
                                  linewidth=0.9),
                  annotation_clip=False)
    ax_e.text(-0.145, 0.62, "refine", transform=ax_e.transAxes,
              ha="center", va="bottom", fontsize=7, color="0.35")

    for outp in (ARXIV / "fig_verification.pdf", FIGD / "fig_verification.png"):
        fig.savefig(outp, dpi=300)
        print("wrote", outp)


if __name__ == "__main__":
    main()
