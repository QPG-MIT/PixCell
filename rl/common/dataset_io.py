"""Shared loading for the frozen PixCell Parquet releases."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .contracts import TaskRecord, task_from_row


TASK_COLUMNS = (
    "id",
    "level",
    "image",
    "target_image",
    "code",
    "footprint_um",
    "representation_id",
    "leakage_group_id",
    "image_sha256",
    "target_image_sha256",
    "variation_role",
    "realization_slot",
    "split_role",
)

_CONFIGURATION_ALIASES = {
    "core": "core",
    "core-v1": "core",
    "depth": "depth",
    "depth-v1": "depth",
}


def parquet_paths(
    dataset_root: Path,
    *,
    configuration: str,
    split: str,
) -> list[Path]:
    root = dataset_root.expanduser().resolve()
    try:
        canonical = _CONFIGURATION_ALIASES[configuration]
    except KeyError as exc:
        supported = ", ".join(sorted(_CONFIGURATION_ALIASES))
        raise ValueError(
            f"unsupported configuration: {configuration}; expected one of {supported}"
        ) from exc
    if canonical == "core":
        if split != "train":
            raise ValueError("core exposes only the train split")
        paths = sorted((root / "data").glob("l*/train-*.parquet"))
    else:
        paths = sorted((root / "depth-v1" / "data").glob(f"{split}-*.parquet"))
    if not paths:
        raise FileNotFoundError(
            f"no {canonical}/{split} Parquet shards under {root}"
        )
    return paths


def load_rows(
    dataset_root: Path,
    *,
    configuration: str,
    split: str,
) -> list[dict[str, Any]]:
    """Load task fields without importing Hugging Face ``datasets``."""

    import pyarrow.parquet as pq

    rows: list[dict[str, Any]] = []
    for path in parquet_paths(
        dataset_root,
        configuration=configuration,
        split=split,
    ):
        schema_names = set(pq.read_schema(path).names)
        columns = [name for name in TASK_COLUMNS if name in schema_names]
        rows.extend(pq.read_table(path, columns=columns).to_pylist())
    return rows


def load_tasks(
    dataset_root: Path,
    *,
    configuration: str,
    split: str,
) -> list[TaskRecord]:
    return [
        task_from_row(row)
        for row in load_rows(
            dataset_root,
            configuration=configuration,
            split=split,
        )
    ]


def batches(values: Iterable[TaskRecord], batch_size: int) -> list[list[TaskRecord]]:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    items = list(values)
    return [items[index : index + batch_size] for index in range(0, len(items), batch_size)]
