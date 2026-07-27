from __future__ import annotations

from pathlib import Path

import pytest

from rl.common.dataset_io import parquet_paths


def test_generic_and_v1_configuration_aliases_resolve_identically():
    dataset_root = Path(__file__).resolve().parents[3] / "dataset"
    assert parquet_paths(
        dataset_root,
        configuration="core",
        split="train",
    ) == parquet_paths(
        dataset_root,
        configuration="core-v1",
        split="train",
    )
    assert parquet_paths(
        dataset_root,
        configuration="depth",
        split="validation",
    ) == parquet_paths(
        dataset_root,
        configuration="depth-v1",
        split="validation",
    )


def test_core_aliases_expose_only_train():
    dataset_root = Path(__file__).resolve().parents[3] / "dataset"
    for configuration in ("core", "core-v1"):
        with pytest.raises(ValueError, match="core exposes only the train split"):
            parquet_paths(
                dataset_root,
                configuration=configuration,
                split="validation",
            )
