# Evidence Collection: Multi-Seed & Multi-Turn Generation

## What was done

Analyzed 640 seed trajectories and 63 exploration experiments across 9 photonic components and 14 VLM models. Extracted quantitative metrics and visual evidence into `figures/` to support two core claims about HOMI's propose-verify architecture.

## Claim 1: Multi-seed exploration is beneficial

**Key numbers:**
- Mean IoU spread (best vs worst seed): **0.246** across 63 experiments
- 84% of experiments show 10+ point spread between seeds
- First seed wins only **12.7%** of the time — winner is unpredictable
- Best seed averages **+11.5 IoU points** over the median
- Largest spread: **0.673** (FINAL_4, Claude Opus 4.5)

**Why include:** Without seed diversity, you get the median result. Different seeds explore fundamentally different geometric strategies (e.g., thick coupled waveguides vs thin crossing waveguides for the same coupler). No single seed reliably wins — the system must explore to find the right approach.

**Figures:** `figures/seed_diversity/` — 10-seed raster grids for FINAL_4 showing IoU range 0.31-0.87

## Claim 2: Iterative turn refinement is beneficial

**Key numbers:**
- 65.9% of seeds peak at a turn after turn 1
- Best-of-2 turns: +10% avg gain; best-of-5 turns: +18.3%
- Paired t-test: t = 10.86, p << 0.001
- Phase 2 extended iteration: 73% of seeds improved, avg +22.3%

**Why include:** The model self-corrects across turns. Even when individual turns regress (turn3 of FINAL_6 drops to 57%), the system recovers to 97.5% by turn5. The ratchet mechanism (keep best result) makes the process monotonically non-decreasing while allowing the model to explore.

**Figures:** `figures/turn_improvement/` — 3 sequences with overlay PNGs at each turn:
1. FINAL_6: 71.8% -> 62.7% -> 57.0% -> 79.8% -> **97.5%** (V-recovery to near-perfect)
2. FINAL_4: 73.7% -> 66.5% -> 60.5% -> 82.4% -> **94.1%** (same pattern, different component)
3. 1x2 Coupler: 21.3% -> **61.5%** (3x improvement in one turn)

**Figures:** `figures/before_after/` — 3 dramatic before/after overlay pairs (deltas of +33 to +40 IoU points)

## File inventory

```
to be included/
  running.md              <- this file
  collect_figures.py      <- script to regenerate all figures
  figures/
    paper_statistics.json <- all numbers cited above
    target_FINAL_4.png    <- target device images
    target_FINAL_6.png
    target_1x2_coupler.png
    turn_improvement/     <- 3 sequences (raster, overlay, diff per turn + metrics)
    seed_diversity/       <- 2 seed grids (10 and 6 seeds, raster + overlay per seed)
    before_after/         <- 3 dramatic pairs (before/after raster, overlay, diff)
```

## Suggested paper figures

1. **Figure N (Seed Diversity):** Grid of 6 rasters from FINAL_4 seeds (best/mid/worst) alongside target, with IoU labels. Shows different geometric strategies from the same prompt.

2. **Figure N+1 (Turn Progression):** 5-panel sequence of FINAL_6 overlays (turns 1-5) with IoU labels. The V-shaped dip and recovery tells a compelling self-correction story.

3. **Figure N+2 (Before/After):** Side-by-side overlay of FINAL_6 turn3 (57%) vs turn5 (97.5%). Single most dramatic improvement.
