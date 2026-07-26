"""Generate fig_trident_sidewall (the mirror-symmetric 1x2 splitter under the
same sidewall sweep: 3 stacks x 5 angles = 15 cells) from the committed
campaign data in data/agents/paper_swap/final1/output/sidewall_sweep/.

Symmetry control: the mirror-protected split balance stays pinned at 0.500 in
every cell while the unprotected total transmission moves with the fab angle,
platform-dependently. Single-column, curves-only: two vertically stacked
panels sharing the angle axis (no field maps).

Run from repo root: .venv/bin/python arxiv/scripts/make_fig_trident_sidewall.py
Writes arxiv/figures/fig_trident_sidewall.pdf and arxiv/figures/fig_trident_sidewall.png.
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "agents" / "paper_swap" / "final1" / "output" / "sidewall_sweep"
FIGS = ROOT / "paper" / "figures"
ARXIV = ROOT / "paper" / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "pdf.fonttype": 42,
    "font.size": 8, "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 200, "savefig.bbox": "tight",
})
# house palette — one fixed color per stack (shared with fig_sidewall_stacks)
C_SOI, C_SIN, C_TFLN = "#3c7ec1", "#c15f3c", "#327162"
C_GRAY, C_INK = "#8a8a8a", "#16161d"
STACKS = [("soi220", "220 nm SOI", C_SOI),
          ("sin400", "400 nm SiN", C_SIN),
          ("tfln400", "400 nm TFLN", C_TFLN)]
MARKERS = {"soi220": "o", "sin400": "s", "tfln400": "^"}
ANGLES = [0, 5, 15, 30, 45]

# --- load the tracked matrix ---------------------------------------------------
cells = json.loads((DATA / "trident_matrix.json").read_text())["cells"]
bal = {(c["stack"], c["angle_deg"]): c["balance"] for c in cells}
tot = {(c["stack"], c["angle_deg"]): c["total_T"] for c in cells}

# --- console cross-check of the prose claims ----------------------------------
devs = {k: abs(v - 0.5) for k, v in bal.items()}
worst = max(devs, key=devs.get)
max_dev = devs[worst]
print(f"{len(cells)} cells; balance min {min(bal.values()):.4f} max {max(bal.values()):.4f} "
      f"(max |dev| {max_dev:.4f} at {worst})")
print(f"SOI T at 0/15/45 deg: {tot[('soi220', 0)]:.3f} / {tot[('soi220', 15)]:.3f} / "
      f"{tot[('soi220', 45)]:.3f}")
print(f"SiN T range: {min(tot[('sin400', a)] for a in ANGLES):.3f}-"
      f"{max(tot[('sin400', a)] for a in ANGLES):.3f}; "
      f"TFLN T at 15/30/45: {tot[('tfln400', 15)]:.3f} / {tot[('tfln400', 30)]:.3f} / "
      f"{tot[('tfln400', 45)]:.3f}")

# --- figure --------------------------------------------------------------------
# single column: two stacked panels sharing the sidewall-angle axis
# (declared size is pre-crop; savefig.bbox=tight + 0.1 in pad lands at ~3.4 in wide)
fig = plt.figure(figsize=(3.22, 3.35))
gs = fig.add_gridspec(2, 1, left=0.155, right=0.99, top=0.965, bottom=0.115,
                      hspace=0.16)
axb = fig.add_subplot(gs[0])
axt = fig.add_subplot(gs[1], sharex=axb)

# (a) mirror-protected split balance — pinned in all 15 cells
axb.plot([0, 45], [0.5, 0.5], ls="--", lw=0.7, color=C_GRAY, zorder=1)
for stack, label, color in STACKS:
    axb.plot(ANGLES, [bal[(stack, a)] for a in ANGLES], color=color,
             marker=MARKERS[stack], lw=1.1, ms=2.8, zorder=3)
axb.text(22.5, 0.545, f"max $|b-0.5|={max_dev:.4f}$", fontsize=7,
         color=C_INK, ha="center", va="bottom")
axb.set_ylim(0.4, 0.6)
axb.set_yticks([0.40, 0.45, 0.50, 0.55, 0.60])
axb.set_ylabel("split balance", fontsize=8)
axb.spines["bottom"].set_bounds(-1.5, 45)
axb.tick_params(labelsize=7)
axb.tick_params(labelbottom=False)
axb.text(-0.19, 1.06, "(a)", transform=axb.transAxes, fontsize=9,
         fontweight="bold", color=C_INK, va="top")

# (b) unprotected total transmission — moves with the fab angle;
# frameless direct labels at the 45-degree line ends
for stack, label, color in STACKS:
    vals = [tot[(stack, a)] for a in ANGLES]
    axt.plot(ANGLES, vals, color=color, marker=MARKERS[stack],
             lw=1.1, ms=2.8, zorder=3)
    axt.text(46.8, vals[-1], label, fontsize=7, color=color, va="center", ha="left")
axt.set_xlim(-1.5, 66)
axt.set_ylim(0.4, 1.0)
axt.set_yticks([0.4, 0.6, 0.8, 1.0])
axt.spines["bottom"].set_bounds(-1.5, 45)
axt.set_xticks(ANGLES)
axt.set_xlabel("sidewall angle from vertical (deg)", fontsize=8)
axt.set_ylabel("total transmission", fontsize=8)
axt.tick_params(labelsize=7)
axt.text(-0.19, 1.06, "(b)", transform=axt.transAxes, fontsize=9,
         fontweight="bold", color=C_INK, va="top")

fig.savefig(ARXIV / "fig_trident_sidewall.pdf")
fig.savefig(FIGS / "fig_trident_sidewall.pdf")  # mirror convention
fig.savefig(FIGS / "fig_trident_sidewall.png", dpi=250)
plt.close(fig)
print(f"wrote {ARXIV / 'fig_trident_sidewall.pdf'}, {FIGS / 'fig_trident_sidewall.pdf'} "
      f"and {FIGS / 'fig_trident_sidewall.png'}")
