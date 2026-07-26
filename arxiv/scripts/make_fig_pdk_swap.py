"""Generate the PDK-swap paper figures (fig_spectra, fig_cross_matrix) from the
committed campaign data in data/agents/pdk_swap/.

Run from repo root: .venv/bin/python arxiv/scripts/make_fig_pdk_swap.py
(Restored from paper/reports/pdk_swap_proof/paper/make_figures.py after that
tree was pruned; paths retargeted to the consolidated data layout.)
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "paper" / "figures"
ARXIV = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
EXP = ROOT / "data" / "agents" / "pdk_swap"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "pdf.fonttype": 42,
    "font.size": 8, "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 200, "savefig.bbox": "tight",
})
# house palette
C_OPUS, C_CODEX, C_BASE, C_OK = "#3c7ec1", "#c15f3c", "#8a8a8a", "#327162"
C_FAIL_BG, C_FAIL_TX = "#f0e6e1", "#9c4a2e"


def load_iters(path):
    lg = json.loads(Path(path).read_text())
    items = lg if isinstance(lg, list) else lg.get("iterations", [])
    return [float(i["iou"]) for i in items]


# --- Fig 1: IoU trajectories -------------------------------------------------
opus = load_iters(EXP / "output/recreation/recreation_log.json")
codex = load_iters(EXP / "output/recreation_codex/recreation_log.json")
jee_iou = json.loads((EXP / "output/jee_refine/refined_metrics.json").read_text())["IoU"]

fig, ax = plt.subplots(figsize=(4.6, 2.9))
ax.plot(range(1, len(opus) + 1), opus, "o-", color=C_OPUS, label="Opus 4.8 medium (live-agent default)")
ax.plot(range(1, len(codex) + 1), codex, "s-", color=C_CODEX, label="codex gpt-5.5 xhigh fast")
ax.plot([len(opus), len(opus) + 1], [opus[-1], jee_iou], "--", color=C_OPUS, alpha=0.6)
ax.plot([len(opus) + 1], [jee_iou], "D", color=C_OPUS, mfc="white")
ax.annotate("JEE polish\n(Nelder–Mead, −20% SSE)", (len(opus) + 1, jee_iou),
            xytext=(4.6, 0.44), fontsize=7.5, color=C_OPUS,
            arrowprops=dict(arrowstyle="-", color=C_OPUS, alpha=0.5))
ax.annotate("cubic-centerline fit\nto the image", (4, codex[3]), xytext=(2.1, 0.80),
            fontsize=7.5, color=C_CODEX,
            arrowprops=dict(arrowstyle="-", color=C_CODEX, alpha=0.5))
ax.set_xlabel("recreation iteration")
ax.set_ylabel("IoU vs input image")
ax.set_ylim(0, 0.9)
ax.legend(fontsize=7.5, loc="lower right", frameon=False)
fig.savefig(OUT / "fig_iou_trajectory.pdf")
fig.savefig(OUT / "fig_iou_trajectory.png")
plt.close(fig)
print("fig 1 done")

# --- Fig 2: analytic transmission spectra ------------------------------------
from homi.spec_optimization import analytic_transmission  # noqa: E402

baseline = json.loads((EXP / "output/baseline_eval.json").read_text())["stacks"]
stacks = ["soi220", "sin400", "tfln400"]
labels = {"soi220": "220 nm SOI", "sin400": "400 nm SiN", "tfln400": "400 nm TFLN"}
opt = {}  # per stack: (n_eff, n_g, dL) from the verified Opus designs
for s in stacks:
    for f in (EXP / f"output/optimize/{s}").glob("*.json"):
        if f.name == "optimization_log.json":
            lg = json.loads(f.read_text())
            it = (lg if isinstance(lg, list) else lg.get("iterations", []))[-1]
            opt[s] = (float(it["n_eff"]), float(it["n_g"]),
                      float(it["delta_length_measured_um"]))

n = 4001
wls = [1.53 + i * 0.04 / (n - 1) for i in range(n)]
wnm = [w * 1000 for w in wls]
fig, axes = plt.subplots(3, 1, figsize=(3.4, 3.8), sharex=True)
for ax, s in zip(axes, stacks):
    b = baseline[s]
    t_base = analytic_transmission(wls, b["n_eff"], b["n_g"], 10.0)
    ne, ng, dl = opt[s]
    t_opt = analytic_transmission(wls, ne, ng, dl)
    ax.plot(wnm, t_base, color=C_BASE, lw=0.9)
    ax.plot(wnm, t_opt, color=C_OK, lw=1.1)
    ax.set_ylabel(f"{labels[s]}\nT (bar port)", fontsize=7.5)
    ax.set_ylim(-0.05, 1.62)
    ax.set_yticks([0, 0.5, 1])
    # direct labels in the reserved headroom (no legend boxes over the curves)
    ax.text(0.02, 0.975, f"as pictured  ΔL = 10 µm — FSR {b['fsr_nm']:.0f} nm",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.8, color="#6e6e6e")
    ax.text(0.02, 0.855, f"retuned  ΔL = {dl:.1f} µm — FSR 8.000 nm",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.8, color=C_OK)
axes[-1].set_xlabel("wavelength (nm)")
fig.align_ylabels(axes)
fig.savefig(OUT / "fig_spectra.pdf")
fig.savefig(ARXIV / "fig_spectra.pdf")
fig.savefig(OUT / "fig_spectra.png")
plt.close(fig)
print("fig 2 done")

# --- Fig 3: cross-stack matrix ------------------------------------------------
cm = json.loads((EXP / "output/optimize/cross_matrix.json").read_text())["design_stack"]
fig, ax = plt.subplots(figsize=(3.2, 2.7))
vals = [[cm[d][e] for e in stacks] for d in stacks]
for i, d in enumerate(stacks):
    for j, e in enumerate(stacks):
        v = vals[i][j]
        ok = abs(v - 8.0) / 8.0 <= 0.02
        ax.add_patch(plt.Rectangle((j, 2 - i), 1, 1, facecolor=C_OK if ok else C_FAIL_BG,
                                   edgecolor="white", lw=2))
        ax.text(j + 0.5, 2 - i + 0.5, f"{v:.2f}", ha="center", va="center",
                fontsize=9, color="white" if ok else C_FAIL_TX,
                fontweight="bold" if ok else "normal")
ax.set_xlim(0, 3); ax.set_ylim(0, 3)
ax.set_xticks([0.5, 1.5, 2.5]); ax.set_xticklabels([labels[s] for s in stacks], fontsize=8)
ax.set_yticks([2.5, 1.5, 0.5]); ax.set_yticklabels([labels[s] for s in stacks], fontsize=8)
ax.set_xlabel("evaluated on stack"); ax.set_ylabel("design optimized for")
ax.set_aspect("equal"); ax.tick_params(length=0)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.set_title("FSR (nm) — target 8.00 ± 2%", fontsize=8.5)
fig.savefig(OUT / "fig_cross_matrix.pdf")
fig.savefig(ARXIV / "fig_cross_matrix.pdf")
fig.savefig(OUT / "fig_cross_matrix.png")
plt.close(fig)
print("fig 3 done")
