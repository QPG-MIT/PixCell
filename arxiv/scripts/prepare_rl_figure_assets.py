#!/usr/bin/env python3
"""Freeze the compact evidence used by Figures 12 and 13.

The complete RL ledger and executable benchmark archive live in the companion
PixCell working repository.  This script reduces those records to the numeric
series and raster pairs required by the paper, records the source commit and
input hashes, and writes a hash manifest beside the derived assets.

Run from the paper repository root:

    python arxiv/scripts/prepare_rl_figure_assets.py \
        --source-repo ../PixCell-running
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image


REPO = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__file__).with_name("fig_rl_assets")
LINEAGE = (
    (
        "L0--L3",
        "pixcell-Qwen-Qwen3.6-35B-A3B-8g-8b-lr1e-05-20260708-0953",
        0,
    ),
    (
        "13-figure L4",
        "pixcell-Qwen-Qwen3.6-35B-A3B-8g-8b-lr1e-05-20260708-1043",
        30,
    ),
    (
        "18-figure L4",
        "pixcell-Qwen-Qwen3.6-35B-A3B-8g-8b-lr1e-05-20260708-1209",
        65,
    ),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _git_commit(source_repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(source_repo), "rev-parse", "HEAD"],
        text=True,
    ).strip()


def _load_training(source_repo: Path) -> tuple[dict, list[Path]]:
    evaluations = []
    training = []
    source_paths = []
    for stage, run_directory, offset in LINEAGE:
        metrics_path = (
            source_repo
            / "rl"
            / "reports"
            / "runs_ledger"
            / run_directory
            / "metrics.jsonl"
        )
        source_paths.append(metrics_path)
        for line in metrics_path.read_text().splitlines():
            record = json.loads(line)
            step = record.get("step")
            if step is None:
                continue
            absolute_step = offset + int(step)
            if record.get("env/L4/iou") is not None:
                training.append(
                    {
                        "step": absolute_step,
                        "iou": float(record["env/L4/iou"]),
                    }
                )
            if "test/env/all/iou" in record:
                benchmark_values = [
                    record.get(f"test/env/final_{index}/iou")
                    for index in range(1, 9)
                ]
                benchmark_values = [
                    float(value) for value in benchmark_values if value is not None
                ]
                evaluations.append(
                    {
                        "step": absolute_step,
                        "benchmark": (
                            float(np.mean(benchmark_values))
                            if benchmark_values
                            else None
                        ),
                        **{
                            f"L{index}": (
                                float(record[f"test/env/L{index}/iou"])
                                if record.get(f"test/env/L{index}/iou") is not None
                                else None
                            )
                            for index in range(4)
                        },
                    }
                )

    # The first record at a stage seam repeats the preceding checkpoint.
    deduplicated = {}
    for record in sorted(evaluations, key=lambda item: item["step"]):
        deduplicated.setdefault(record["step"], record)

    first_draw_path = (
        source_repo / "rl" / "reports" / "benchmark_eval_bridge2.json"
    )
    source_paths.append(first_draw_path)
    first_draw = json.loads(first_draw_path.read_text())

    return (
        {
            "stages": [
                {"label": label, "start_step": offset}
                for label, _run_directory, offset in LINEAGE
            ],
            "evaluations": list(deduplicated.values()),
            "training": sorted(training, key=lambda item: item["step"]),
            "final_draw": {
                "eval_at_1": float(first_draw["bench_mean_of_means"]),
                "best_at_8": float(first_draw["bench_mean_of_bests"]),
            },
        },
        source_paths,
    )


def _mask(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("L")) < 128


def _load_gallery(source_repo: Path) -> tuple[dict, list[Path]]:
    reports = source_repo / "rl" / "reports"
    attempts_path = reports / "benchmark_attempts_bridge2.jsonl"
    attempts = [
        json.loads(line)
        for line in attempts_path.read_text().splitlines()
        if line.strip()
    ]
    best = {}
    grouped = {}
    for attempt in attempts:
        figure = attempt["figure"]
        grouped.setdefault(figure, []).append(attempt)
        if figure not in best or attempt["iou"] > best[figure]["iou"]:
            best[figure] = attempt

    old_cwd = Path.cwd()
    sys.path.insert(0, str(reports))
    sys.path.insert(0, str(source_repo / "src"))
    os.chdir(source_repo)
    try:
        from make_gallery import render_code

        rows = []
        source_paths = [attempts_path]
        for figure in sorted(best):
            attempt = best[figure]
            number = int(figure.removeprefix("final_"))
            sample_directory = source_repo / attempt["sample_dir"]
            target_source = sample_directory / "device_bw.png"
            calibration_source = sample_directory / "calibration.json"
            source_paths.extend((target_source, calibration_source))

            target = Image.open(target_source).convert("L")
            render = render_code(attempt["code"], attempt["sample_dir"])
            if render is None:
                raise RuntimeError(f"Best archived attempt for {figure} did not render.")
            render = render.convert("L")
            if target.size != render.size:
                raise ValueError(
                    f"Target/render dimensions differ for {figure}: "
                    f"{target.size} versus {render.size}."
                )

            target_mask = _mask(target)
            render_mask = _mask(render)
            union = np.logical_or(target_mask, render_mask).sum()
            measured_iou = float(
                np.logical_and(target_mask, render_mask).sum() / union
            )
            # The archived IoU is stored at two to four decimals, while this
            # qualitative gallery threshold-binarizes antialiased rasters at
            # mid-gray.  Guard against a mismatched winner without pretending
            # that the display composite is the scoring raster itself.
            if not np.isclose(measured_iou, float(attempt["iou"]), atol=5.0e-2):
                raise ValueError(
                    f"Re-rendered IoU {measured_iou:.6f} does not reconcile "
                    f"with archived IoU {attempt['iou']:.6f} for {figure}."
                )

            target_name = f"F{number}_target.png"
            render_name = f"F{number}_render.png"
            target_binary = Image.fromarray(
                np.where(target_mask, 0, 255).astype(np.uint8),
                mode="L",
            )
            render_binary = Image.fromarray(
                np.where(render_mask, 0, 255).astype(np.uint8),
                mode="L",
            )
            target_binary.save(ASSET_DIR / target_name, optimize=True)
            render_binary.save(ASSET_DIR / render_name, optimize=True)
            rows.append(
                {
                    "device": f"F{number}",
                    "best_iou": float(attempt["iou"]),
                    "eval_at_1": float(
                        np.mean(
                            [
                                float(candidate["iou"])
                                for candidate in grouped[figure]
                            ]
                        )
                    ),
                    "executable": sum(
                        bool(candidate.get("gds_ok"))
                        for candidate in grouped[figure]
                    ),
                    "attempts": len(grouped[figure]),
                    "target": target_name,
                    "render": render_name,
                }
            )
    finally:
        os.chdir(old_cwd)

    return {"devices": rows}, source_paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-repo",
        type=Path,
        default=REPO.parent / "PixCell-running",
    )
    arguments = parser.parse_args()
    source_repo = arguments.source_repo.resolve()
    if not (source_repo / "rl" / "reports").is_dir():
        raise FileNotFoundError(
            f"RL evidence directory not found under {source_repo}."
        )

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    training, training_sources = _load_training(source_repo)
    gallery, gallery_sources = _load_gallery(source_repo)
    training_path = ASSET_DIR / "training_telemetry.json"
    gallery_path = ASSET_DIR / "gallery.json"
    _write_json(training_path, training)
    _write_json(gallery_path, gallery)

    derived_paths = [training_path, gallery_path]
    for row in gallery["devices"]:
        derived_paths.extend(
            (ASSET_DIR / row["target"], ASSET_DIR / row["render"])
        )
    source_paths = list(dict.fromkeys(training_sources + gallery_sources))
    manifest = {
        "source_repository": "QPG-MIT/PixCell-running",
        "source_commit": _git_commit(source_repo),
        "runtime": {
            "python": f"{sys.version_info.major}.{sys.version_info.minor}",
            "gdsfactory": importlib.metadata.version("gdsfactory"),
        },
        "source_files": [
            {
                "path": str(path.relative_to(source_repo)),
                "sha256": _sha256(path),
            }
            for path in source_paths
        ],
        "assets": {
            str(path.relative_to(ASSET_DIR)): {"sha256": _sha256(path)}
            for path in derived_paths
        },
    }
    _write_json(ASSET_DIR / "manifest.json", manifest)
    print(f"wrote {ASSET_DIR / 'manifest.json'}")


if __name__ == "__main__":
    main()
