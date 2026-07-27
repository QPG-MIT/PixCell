#!/usr/bin/env python3
"""
Collect and organize visual evidence for the HOMI paper.
Demonstrates: (1) seed diversity benefit, (2) turn-by-turn improvement.

Copies relevant PNGs into paper/final/figures/ with descriptive names,
and generates summary data tables.
"""

import shutil
import json
from pathlib import Path

PROJECTS = Path(__file__).resolve().parents[2] / "projects"
FIGURES = Path(__file__).resolve().parents[2] / "paper/final/figures"

# ============================================================
# 1. TURN IMPROVEMENT SEQUENCES
# ============================================================

turn_examples = [
    {
        "name": "FINAL_6_gemini3pro_run006",
        "label": "FINAL_6 (gemini-3-pro-preview) — 71.8% → 97.5% IoU",
        "turns": {
            "turn1": PROJECTS / "gemini_images_run/FINAL_6/benchmark_gemini_gemini-3-pro-preview/phase1/benchmark_gemini-3-pro-preview/run_006/turn1",
            "turn2": PROJECTS / "gemini_images_run/FINAL_6/benchmark_gemini_gemini-3-pro-preview/phase1/benchmark_gemini-3-pro-preview/run_006/turn2",
            "turn3": PROJECTS / "gemini_images_run/FINAL_6/benchmark_gemini_gemini-3-pro-preview/phase2/benchmark_gemini-3-pro-preview/run_006/turn3",
            "turn4": PROJECTS / "gemini_images_run/FINAL_6/benchmark_gemini_gemini-3-pro-preview/phase2/benchmark_gemini-3-pro-preview/run_006/turn4",
            "turn5": PROJECTS / "gemini_images_run/FINAL_6/benchmark_gemini_gemini-3-pro-preview/phase2/benchmark_gemini-3-pro-preview/run_006/turn5",
        },
        "ious": [0.7184, 0.6265, 0.5703, 0.7980, 0.9750],
    },
    {
        "name": "FINAL_4_gemini3pro_run009",
        "label": "FINAL_4 (gemini-3-pro-preview) — 73.7% → 94.1% IoU",
        "turns": {
            "turn1": PROJECTS / "gemini_images_run/FINAL_4/benchmark_gemini_gemini-3-pro-preview/phase1/benchmark_gemini-3-pro-preview/run_009/turn1",
            "turn2": PROJECTS / "gemini_images_run/FINAL_4/benchmark_gemini_gemini-3-pro-preview/phase1/benchmark_gemini-3-pro-preview/run_009/turn2",
            "turn3": PROJECTS / "gemini_images_run/FINAL_4/benchmark_gemini_gemini-3-pro-preview/phase2/benchmark_gemini-3-pro-preview/run_009/turn3",
            "turn4": PROJECTS / "gemini_images_run/FINAL_4/benchmark_gemini_gemini-3-pro-preview/phase2/benchmark_gemini-3-pro-preview/run_009/turn4",
            "turn5": PROJECTS / "gemini_images_run/FINAL_4/benchmark_gemini_gemini-3-pro-preview/phase2/benchmark_gemini-3-pro-preview/run_009/turn5",
        },
        "ious": [0.7370, 0.6650, 0.6054, 0.8235, 0.9408],
    },
    {
        "name": "1x2coupler_gemini3flash_run002",
        "label": "1x2 Coupler (gemini-3-flash-preview) — 21.3% → 61.5% IoU",
        "turns": {
            "turn1": PROJECTS / "1x2_coupler/benchmark_gemini_gemini-3-flash-preview/phase1/run_002/turn1",
            "turn2": PROJECTS / "1x2_coupler/benchmark_gemini_gemini-3-flash-preview/phase1/run_002/turn2",
        },
        "ious": [0.2129, 0.6153],
    },
]

print("=" * 60)
print("COLLECTING TURN IMPROVEMENT FIGURES")
print("=" * 60)

for ex in turn_examples:
    dest_dir = FIGURES / "turn_improvement" / ex["name"]
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n{ex['label']}")
    for turn_name, turn_path in ex["turns"].items():
        for img_type in ["raster.png", "overlay.png", "diff.png"]:
            src = turn_path / img_type
            if src.exists():
                dst = dest_dir / f"{turn_name}_{img_type}"
                shutil.copy2(src, dst)
                print(f"  ✓ {turn_name}/{img_type}")
            else:
                print(f"  ✗ {turn_name}/{img_type} NOT FOUND")
        # Also copy metrics
        metrics_src = turn_path / "metrics.json"
        if metrics_src.exists():
            shutil.copy2(metrics_src, dest_dir / f"{turn_name}_metrics.json")

    # Write summary
    with open(dest_dir / "summary.json", "w") as f:
        json.dump({"label": ex["label"], "ious": ex["ious"]}, f, indent=2)

