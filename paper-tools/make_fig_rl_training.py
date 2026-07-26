"""fig_rl_training: the reported lineage's training and transfer curves.

(a) Synthetic evaluation ladder: per-tier IoU on the fixed seed-disjoint eval
    pool, across the main lineage's 95 GRPO steps (trunk 0-30, bridge-1
    30-65, bridge-2 65-95; scheduled evals through cumulative step 85).
(b) Dense per-step training IoU on the L4 real-figure tier versus the
    training-excluded development benchmark (single-attempt evaluation points;
    k=8 endpoints). The sequential stages show divergence and later recovery,
    but do not isolate the effect of expanding the L4 corpus.
Data: rl/runs/*/metrics.jsonl and rl/reports/benchmark_eval_bridge2.json
      (artifacts, not narrative documents).

Run: .venv/bin/python paper-tools/make_fig_rl_training.py
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
ARXIV = REPO / "arxiv/figures"
FIGD = REPO / "arxiv/figures"
FIGD.mkdir(parents=True, exist_ok=True)
RUNS = REPO / "rl/reports/runs_ledger"  # tracked ledger (metrics/config/checkpoints; probes copied here)

plt.rcParams.update({
    "font.family": "serif", "font.size": 8, "axes.spines.top": False,
    "axes.spines.right": False, "figure.dpi": 200, "savefig.bbox": "tight",
    "axes.linewidth": 0.7, "xtick.major.width": 0.7, "ytick.major.width": 0.7,
})

LINEAGE = [
    ("trunk", "pixcell-Qwen-Qwen3.6-35B-A3B-8g-8b-lr1e-05-20260708-0953", 0),
    ("bridge-1", "pixcell-Qwen-Qwen3.6-35B-A3B-8g-8b-lr1e-05-20260708-1043", 30),
    ("bridge-2", "pixcell-Qwen-Qwen3.6-35B-A3B-8g-8b-lr1e-05-20260708-1209", 65),
]

# tiers: ordered difficulty -> one-hue ramp, light (easy) to dark (hard)
TIER_C = {"L0": "#a8c4de", "L1": "#6f9dc8", "L2": "#3c7ec1", "L3": "#1d4569"}
C_TRAIN = "#c15f3c"   # house warm accent: training-tier curve
C_BENCH = "#444444"


def load_series():
    evals, train = [], []
    for name, d, off in LINEAGE:
        for line in open(RUNS / d / "metrics.jsonl"):
            r = json.loads(line)
            s = r.get("step")
            if s is None:
                continue
            if r.get("env/L4/iou") is not None:
                train.append({"abs": off + s, "l4": r["env/L4/iou"]})
            if "test/env/all/iou" in r:
                fin = [r.get(f"test/env/final_{i}/iou") for i in range(1, 9)]
                fin = [x for x in fin if x is not None]
                evals.append({
                    "abs": off + s,
                    "bench": sum(fin) / len(fin) if fin else None,
                    **{f"L{i}": r.get(f"test/env/L{i}/iou") for i in range(4)},
                })
    # drop the duplicated eval at each stage seam (step 0 of run n+1 == final
    # weights of run n): keep the later run's point only when the abs step is new
    seen, dedup = set(), []
    for e in sorted(evals, key=lambda e: e["abs"]):
        if e["abs"] in seen:
            continue
        seen.add(e["abs"])
        dedup.append(e)
    return dedup, sorted(train, key=lambda t: t["abs"])


def main():
    evals, train = load_series()
    first_draw = json.load(open(REPO / "rl/reports/benchmark_eval_bridge2.json"))

    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.5))

    # ---------------------------------------------------------- (a) mastery ladder
    ax = axes[0]
    xs = [e["abs"] for e in evals]
    NUDGE = {"L0": 0.0, "L1": 0.0, "L2": -0.035, "L3": 0.035}
    for tier in ("L0", "L1", "L2", "L3"):
        ys = [e[tier] for e in evals]
        ax.plot(xs, ys, "-o", ms=2.6, lw=1.2, color=TIER_C[tier])
        ax.text(xs[-1] + 1.5, ys[-1] + NUDGE[tier], tier, color=TIER_C[tier],
                fontsize=7, va="center")
    for x in (30, 65):
        ax.axvline(x, color="#bbbbbb", lw=0.7, ls=":")
    ax.set_xlim(-2, 97)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("GRPO step (lineage-cumulative)")
    ax.set_ylabel("IoU (fixed seed-disjoint pool)")
    ax.set_title("(a) synthetic evaluation by tier", fontsize=8)

    # ------------------------------------------------- (b) real-figure transfer
    ax = axes[1]
    txs = [t["abs"] for t in train if t["l4"] is not None and t["abs"] >= 30]
    tys = [t["l4"] for t in train if t["l4"] is not None and t["abs"] >= 30]
    ax.plot(txs, tys, "-", lw=0.6, color=C_TRAIN, alpha=0.30)
    # 5-step rolling mean makes the memorize->generalize arc readable
    roll = [sum(tys[max(0, i - 4):i + 1]) / len(tys[max(0, i - 4):i + 1])
            for i in range(len(tys))]
    ax.plot(txs, roll, "-", lw=1.4, color=C_TRAIN)
    ax.text(102, 0.78, "training-figure tier\n(train-time IoU)", color=C_TRAIN,
            fontsize=7, ha="right")
    bxs = [e["abs"] for e in evals if e["bench"] is not None]
    bys = [e["bench"] for e in evals if e["bench"] is not None]
    ax.plot(bxs, bys, "o", ms=3.4, mfc="white", mec=C_BENCH, mew=0.9)
    ax.plot(bxs, bys, "-", lw=0.7, color=C_BENCH, alpha=0.45)
    ax.text(30, 0.015, "training-excluded benchmark (one sample)", color=C_BENCH,
            fontsize=7)
    # k=8 robust endpoints for the final checkpoint
    ax.plot([95], [first_draw["bench_mean_of_means"]], "o", ms=4.5, color="black",
            zorder=5)
    ax.plot([95], [first_draw["bench_mean_of_bests"]], "D", ms=4.5, mfc="white",
            mec="black", mew=1.1, zorder=5)
    ax.annotate(f"eval@1 {first_draw['bench_mean_of_means']:.2f}",
                xy=(95, first_draw["bench_mean_of_means"]),
                xytext=(72, 0.36), fontsize=7,
                arrowprops=dict(arrowstyle="-", lw=0.6, color="#888"))
    ax.annotate(f"best@8 {first_draw['bench_mean_of_bests']:.2f}",
                xy=(95, first_draw["bench_mean_of_bests"]),
                xytext=(72, 0.55), fontsize=7,
                arrowprops=dict(arrowstyle="-", lw=0.6, color="#888"))
    for x in (30, 65):
        ax.axvline(x, color="#bbbbbb", lw=0.7, ls=":")
    ax.text(31, 0.955, "13 figs", fontsize=6.2, color="#777")
    ax.text(66, 0.955, "18 figs", fontsize=6.2, color="#777")
    ax.set_xlim(-2, 104)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("GRPO step (lineage-cumulative)")
    ax.set_ylabel("IoU")
    ax.set_title("(b) real figures: training vs benchmark", fontsize=8)

    fig.tight_layout(w_pad=1.6)
    for out in (ARXIV / "fig_rl_training.pdf", FIGD / "fig_rl_training.png"):
        fig.savefig(out)
        print("wrote", out)


if __name__ == "__main__":
    main()
