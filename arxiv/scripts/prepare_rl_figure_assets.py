#!/usr/bin/env python3
"""Freeze the compact Run B evidence used by the training figure.

The complete paid-run archive remains outside the repository. This script
reduces its five 30-step metric ledgers and six fixed-probe evaluations to the
numeric record needed by the paper. It also binds the derived record to every
source file by SHA-256. The F1--F8 benchmark and iterative deployment records
are already tracked under ``data/training/qwen-rl-v2`` and are incorporated
directly.

Run from the repository root:

    uv run python arxiv/scripts/prepare_rl_figure_assets.py \
        --run-root /path/to/runs-v2/runB-base-rl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__file__).with_name("fig_rl_assets")
TELEMETRY_PATH = ASSET_DIR / "training_telemetry.json"
MANIFEST_PATH = ASSET_DIR / "manifest.json"
EVIDENCE_DIR = REPO / "data" / "training" / "qwen-rl-v2"
LEVELS = tuple(f"L{index}" for index in range(5))
CHECKPOINTS = ("base", *(f"rl-l{index}" for index in range(5)))
STEPS_PER_LEVEL = 30
CONTENTION_L3_SHA256 = (
    "ff01225caa2aaf372a949c00c7dc113e0ba340708221970263664fa3494a5d05"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _finite_unit(value: Any, *, field: str) -> float:
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{field} must be finite and in [0, 1], got {value!r}.")
    return result


def _load_training(run_root: Path) -> tuple[list[dict[str, Any]], list[Path]]:
    records: list[dict[str, Any]] = []
    sources: list[Path] = []
    for level_index, level in enumerate(LEVELS):
        path = run_root / "stages" / f"rl-l{level_index}" / "metrics.jsonl"
        sources.append(path)
        rows = [
            json.loads(line)
            for line in path.read_text().splitlines()
            if line.strip()
        ]
        if len(rows) != STEPS_PER_LEVEL:
            raise ValueError(
                f"{path} has {len(rows)} metric rows, expected {STEPS_PER_LEVEL}."
            )
        for local_step, row in enumerate(rows, start=1):
            records.append(
                {
                    "step": level_index * STEPS_PER_LEVEL + local_step,
                    "level": level,
                    "mean_iou": _finite_unit(
                        row["env/all/iou"],
                        field=f"{level} step {local_step} mean_iou",
                    ),
                    "mean_shaped": _finite_unit(
                        row["env/all/reward/total"],
                        field=f"{level} step {local_step} mean_shaped",
                    ),
                    "executable_rate": _finite_unit(
                        row["env/all/program_valid"],
                        field=f"{level} step {local_step} executable_rate",
                    ),
                }
            )
    if [record["step"] for record in records] != list(range(1, 151)):
        raise ValueError("Run B training steps are not the expected contiguous 1--150.")
    return records, sources


def _summary_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    graded = [row for row in rows if row["shaped"] is not None]
    if not graded:
        raise ValueError("Probe contains no graded rows.")
    return {
        "n": len(rows),
        "executable_rate": sum(bool(row["executable"]) for row in rows) / len(rows),
        "mean_iou": sum(float(row["iou"]) for row in rows) / len(rows),
        "mean_shaped": sum(float(row["shaped"]) for row in graded) / len(graded),
    }


def _assert_close(actual: Any, expected: Any, *, field: str) -> None:
    if isinstance(expected, int):
        if int(actual) != expected:
            raise ValueError(f"{field}: {actual!r} != {expected!r}.")
        return
    if not math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"{field}: {actual!r} != {expected!r}.")


def _load_probes(
    run_root: Path,
    *,
    model_name: str,
    renderer_name: str,
    max_tokens: int,
) -> tuple[list[dict[str, Any]], list[Path]]:
    probes: list[dict[str, Any]] = []
    sources: list[Path] = []
    fixed_tasks: list[tuple[str, str]] | None = None
    for checkpoint_index, checkpoint in enumerate(CHECKPOINTS):
        path = run_root / "probes" / f"{checkpoint}.json"
        sources.append(path)
        report = _read_json(path)
        rows = report["rows"]
        if len(rows) != 80:
            raise ValueError(f"{path} has {len(rows)} rows, expected 80.")
        if (
            report["model_name"] != model_name
            or report["renderer_name"] != renderer_name
            or int(report["max_tokens"]) != max_tokens
            or not math.isclose(
                float(report["temperature"]),
                1.0,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            raise ValueError(f"{path} does not use the fixed probe operating point.")
        task_keys = [(row["opaque_id"], row["level"]) for row in rows]
        if len(set(task_keys)) != 80:
            raise ValueError(f"{path} contains duplicate fixed-probe tasks.")
        if fixed_tasks is None:
            fixed_tasks = task_keys
        elif task_keys != fixed_tasks:
            raise ValueError(f"{path} does not contain the same ordered 80-task probe.")
        per_level: dict[str, dict[str, Any]] = {}
        for level in LEVELS:
            level_rows = [row for row in rows if row["level"] == level]
            if len(level_rows) != 16:
                raise ValueError(
                    f"{path} has {len(level_rows)} {level} rows, expected 16."
                )
            computed = _summary_from_rows(level_rows)
            stored = report["per_level"][level]
            for field, expected in computed.items():
                _assert_close(
                    stored[field],
                    expected,
                    field=f"{checkpoint}.{level}.{field}",
                )
            per_level[level] = {
                "n": 16,
                "executable_rate": _finite_unit(
                    stored["executable_rate"],
                    field=f"{checkpoint}.{level}.executable_rate",
                ),
                "mean_iou": _finite_unit(
                    stored["mean_iou"],
                    field=f"{checkpoint}.{level}.mean_iou",
                ),
                "mean_shaped": _finite_unit(
                    stored["mean_shaped"],
                    field=f"{checkpoint}.{level}.mean_shaped",
                ),
            }
        computed_overall = _summary_from_rows(rows)
        for field, expected in computed_overall.items():
            _assert_close(
                report["overall"][field],
                expected,
                field=f"{checkpoint}.overall.{field}",
            )
        probes.append(
            {
                "checkpoint": checkpoint,
                "step": checkpoint_index * STEPS_PER_LEVEL,
                "condition": (
                    "evaluation_contention"
                    if checkpoint == "rl-l3"
                    and _sha256(path) == CONTENTION_L3_SHA256
                    else "nominal"
                ),
                "model_path": report["model_path"],
                "overall": {
                    "n": 80,
                    "executable_rate": _finite_unit(
                        report["overall"]["executable_rate"],
                        field=f"{checkpoint}.overall.executable_rate",
                    ),
                    "mean_iou": _finite_unit(
                        report["overall"]["mean_iou"],
                        field=f"{checkpoint}.overall.mean_iou",
                    ),
                    "mean_shaped": _finite_unit(
                        report["overall"]["mean_shaped"],
                        field=f"{checkpoint}.overall.mean_shaped",
                    ),
                },
                "per_level": per_level,
            }
        )
    return probes, sources


def _load_outcomes() -> tuple[dict[str, Any], list[Path]]:
    base_path = EVIDENCE_DIR / "bench" / "base-nothink.json"
    benchmark_path = EVIDENCE_DIR / "bench" / "b-final.json"
    loop_path = EVIDENCE_DIR / "agentloop" / "b-final.json"
    base = _read_json(base_path)
    benchmark = _read_json(benchmark_path)
    loop = _read_json(loop_path)
    if benchmark["model_path"] != loop["model_path"]:
        raise ValueError("Run B benchmark and iterative loop use different checkpoints.")
    if base["model_path"] is not None:
        raise ValueError("The base benchmark unexpectedly names an adapted checkpoint.")
    if (
        len(base["per_target"]) != 8
        or int(base["overall"]["total"]) != 64
        or int(base["overall"]["executable"]) != 0
    ):
        raise ValueError("The base F1--F8 benchmark is not the expected 0/64 record.")
    if (
        len(benchmark["per_target"]) != 8
        or int(benchmark["overall"]["total"]) != 64
        or len(loop["per_target"]) != 8
    ):
        raise ValueError("The Run B evaluation records do not cover eight targets.")

    per_target = loop["per_target"]
    round_count = int(loop["rounds"])
    round_means = []
    for round_index in range(round_count + 1):
        values = [
            float(target["rounds"][round_index]["champion_iou"])
            for target in per_target.values()
        ]
        round_means.append(
            {
                "round": round_index,
                "mean_champion_iou": sum(values) / len(values),
            }
        )
    _assert_close(
        round_means[-1]["mean_champion_iou"],
        loop["overall_mean_champion"],
        field="agent_loop.overall_mean_champion",
    )
    return (
        {
            "model_path": benchmark["model_path"],
            "base_single_pass": base["overall"],
            "single_pass": benchmark["overall"],
            "iterative": {
                "initial_attempts": int(loop["init_attempts"]),
                "revision_rounds": round_count,
                "revisions_per_round": int(loop["revisions_per_round"]),
                "round_means": round_means,
                "final_mean_champion_iou": float(loop["overall_mean_champion"]),
            },
        },
        [base_path, benchmark_path, loop_path],
    )


def _source_entry(path: Path, root: Path) -> dict[str, str]:
    return {
        "path": str(path.relative_to(root)),
        "sha256": _sha256(path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-root",
        type=Path,
        required=True,
        help="Path to the external runs-v2/runB-base-rl evidence directory.",
    )
    arguments = parser.parse_args()
    run_root = arguments.run_root.resolve()
    plan_path = run_root / "provenance" / "plan.json"
    plan = _read_json(plan_path)
    run_plan = plan["plan"]
    if (
        run_plan["key"] != "B"
        or run_plan["name"] != "runB-base-rl"
        or run_plan["steps_per_level"] != STEPS_PER_LEVEL
        or run_plan["sft"]
    ):
        raise ValueError("The supplied run root is not the completed raw-base Run B.")

    training, training_sources = _load_training(run_root)
    probes, probe_sources = _load_probes(
        run_root,
        model_name=plan["model_name"],
        renderer_name=run_plan["renderer_name"],
        max_tokens=int(run_plan["max_tokens"]),
    )
    outcomes, outcome_sources = _load_outcomes()
    if probes[-1]["model_path"] != outcomes["model_path"]:
        raise ValueError("Final probe and released-model outcomes use different checkpoints.")

    telemetry = {
        "run": {
            "key": "B",
            "name": "runB-base-rl",
            "model_name": plan["model_name"],
            "renderer_name": run_plan["renderer_name"],
            "max_tokens": int(run_plan["max_tokens"]),
            "lora_rank": 32,
            "steps_per_level": STEPS_PER_LEVEL,
            "total_steps": 150,
            "source_git_head": plan["git_head"],
            "source_git_dirty": bool(plan["git_dirty"]),
        },
        "levels": list(LEVELS),
        "training": training,
        "probes": probes,
        "outcomes": outcomes,
    }
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(TELEMETRY_PATH, telemetry)

    run_sources = [plan_path, *training_sources, *probe_sources]
    manifest = {
        "record": "runs-v2/runB-base-rl",
        "run_sources": [
            _source_entry(path, run_root)
            for path in run_sources
        ],
        "repository_sources": [
            _source_entry(path, REPO)
            for path in outcome_sources
        ],
        "assets": {
            TELEMETRY_PATH.name: {
                "sha256": _sha256(TELEMETRY_PATH),
            }
        },
    }
    _write_json(MANIFEST_PATH, manifest)
    print(f"wrote {TELEMETRY_PATH}")
    print(f"wrote {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
