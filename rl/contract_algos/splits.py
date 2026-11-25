"""Create a reproducible group-held-out view without modifying the release."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from rl.common.contracts import TaskRecord
from rl.common.dataset_io import load_tasks, parquet_paths
from rl.common.prompt import CONTRACT_VERSION, prompt_asset_hashes


DATASET_ROOT = Path(__file__).resolve().parents[2] / "dataset"
SPLITS = ("train", "validation", "test")


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def file_digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def load_release(dataset_root: Path) -> list[TaskRecord]:
    return [
        task
        for split in ("train", "validation")
        for task in load_tasks(dataset_root, configuration="depth", split=split)
    ]


def release_fingerprints(dataset_root: Path) -> dict[str, str]:
    files = [
        path
        for split in ("train", "validation")
        for path in parquet_paths(dataset_root, configuration="depth", split=split)
    ]
    observed = {
        str(path.relative_to(dataset_root.resolve())): file_digest(path)
        for path in files
    }
    freeze = json.loads(
        (dataset_root / "depth-v1/factory/freeze.json").read_text()
    )
    for relative, checksum in observed.items():
        expected = freeze["reference_artifacts"].get(relative.removeprefix("depth-v1/"))
        if checksum != expected:
            raise ValueError(f"frozen dataset shard mismatch: {relative}")
    return observed


def partition_rows(tasks: list[TaskRecord], *, seed: int) -> list[dict]:
    """Co-locate leakage groups and transitively identical raster payloads.

    Hash assignment is 70/15/15 in expectation, not a row-count promise.
    Identical images are merged even at different footprints: conservative
    exclusion is preferable to inadvertent visual memorization.
    """
    parent: dict[str, str] = {}
    seen_images: dict[str, str] = {}
    seen_targets: dict[str, str] = {}
    seen_tasks: set[str] = set()

    def find(group: str) -> str:
        parent.setdefault(group, group)
        if parent[group] != group:
            parent[group] = find(parent[group])
        return parent[group]

    def merge(left: str, right: str) -> None:
        roots = sorted((find(left), find(right)))
        parent[roots[1]] = roots[0]

    for task in sorted(tasks, key=lambda item: item.sampler.opaque_id):
        group = task.sampler.leakage_group_id
        task_id = task.sampler.opaque_id
        if not group:
            raise ValueError(f"missing leakage group: {task_id}")
        if task_id in seen_tasks:
            raise ValueError(f"duplicate task ID: {task_id}")
        seen_tasks.add(task_id)
        find(group)
        for index, checksum in (
            (seen_images, task.observation.image_sha256),
            (seen_targets, task.reference.target_image_sha256),
        ):
            if checksum in index:
                merge(group, index[checksum])
            else:
                index[checksum] = group

    members: dict[str, list[str]] = defaultdict(list)
    for group in sorted(parent):
        members[find(group)].append(group)
    component_ids = {root: digest(groups) for root, groups in members.items()}
    rows = []
    for task in sorted(tasks, key=lambda item: item.sampler.opaque_id):
        component_id = component_ids[find(task.sampler.leakage_group_id)]
        value = int(digest([seed, component_id]), 16) / 2**256
        split = "train" if value < 0.7 else "validation" if value < 0.85 else "test"
        rows.append({
            "task_id": task.sampler.opaque_id,
            "split": split,
            "level": task.sampler.level,
            "release_split": task.sampler.split_role,
            "representation_id": task.sampler.representation_id,
            "leakage_group_id": task.sampler.leakage_group_id,
            "component_id": component_id,
            "image_sha256": task.observation.image_sha256,
            "target_image_sha256": task.reference.target_image_sha256,
            "code_sha256": hashlib.sha256(task.label.encode()).hexdigest(),
        })
    return rows


def build_manifest(tasks: list[TaskRecord], dataset_root: Path, *, seed: int = 17) -> dict:
    rows = partition_rows(tasks, seed=seed)
    counts = {
        split: dict(Counter(row["level"] for row in rows if row["split"] == split))
        for split in SPLITS
    }
    if any(not counts[split] for split in SPLITS):
        raise ValueError("empty partition; review group population before training")
    manifest = {
        "schema_version": "pixcell-contract-splits-v1",
        "seed": seed,
        "assignment": "sha256(seed, raster-linked leakage component); 70/15/15 thresholds",
        "limits": [
            "Existing depth validation shares representation families with its train split.",
            "This manifest repartitions BOTH released splits; old trained checkpoints may have seen held-out rows.",
            "Group exclusion covers declared leakage groups and identical raster bytes, not all semantic similarities.",
            "Use a fresh base checkpoint; reserve test for final evaluation, never reward selection.",
        ],
        "prompt_contract": CONTRACT_VERSION,
        "prompt_assets": prompt_asset_hashes(),
        "dataset_shards": release_fingerprints(dataset_root),
        "counts_by_split_level": counts,
        "leakage_group_count": len({row["leakage_group_id"] for row in rows}),
        "component_count": len({row["component_id"] for row in rows}),
        "rows": rows,
    }
    manifest["manifest_sha256"] = digest(manifest)
    return manifest


def verify_manifest(manifest: dict, dataset_root: Path) -> None:
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if digest(body) != manifest.get("manifest_sha256"):
        raise ValueError("split manifest digest mismatch")
    if manifest.get("schema_version") != "pixcell-contract-splits-v1":
        raise ValueError("unsupported split manifest")
    if manifest["dataset_shards"] != release_fingerprints(dataset_root):
        raise ValueError("dataset differs from the split manifest")
    if manifest["prompt_contract"] != CONTRACT_VERSION or manifest["prompt_assets"] != prompt_asset_hashes():
        raise ValueError("prompt differs from the split manifest")
    for key in ("leakage_group_id", "component_id", "image_sha256", "target_image_sha256"):
        locations: dict[str, str] = {}
        for row in manifest["rows"]:
            previous = locations.setdefault(row[key], row["split"])
            if previous != row["split"]:
                raise ValueError(f"cross-partition leakage: {key}")


def write_new_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=DATASET_ROOT)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_manifest(load_release(args.dataset_root), args.dataset_root, seed=args.seed)
    write_new_json(args.out, manifest)
    print(json.dumps({"manifest_sha256": manifest["manifest_sha256"], "counts": manifest["counts_by_split_level"]}))


if __name__ == "__main__":
    main()
