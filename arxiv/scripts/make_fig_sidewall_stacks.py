"""Generate the end-to-end realization and sidewall-sensitivity figure.

The upper row closes the F1 pipeline with three provenance-linked artifacts:
the source paper's withheld field panel, the exact blind input and executed
primitives program, and a retained full-wave field from the later SOI-retargeted
realization.  The lower row keeps the quantitative sidewall experiment and its
mirror-symmetric splitter control.

Run from repo root::

    .venv/bin/python arxiv/scripts/make_fig_sidewall_stacks.py

Writes ``arxiv/figures/fig_sidewall_stacks.pdf`` and ``.png``.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
COUPLER_DATA = (
    ROOT / "data" / "agents" / "catalog_swap" / "cat5" / "output" /
    "sidewall_sweep"
)
F1 = ROOT / "data" / "agents" / "paper_swap" / "final1"
F1_OUTPUT = F1 / "output"
TRIDENT_DATA = F1_OUTPUT / "sidewall_sweep"
FIGS = ROOT / "paper" / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "pdf.fonttype": 42,
    "font.size": 8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 200,
    "savefig.bbox": "tight",
})

# One fixed color per stack, shared with the other PDK figures.
C_SOI, C_SIN, C_TFLN = "#3c7ec1", "#c15f3c", "#327162"
C_GRAY, C_LIGHT, C_INK = "#858585", "#d4d4d4", "#16161d"
STACKS = [
    ("soi220", "220 nm SOI", C_SOI),
    ("sin400", "400 nm SiN", C_SIN),
    ("tfln400", "400 nm TFLN", C_TFLN),
]
MARKERS = {"soi220": "o", "sin400": "s", "tfln400": "^"}
CTRL_ANGLES = [0, 5, 15, 30, 45]
CURVE_TICKS = [0, 5, 15, 30, 45]


def _cells(name):
    return json.loads((COUPLER_DATA / name).read_text())["cells"]


def _source_field_image():
    """Extract the original Fig. 4 raster directly from the archived PDF.

    Page 3 contains repeated image objects because of the source PDF's internal
    structure.  The 1033 x 421 object is the normalized field panel in Fig. 4.
    """
    source_pdf = ROOT / "database" / "papers" / "1.pdf"
    with tempfile.TemporaryDirectory() as td:
        prefix = Path(td) / "source"
        subprocess.run(
            ["pdfimages", "-f", "3", "-l", "3", "-png",
             str(source_pdf), str(prefix)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for path in sorted(Path(td).glob("source-*.png")):
            with Image.open(path) as im:
                if im.size == (1033, 421):
                    return np.asarray(im.convert("RGB"))
    raise RuntimeError("Could not find the 1033 x 421 Fig. 4 field image")


def _crop_silhouette(path):
    """Use the same vertical crop for target and reconstruction."""
    image = np.asarray(Image.open(path).convert("L"))
    return image[42:614, :]


def _tint_mask(gray, color):
    """Render a grayscale black-on-white raster in a supplied ink color."""
    rgb = np.array(matplotlib.colors.to_rgb(color))
    coverage = 1.0 - gray.astype(float) / 255.0
    return 1.0 - coverage[..., None] * (1.0 - rgb[None, None, :])


def _crossing(values):
    angles = sorted(values)
    for lo, hi in zip(angles, angles[1:]):
        r0, r1 = values[lo], values[hi]
        if (r0 - 0.5) * (r1 - 0.5) < 0:
            return lo + (hi - lo) * (0.5 - r0) / (r1 - r0)
    return None


# Directional-coupler sensitivity matrices.
ratio = {stack: {} for stack, _, _ in STACKS}
for cell in _cells("stacks_matrix.json"):
    ratio[cell["stack"]][cell["angle_deg"]] = cell["ratio"]
for cell in _cells("soi_dense_matrix.json"):
    ratio["soi220"][cell["angle_deg"]] = cell["ratio"]
for cell in _cells("sidewall_matrix.json"):
    ratio["sin400"][cell["angle_deg"]] = cell["ratio"]

# Symmetric-splitter control and the retained vertical-wall field.
trident_cells = json.loads((TRIDENT_DATA / "trident_matrix.json").read_text())["cells"]
ctrl_bal = {(c["stack"], c["angle_deg"]): c["balance"] for c in trident_cells}
ctrl_tot = {(c["stack"], c["angle_deg"]): c["total_T"] for c in trident_cells}
ctrl_max_dev = max(abs(value - 0.5) for value in ctrl_bal.values())
soi_balance = ctrl_bal[("soi220", 0)]
soi_total = ctrl_tot[("soi220", 0)]
field = np.load(TRIDENT_DATA / "field_soi220_0deg.npz")
field_e2 = field["E2"] / float(field["E2"].max())

# Phase-A reconstruction evidence.
metrics = json.loads((F1_OUTPUT / "recreation_opus" / "metrics.json").read_text())
target = _crop_silhouette(F1 / "device_bw.png")
reconstruction = _crop_silhouette(F1_OUTPUT / "recreation_opus" / "raster.png")
source_field = _source_field_image()

# Console checks for all values quoted in the manuscript/caption.
soi_plateau = [ratio["soi220"][a] for a in sorted(ratio["soi220"]) if a <= 12.5]
print(
    f"F1 reconstruction: IoU={metrics['IoU']:.6f}; "
    f"SOI 0 deg balance={soi_balance:.9f}, T={soi_total:.9f}"
)
print(
    f"SiN 50/50 crossing: {_crossing(ratio['sin400']):.1f} deg; "
    f"TFLN: {_crossing(ratio['tfln400']):.1f} deg"
)
print(
    f"SOI 0-12.5 deg: n={len(soi_plateau)}, mean={np.mean(soi_plateau):.3f}, "
    f"range={min(soi_plateau):.3f}-{max(soi_plateau):.3f}; "
    f"control max deviation={ctrl_max_dev:.4f}"
)


# ---------------------------------------------------------------------------
# Figure.  The withheld source panel is visually separated from the worker's
# actual information path.  Only the blind input/program points to simulation.
fig = plt.figure(figsize=(7.0, 4.15))

# (a) Published, withheld reference.
axa = fig.add_axes([0.025, 0.635, 0.315, 0.265])
axa.imshow(source_field)
axa.axis("off")
axa.set_title("published field (withheld from worker)", fontsize=7.5, pad=3)
axa.text(-0.055, 1.12, "(a)", transform=axa.transAxes, fontsize=9,
         fontweight="bold", color=C_INK, va="top")

# Deliberately no arrow from the withheld reference into the worker-visible path.
fig.lines.append(plt.Line2D([0.352, 0.352], [0.615, 0.935],
                            transform=fig.transFigure, color=C_LIGHT,
                            lw=0.8, ls=(0, (2, 2))))
fig.text(0.352, 0.925, "not provided", fontsize=5.8, color=C_GRAY,
         ha="center", va="bottom")

# (b) Exact blind input and the executed primitives-only program.
axb1 = fig.add_axes([0.382, 0.765, 0.225, 0.125])
axb1.imshow(_tint_mask(target, C_INK), interpolation="antialiased")
axb1.axis("off")
axb1.text(0.0, 1.03, r"blind input: $40.0\times1.7\,\mu$m$^2$", transform=axb1.transAxes,
          fontsize=6.5, color=C_INK, va="bottom")
axb1.text(-0.12, 1.16, "(b)", transform=axb1.transAxes, fontsize=9,
          fontweight="bold", color=C_INK, va="top")

axb2 = fig.add_axes([0.382, 0.625, 0.225, 0.125])
axb2.imshow(_tint_mask(reconstruction, C_SOI), interpolation="antialiased")
axb2.axis("off")
axb2.text(0.0, 1.03, f"executed program: IoU $={metrics['IoU']:.3f}$",
          transform=axb2.transAxes, fontsize=6.5, color=C_SOI, va="bottom")

arrow = FancyArrowPatch(
    (0.615, 0.605), (0.655, 0.605), transform=fig.transFigure,
    arrowstyle="-|>", mutation_scale=8, lw=0.8, color=C_GRAY,
)
fig.patches.append(arrow)

# (c) Full-wave field of the SOI-retargeted descendant.
axc = fig.add_axes([0.675, 0.655, 0.285, 0.225])
im = axc.imshow(
    field_e2.T,
    origin="lower",
    aspect="auto",
    cmap="turbo",
    vmin=0,
    vmax=1,
    extent=[field["x"].min(), field["x"].max(),
            field["y"].min(), field["y"].max()],
    interpolation="bilinear",
)
axc.set_xlabel("$x$ ($\\mu$m)", fontsize=6.5, labelpad=1)
axc.tick_params(labelsize=5.5, length=2, pad=1)
for spine in axc.spines.values():
    spine.set_linewidth(0.5)
cax = fig.add_axes([0.965, 0.655, 0.008, 0.225])
cb = fig.colorbar(im, cax=cax, ticks=[0, 0.5, 1])
cb.ax.tick_params(labelsize=5.5, length=2, pad=1)
cb.outline.set_linewidth(0.45)
axc.set_title("retargeted SOI: independently normalized $|E|^2$", fontsize=7.2, pad=3)
axc.text(-0.115, 1.18, "(c)", transform=axc.transAxes, fontsize=9,
         fontweight="bold", color=C_INK, va="top")
axc.text(0.025, 0.94,
         f"balance $={soi_balance:.5f}$\nmonitored $T={soi_total:.3f}$",
         transform=axc.transAxes, fontsize=6.0, color="white", ha="left", va="top")

# Divide the end-to-end evidence from the fabrication-sensitivity controls.
fig.lines.append(plt.Line2D([0.025, 0.975], [0.565, 0.565],
                            transform=fig.transFigure, color=C_LIGHT, lw=0.65))

# (d) Coupling ratio versus uniform sidewall angle.
axd = fig.add_axes([0.075, 0.095, 0.505, 0.385])
axd.plot([-1.2, 45], [0.5, 0.5], ls="--", lw=0.75, color=C_GRAY, zorder=1)
axd.text(0.2, 0.53, "50/50", fontsize=6.2, color=C_GRAY, va="bottom")
for stack, label, color in STACKS:
    angles = sorted(ratio[stack])
    values = [ratio[stack][angle] for angle in angles]
    axd.plot(angles, values, color=color, marker=MARKERS[stack], lw=1.15,
             ms=3.0, zorder=3)
    axd.text(46.0, values[-1], label, fontsize=6.8, color=color,
             va="center", ha="left")
axd.text(1.0, 0.84, "SOI, 0 to 12.5 deg: mean $\\approx 0.69$",
         fontsize=6.1, color=C_SOI, ha="left", va="bottom")
axd.set_xlim(-1.2, 58)
axd.set_ylim(-0.04, 1.06)
axd.spines["bottom"].set_bounds(-1.2, 45)
axd.set_xticks(CURVE_TICKS)
axd.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
axd.set_xlabel("sidewall angle from vertical (deg)", fontsize=7.5)
axd.set_ylabel("coupling ratio", fontsize=7.5)
axd.tick_params(labelsize=6.5)
axd.text(-0.115, 1.05, "(d)", transform=axd.transAxes, fontsize=9,
         fontweight="bold", color=C_INK, va="top")

# (e,f) Mirror-symmetric splitter control.
axe = fig.add_axes([0.675, 0.295, 0.245, 0.185])
axf = fig.add_axes([0.675, 0.095, 0.245, 0.165], sharex=axe)
axe.plot([0, 45], [0.5, 0.5], ls="--", lw=0.7, color=C_GRAY, zorder=1)
for stack, _, color in STACKS:
    axe.plot(CTRL_ANGLES, [ctrl_bal[(stack, angle)] for angle in CTRL_ANGLES],
             color=color, marker=MARKERS[stack], lw=1.0, ms=2.5, zorder=3)
axe.text(22.5, 0.555, f"max $|b-0.5|={ctrl_max_dev:.4f}$", fontsize=6.2,
         color=C_INK, ha="center", va="bottom")
axe.set_ylim(0.4, 0.6)
axe.set_yticks([0.40, 0.50, 0.60])
axe.set_ylabel("split balance", fontsize=7)
axe.spines["bottom"].set_bounds(-1.5, 45)
axe.tick_params(labelsize=6.2, labelbottom=False)
axe.text(-0.23, 1.08, "(e)", transform=axe.transAxes, fontsize=9,
         fontweight="bold", color=C_INK, va="top")

for stack, _, color in STACKS:
    values = [ctrl_tot[(stack, angle)] for angle in CTRL_ANGLES]
    axf.plot(CTRL_ANGLES, values, color=color, marker=MARKERS[stack],
             lw=1.0, ms=2.5, zorder=3)
    short = {"soi220": "SOI", "sin400": "SiN", "tfln400": "TFLN"}[stack]
    axf.text(47.0, values[-1], short, fontsize=6.3, color=color,
             va="center", ha="left")
axf.set_xlim(-1.5, 63)
axf.set_ylim(0.4, 1.0)
axf.set_yticks([0.4, 0.6, 0.8, 1.0])
axf.spines["bottom"].set_bounds(-1.5, 45)
axf.set_xticks(CTRL_ANGLES)
axf.set_xlabel("sidewall angle (deg)", fontsize=7)
axf.set_ylabel("total transmission", fontsize=7)
axf.tick_params(labelsize=6.2)
axf.text(-0.39, 1.08, "(f)", transform=axf.transAxes, fontsize=9,
         fontweight="bold", color=C_INK, va="top")

fig.savefig(FIGS / "fig_sidewall_stacks.pdf")
fig.savefig(FIGS / "fig_sidewall_stacks.png", dpi=250)
plt.close(fig)
print(f"wrote {FIGS / 'fig_sidewall_stacks.pdf'} and {FIGS / 'fig_sidewall_stacks.png'}")
