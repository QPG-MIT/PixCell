"""Pilot post-processing: heatmap figure + verdict + cost ledger append."""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path("/Users/aadarwal/src/QPG-MIT/homi-anu-powered")
PILOT = ROOT / "experiments/catalog_swap/cat5/output/sweep_pilot"
d = json.loads((PILOT / "sweep_matrix.json").read_text())

gaps = d["axes"]["gap_um"]
lengths = d["axes"]["coupling_length"]
M = np.full((len(gaps), len(lengths)), np.nan)
T = np.full_like(M, np.nan)
for c in d["cells"]:
    if c.get("ratio") is None:
        continue
    i = gaps.index(c["params"]["gap_um"])
    j = lengths.index(c["params"]["coupling_length"])
    M[i, j] = c["ratio"]
    T[i, j] = c.get("total_T", np.nan)

best = np.unravel_index(np.nanargmin(np.abs(M - 0.5)), M.shape)
best_ratio = M[best]

plt.rcParams.update({"font.family": "serif", "font.size": 9})
fig, ax = plt.subplots(figsize=(4.6, 3.4))
im = ax.imshow(M, cmap="viridis", vmin=0, vmax=1, aspect="auto", origin="lower")
ax.set_xticks(range(len(lengths)), [f"{v:g}" for v in lengths])
ax.set_yticks(range(len(gaps)), [f"{v:g}" for v in gaps])
ax.set_xlabel("interaction length (µm)")
ax.set_ylabel("gap (µm)")
for i in range(len(gaps)):
    for j in range(len(lengths)):
        if not np.isnan(M[i, j]):
            ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center",
                    fontsize=7, color="w" if M[i, j] < 0.6 else "k")
ax.add_patch(plt.Rectangle((best[1] - 0.5, best[0] - 0.5), 1, 1,
                           fill=False, ec="#ff5555", lw=2))
ax.set_title(f"measured cross-coupling ratio (full-wave, SiN stack)\n"
             f"nearest to 0.50: gap={gaps[best[0]]:g}, L={lengths[best[1]]:g} "
             f"→ {best_ratio:.2f}", fontsize=8)
fig.colorbar(im, shrink=0.8)
for out in (ROOT / "paper/figures/fig_sweep_feasibility.pdf",
            ROOT / "paper/figures/fig_sweep_feasibility.png",
            ROOT / "paper/arxiv/fig_sweep_feasibility.pdf"):
    fig.savefig(out, bbox_inches="tight", dpi=200)

# verdict (representation-relative)
crosses = np.nanmin(M) <= 0.5 <= np.nanmax(M)
if abs(best_ratio - 0.5) <= 0.05:
    verdict = "target-point-found"
elif crosses:
    verdict = "target-bracketed: 0.50 crossed between grid cells (refine locally)"
else:
    verdict = ("infeasible-for-this-representation within swept ranges "
               "(representation-relative; other decompositions/knobs may differ)")

ledger_p = ROOT / "experiments/catalog_swap/cloud_costs.json"
ledger = json.loads(ledger_p.read_text()) if ledger_p.exists() else {}
ledger["cat5_sweep_pilot"] = {
    "tasks": [{"task_id": c.get("task_id"), "billed_fc": c.get("billed_fc")}
              for c in d["cells"] if c.get("task_id")],
    "total_billed_fc": d.get("total_billed_fc"),
    "total_estimate_fc": d.get("total_estimate_fc"),
}
ledger_p.write_text(json.dumps(ledger, indent=1))

summary = {
    "verdict": verdict,
    "best_cell": {"gap_um": gaps[best[0]], "coupling_length": lengths[best[1]],
                  "ratio": float(best_ratio)},
    "ratio_range": [float(np.nanmin(M)), float(np.nanmax(M))],
    "total_billed_fc": d.get("total_billed_fc"),
    "n_failed_cells": sum(1 for c in d["cells"] if c.get("ratio") is None),
}
(PILOT / "pilot_summary.json").write_text(json.dumps(summary, indent=1))
print(json.dumps(summary, indent=1))
