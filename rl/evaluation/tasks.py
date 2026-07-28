"""Frozen evaluation-task selection and model/reference-safe loading."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from rl.common.contracts import (
    ModelObservation,
    VerifierReference,
    observation_from_row,
    reference_from_row,
    sampler_from_row,
)
from rl.common.dataset_io import parquet_paths


TASK_MANIFEST_SCHEMA = "pixcell-evaluation-task-manifest-v1"
OPERATING_POINT_TASK_SET = "qwen_operating_point"
BENCHMARK_TASK_SET = "f1_f8"
_SELECTION_SEED = "representation-curriculum-v1-operating-point-20260727"
_DEV_ROWS_PER_LEVEL = 8
_LEVELS = ("L0", "L1", "L2", "L3", "L4")
_DEV_COLUMNS = (
    "id",
    "level",
    "image",
    "target_image",
    "footprint_um",
    "representation_id",
    "leakage_group_id",
    "image_sha256",
    "target_image_sha256",
    "realization_slot",
    "split_role",
)


@dataclass(frozen=True)
class EvaluationTask:
    """A task with no supervised label in memory."""

    task_id: str
    level: str
    representation_id: str
    observation: ModelObservation
    reference: VerifierReference


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_depth_validation_rows(dataset_root: Path) -> list[dict[str, Any]]:
    import pyarrow.parquet as pq

    rows: list[dict[str, Any]] = []
    for path in parquet_paths(
        dataset_root,
        configuration="depth",
        split="validation",
    ):
        schema = set(pq.read_schema(path).names)
        missing = set(_DEV_COLUMNS) - schema
        if missing:
            raise ValueError(
                f"{path} is missing evaluation columns: {sorted(missing)}"
            )
        rows.extend(pq.read_table(path, columns=list(_DEV_COLUMNS)).to_pylist())
    return rows


def _row_rank(row: dict[str, Any], *, namespace: str) -> str:
    payload = (
        f"{_SELECTION_SEED}\0{namespace}\0{row['representation_id']}\0{row['id']}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _dev_manifest_entries(dataset_root: Path) -> list[dict[str, Any]]:
    rows = _read_depth_validation_rows(dataset_root)
    by_level_representation: dict[str, dict[str, list[dict[str, Any]]]] = {
        level: {} for level in _LEVELS
    }
    for row in rows:
        level = str(row["level"]).upper()
        if level not in by_level_representation:
            raise ValueError(f"unexpected validation level: {level!r}")
        by_level_representation[level].setdefault(
            str(row["representation_id"]),
            [],
        ).append(row)

    selected: list[dict[str, Any]] = []
    for level in _LEVELS:
        representations = by_level_representation[level]
        ranked_representations = sorted(
            representations,
            key=lambda value: hashlib.sha256(
                f"{_SELECTION_SEED}\0{level}\0{value}".encode()
            ).hexdigest(),
        )
        if len(ranked_representations) < _DEV_ROWS_PER_LEVEL:
            raise ValueError(
                f"{level} has only {len(ranked_representations)} representations"
            )
        for representation_id in ranked_representations[:_DEV_ROWS_PER_LEVEL]:
            row = min(
                representations[representation_id],
                key=lambda value: _row_rank(value, namespace=level),
            )
            sampler = sampler_from_row(row)
            observation = observation_from_row(row)
            reference = reference_from_row(row)
            selected.append(
                {
                    "task_id": sampler.opaque_id,
                    "source": "depth/validation",
                    "level": level,
                    "representation_id": representation_id,
                    "image_sha256": observation.image_sha256,
                    "target_image_sha256": reference.target_image_sha256,
                    "footprint_um": list(observation.footprint_um),
                }
            )
    return selected


def _benchmark_entry(repo_root: Path, index: int) -> dict[str, Any]:
    relative = Path("data") / "benchmark" / f"final_{index}"
    root = repo_root / relative
    image_path = root / "device_bw.png"
    footprint_path = root / "footprint.json"
    meta_path = root / "meta.json"
    image = image_path.read_bytes()
    footprint_doc = json.loads(footprint_path.read_text(encoding="utf-8"))
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    footprint = [float(value) for value in footprint_doc["footprint_um"]]
    digest = hashlib.sha256(image).hexdigest()
    with Image.open(image_path) as raster:
        image_size = [int(raster.width), int(raster.height)]
    return {
        "task_id": f"F{index}",
        "source": str(relative),
        "source_id": str(meta["id"]),
        "level": "BENCHMARK",
        "representation_id": f"benchmark-f{index}",
        "image_sha256": digest,
        "target_image_sha256": digest,
        "footprint_um": footprint,
        "image_size_px": image_size,
    }


def build_task_manifest(repo_root: Path) -> dict[str, Any]:
    root = repo_root.expanduser().resolve()
    manifest = {
        "schema_version": TASK_MANIFEST_SCHEMA,
        "selection": {
            "seed": _SELECTION_SEED,
            "algorithm": (
                "sha256-rank representations per level, then sha256-rank held-out "
                "realizations within each selected representation"
            ),
            "depth_validation_rows_per_level": _DEV_ROWS_PER_LEVEL,
        },
        "task_sets": {
            OPERATING_POINT_TASK_SET: _dev_manifest_entries(root / "dataset"),
            BENCHMARK_TASK_SET: [
                _benchmark_entry(root, index) for index in range(1, 9)
            ],
        },
    }
    manifest["logical_sha256"] = canonical_json_sha256(manifest)
    return manifest


def build_benchmark_task_manifest(repo_root: Path) -> dict[str, Any]:
    """Bind only the fixed repository benchmark without touching dataset rows."""

    root = repo_root.expanduser().resolve()
    manifest = {
        "schema_version": TASK_MANIFEST_SCHEMA,
        "selection": {
            "algorithm": (
                "ordered fixed repository fixtures "
                "data/benchmark/final_1 through final_8"
            ),
            "seed": None,
        },
        "task_sets": {
            BENCHMARK_TASK_SET: [
                _benchmark_entry(root, index) for index in range(1, 9)
            ],
        },
    }
    manifest["logical_sha256"] = canonical_json_sha256(manifest)
    return manifest


def load_task_manifest(path: Path, *, repo_root: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != TASK_MANIFEST_SCHEMA:
        raise ValueError("unsupported evaluation task-manifest schema")
    logical_sha = manifest.pop("logical_sha256", None)
    observed_sha = canonical_json_sha256(manifest)
    manifest["logical_sha256"] = logical_sha
    if logical_sha != observed_sha:
        raise ValueError("evaluation task-manifest logical SHA-256 mismatch")
    task_sets = set(manifest.get("task_sets", {}))
    if task_sets == {BENCHMARK_TASK_SET}:
        expected = build_benchmark_task_manifest(repo_root)
    elif task_sets == {OPERATING_POINT_TASK_SET, BENCHMARK_TASK_SET}:
        expected = build_task_manifest(repo_root)
    else:
        raise ValueError(
            f"unsupported evaluation task-set collection: {sorted(task_sets)}"
        )
    if manifest != expected:
        raise ValueError("evaluation task manifest does not match frozen sources")
    return manifest


def _task_from_depth_row(row: dict[str, Any]) -> EvaluationTask:
    sampler = sampler_from_row(row)
    return EvaluationTask(
        task_id=sampler.opaque_id,
        level=sampler.level.upper(),
        representation_id=sampler.representation_id,
        observation=observation_from_row(row),
        reference=reference_from_row(row),
    )


def _load_depth_tasks(dataset_root: Path) -> dict[str, EvaluationTask]:
    return {
        task.task_id: task
        for task in (
            _task_from_depth_row(row)
            for row in _read_depth_validation_rows(dataset_root)
        )
    }


def _load_benchmark_task(repo_root: Path, entry: dict[str, Any]) -> EvaluationTask:
    root = repo_root / entry["source"]
    image = (root / "device_bw.png").read_bytes()
    digest = hashlib.sha256(image).hexdigest()
    footprint = tuple(float(value) for value in entry["footprint_um"])
    if digest != entry["image_sha256"]:
        raise ValueError(f"{entry['task_id']} benchmark image digest changed")
    observation = ModelObservation(
        image_bytes=image,
        footprint_um=footprint,
        image_sha256=digest,
    )
    reference = VerifierReference(
        target_image_bytes=image,
        footprint_um=footprint,
        target_image_sha256=digest,
    )
    return EvaluationTask(
        task_id=str(entry["task_id"]),
        level="BENCHMARK",
        representation_id=str(entry["representation_id"]),
        observation=observation,
        reference=reference,
    )


def load_task_set(
    *,
    repo_root: Path,
    manifest: dict[str, Any],
    task_set: str,
) -> list[EvaluationTask]:
    entries = list(manifest["task_sets"].get(task_set, ()))
    if not entries:
        raise ValueError(f"unknown or empty task set: {task_set!r}")
    if task_set == OPERATING_POINT_TASK_SET:
        available = _load_depth_tasks(repo_root / "dataset")
        tasks = []
        for entry in entries:
            task = available.get(str(entry["task_id"]))
            if task is None:
                raise ValueError(f"missing depth task {entry['task_id']}")
            tasks.append(task)
    elif task_set == BENCHMARK_TASK_SET:
        tasks = [_load_benchmark_task(repo_root, entry) for entry in entries]
    else:
        raise ValueError(f"unsupported task set: {task_set!r}")

    for entry, task in zip(entries, tasks, strict=True):
        observed = {
            "task_id": task.task_id,
            "level": task.level,
            "representation_id": task.representation_id,
            "image_sha256": task.observation.image_sha256,
            "target_image_sha256": task.reference.target_image_sha256,
            "footprint_um": list(task.observation.footprint_um),
        }
        for key, value in observed.items():
            if entry.get(key) != value:
                raise ValueError(
                    f"{task.task_id} manifest mismatch for {key}: "
                    f"{entry.get(key)!r} != {value!r}"
                )
    return tasks


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--benchmark-only", action="store_true")
    return result


def main() -> None:
    args = parser().parse_args()
    document = (
        build_benchmark_task_manifest(args.repo_root)
        if args.benchmark_only
        else build_task_manifest(args.repo_root)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