# ============================================================
# 2. SEED DIVERSITY EXAMPLES
# ============================================================

seed_diversity_examples = [
    {
        "name": "FINAL_4_gemini3flash_10seeds",
        # Values are the archived turn-2 metrics.json IoUs (verbatim, 4 dp)
        "label": "FINAL_4 (gemini-3-flash-preview) — 10 seeds, IoU 0.31–0.82",
        "base": PROJECTS / "gemini_images_run/FINAL_4/benchmark_gemini_gemini-3-flash-preview/phase1/benchmark_gemini-3-flash-preview",
        "seeds": [
            ("run_006", 0.8235, "best"),
            ("run_008", 0.7375, "2nd"),
            ("run_010", 0.7365, "3rd"),
            ("run_000", 0.6620, "mid-high"),
            ("run_004", 0.6554, "mid"),
            ("run_003", 0.5990, "mid-low"),
            ("run_009", 0.5951, "mid-low"),
            ("run_002", 0.4591, "low"),
            ("run_007", 0.4061, "very-low"),
            ("run_001", 0.3109, "worst"),
        ],
    },
    {
        "name": "FINAL_4_gemini3pro_10seeds",
        # Values are the archived turn-2 metrics.json IoUs (verbatim, 4 dp)
        "label": "FINAL_4 (gemini-3-pro-preview) — 11 seeds (10 archive-ranked), IoU 0.36–0.87",
        "base": PROJECTS / "gemini_images_run/FINAL_4/benchmark_gemini_gemini-3-pro-preview/phase1/benchmark_gemini-3-pro-preview",
        "seeds": [
            ("run_000", 0.8684, "best"),
            ("run_007", 0.8258, "2nd"),
            ("run_006", 0.7797, "3rd"),
            ("run_010", 0.6102, "low"),
            ("run_004", 0.5031, "very-low"),
            ("run_001", 0.4373, "worst"),
        ],
    },
]

print("\n" + "=" * 60)
print("COLLECTING SEED DIVERSITY FIGURES")
print("=" * 60)

for ex in seed_diversity_examples:
    dest_dir = FIGURES / "seed_diversity" / ex["name"]
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n{ex['label']}")

    seed_data = []
    for run_id, iou, rank_label in ex["seeds"]:
        # Try turn2 first (final phase1 result), fallback to turn1
        for turn in ["turn2", "turn1"]:
            src_dir = ex["base"] / run_id / turn
            if src_dir.exists():
                for img in ["raster.png", "overlay.png"]:
                    src = src_dir / img
                    if src.exists():
                        dst = dest_dir / f"{rank_label}_{run_id}_iou{iou:.3f}_{img}"
                        shutil.copy2(src, dst)
                print(f"  ✓ {run_id} ({rank_label}, IoU={iou:.3f}) from {turn}")
                seed_data.append({"run": run_id, "iou": iou, "rank": rank_label, "turn": turn})
                break
        else:
            print(f"  ✗ {run_id} NOT FOUND at {ex['base']}")

    with open(dest_dir / "summary.json", "w") as f:
        json.dump({"label": ex["label"], "seeds": seed_data}, f, indent=2)

# ============================================================
# 3. DRAMATIC BEFORE/AFTER PAIRS
# ============================================================

