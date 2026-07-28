"""Frozen dataset provenance shared by launch and promotion gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from rl.common.dataset_io import load_rows, parquet_paths

from .protocol import file_sha256


def _dataset_binding(dataset_root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    freeze_path = dataset_root / "depth-v1" / "factory" / "freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    expected = protocol["dataset"]["logical_release_sha256"]
    if freeze.get("logical_release_sha256") != expected:
        raise RuntimeError("local depth release differs from the training protocol")
    train = load_rows(dataset_root, configuration="depth", split="train")
    validation = load_rows(dataset_root, configuration="depth", split="validation")
    if (
        len(train) != protocol["dataset"]["train_rows"]
        or len(validation) != protocol["dataset"]["validation_rows"]
    ):
        raise RuntimeError("local depth row counts differ from the training protocol")
    reference_artifacts = freeze.get("reference_artifacts")
    if not isinstance(reference_artifacts, dict) or not reference_artifacts:
        raise RuntimeError("depth freeze has no reference artifact inventory")
    observed_artifacts: dict[str, str] = {}
    release_root = freeze_path.parents[1]
    for relative, expected_sha in sorted(reference_artifacts.items()):
        path = (release_root / relative).resolve(strict=True)
        if not path.is_relative_to(release_root.resolve()):
            raise RuntimeError("depth reference artifact escaped its release")
        observed = file_sha256(path)
        if observed != expected_sha:
            raise RuntimeError(f"depth reference artifact changed: {relative}")
        observed_artifacts[str(relative)] = observed
    return {
        "logical_release_sha256": expected,
        "freeze_file_sha256": file_sha256(freeze_path),
        "train_rows": len(train),
        "validation_rows": len(validation),
        "parquet_shards": {
            str(path.relative_to(dataset_root)): file_sha256(path)
            for split in ("train", "validation")
            for path in parquet_paths(
                dataset_root,
                configuration="depth",
                split=split,
            )
        },
        "reference_artifacts_sha256": hashlib.sha256(
            json.dumps(
                observed_artifacts,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest(),
        "reference_artifact_count": len(observed_artifacts),
    }