before_after = [
    {
        "name": "FINAL_6_57pct_to_97pct",
        "label": "FINAL_6: turn3 (57%) → turn5 (97.5%)",
        "before": PROJECTS / "gemini_images_run/FINAL_6/benchmark_gemini_gemini-3-pro-preview/phase2/benchmark_gemini-3-pro-preview/run_006/turn3",
        "after": PROJECTS / "gemini_images_run/FINAL_6/benchmark_gemini_gemini-3-pro-preview/phase2/benchmark_gemini-3-pro-preview/run_006/turn5",
        "before_iou": 0.5703,
        "after_iou": 0.9750,
    },
    {
        "name": "1x2coupler_21pct_to_62pct",
        "label": "1x2 Coupler: turn1 (21%) → turn2 (62%)",
        "before": PROJECTS / "1x2_coupler/benchmark_gemini_gemini-3-flash-preview/phase1/run_002/turn1",
        "after": PROJECTS / "1x2_coupler/benchmark_gemini_gemini-3-flash-preview/phase1/run_002/turn2",
        "before_iou": 0.2129,
        "after_iou": 0.6153,
    },
    {
        "name": "FINAL_4_60pct_to_94pct",
        "label": "FINAL_4: turn3 (60%) → turn5 (94%)",
        "before": PROJECTS / "gemini_images_run/FINAL_4/benchmark_gemini_gemini-3-pro-preview/phase2/benchmark_gemini-3-pro-preview/run_009/turn3",
        "after": PROJECTS / "gemini_images_run/FINAL_4/benchmark_gemini_gemini-3-pro-preview/phase2/benchmark_gemini-3-pro-preview/run_009/turn5",
        "before_iou": 0.6054,
        "after_iou": 0.9408,
    },
]

print("\n" + "=" * 60)
print("COLLECTING BEFORE/AFTER PAIRS")
print("=" * 60)

for ex in before_after:
    dest_dir = FIGURES / "before_after" / ex["name"]
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n{ex['label']}")

    for stage, path, iou in [("before", ex["before"], ex["before_iou"]),
                              ("after", ex["after"], ex["after_iou"])]:
        for img in ["raster.png", "overlay.png", "diff.png"]:
            src = path / img
            if src.exists():
                dst = dest_dir / f"{stage}_iou{iou:.3f}_{img}"
                shutil.copy2(src, dst)
                print(f"  ✓ {stage} ({img}, IoU={iou:.3f})")
            else:
                print(f"  ✗ {stage}/{img} NOT FOUND")

    with open(dest_dir / "summary.json", "w") as f:
        json.dump({"label": ex["label"], "before_iou": ex["before_iou"], "after_iou": ex["after_iou"]}, f, indent=2)

# ============================================================
# Also copy target device images for reference
# ============================================================

print("\n" + "=" * 60)
print("COPYING TARGET DEVICE IMAGES")
print("=" * 60)

targets = {
    "FINAL_4": PROJECTS / "gemini_images_run/FINAL_4/device_bw.png",
    "FINAL_6": PROJECTS / "gemini_images_run/FINAL_6/device_bw.png",
    "1x2_coupler": PROJECTS / "1x2_coupler/device_bw.png",
}

for name, path in targets.items():
    if path.exists():
        shutil.copy2(path, FIGURES / f"target_{name}.png")
        print(f"  ✓ {name} target image")
    else:
        print(f"  ✗ {name} target NOT FOUND")

# ============================================================
# SUMMARY STATISTICS
# ============================================================

print("\n" + "=" * 60)
print("PAPER-READY STATISTICS")
print("=" * 60)

stats = {
    "seed_diversity": {
        "experiments_analyzed": 63,
        "mean_iou_spread_best_minus_worst": 0.246,
        "mean_best_iou": 0.447,
        "mean_median_iou": 0.332,
        "mean_gain_best_over_median": 0.115,
        "pct_experiments_with_10pt_spread": 84,
        "pct_first_seed_wins": 12.7,
        "largest_spread": 0.673,
        "largest_spread_detail": "FINAL_4, Claude Opus 4.5 (best=0.804, worst=0.131)",
    },
    "turn_improvement": {
        "trajectories_analyzed": 640,
        "avg_first_turn_iou": 0.3693,
        "avg_best_turn_iou": 0.4156,
        "avg_relative_improvement": 12.5,
        "pct_seeds_improved_by_iteration": 48.0,
        "pct_peak_not_at_turn1": 65.9,
        "best_of_2_turns_avg_gain_pct": 10.0,
        "best_of_3_turns_avg_gain_pct": 16.0,
        "best_of_5_turns_avg_gain_pct": 18.3,
        "paired_t_statistic": 10.86,
        "phase2_extended_improvement_pct": 22.3,
        "phase2_seeds_improved_pct": 73.0,
    },
}

with open(FIGURES / "paper_statistics.json", "w") as f:
    json.dump(stats, f, indent=2)

print(json.dumps(stats, indent=2))
print(f"\nAll figures collected in: {FIGURES}")
print(f"Total directories created: {sum(1 for _ in FIGURES.rglob('*') if _.is_dir())}")
