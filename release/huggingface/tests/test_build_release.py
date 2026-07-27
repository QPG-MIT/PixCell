from __future__ import annotations

import json
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from release.huggingface.build_release import (
    CALIBRATION_COLUMNS,
    CORE_ROW_COUNT,
    FORBIDDEN_MODEL_COLUMNS,
    MAX_ROWS_PER_SHARD,
    MODEL_COLUMNS,
    REFERENCE_COLUMNS,
    ReleaseBuildError,
    assert_core_ordered_subset,
    assert_frozen_sources,
    depth_source_paths,
    opaque_id,
    project_model_row,
    project_reference_row,
    shard_plan,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET_ROOT = REPO_ROOT / "dataset"


def _first_depth_row() -> dict:
    path = depth_source_paths(DATASET_ROOT, "train")[0]
    return pq.read_table(path).slice(0, 1).to_pylist()[0]


def _row_with_slot(slot: int) -> dict:
    for path in depth_source_paths(DATASET_ROOT, "train"):
        for row in pq.read_table(path).to_pylist():
            if row["realization_slot"] == slot:
                return row
    raise AssertionError(f"no depth row with realization_slot={slot}")


def test_model_projection_is_generic_and_has_no_reference_payload():
    source = _first_depth_row()
    projected = project_model_row(source)
    assert tuple(projected) == MODEL_COLUMNS
    assert projected["opaque_id"] == opaque_id(source["id"])
    assert projected["is_core"] is True
    assert not FORBIDDEN_MODEL_COLUMNS.intersection(projected)
    assert "instruction" not in projected
    assert "target_image" not in projected
    assert "calibration_json" not in projected


def test_is_core_marks_all_core_members_but_not_depth_descendants():
    assert project_model_row(_row_with_slot(-1))["is_core"] is True
    assert project_model_row(_row_with_slot(0))["is_core"] is True
    assert project_model_row(_row_with_slot(1))["is_core"] is False


def test_reference_projection_has_trimmed_calibration_and_lineage():
    source = _first_depth_row()
    projected = project_reference_row(source)
    assert tuple(projected) == REFERENCE_COLUMNS
    assert "image" not in projected
    assert "code" not in projected
    assert projected["parent_opaque_id"] == opaque_id(source["parent_core_id"])
    calibration = json.loads(projected["calibration_json"])
    assert tuple(sorted(calibration)) == tuple(sorted(CALIBRATION_COLUMNS))
    assert calibration["footprint_um"] == source["footprint_um"]


def test_descendant_reference_derives_calibration_from_target_raster():
    source = _row_with_slot(1)
    metadata = json.loads(source["metadata_json"])
    assert "calibration" not in metadata
    calibration = json.loads(project_reference_row(source)["calibration_json"])
    assert set(calibration) == set(CALIBRATION_COLUMNS)
    assert calibration["footprint_um"] == source["footprint_um"]
    assert all(value > 0 for value in calibration["scale_px_per_um"])


def test_shard_plan_is_bounded_and_complete():
    plan = shard_plan(3468)
    assert plan[0] == (0, MAX_ROWS_PER_SHARD)
    assert plan[-1][1] == 3468
    assert all(0 < stop - start <= MAX_ROWS_PER_SHARD for start, stop in plan)
    assert len(plan) == 7


def test_core_ordered_subset_rejects_reordering():
    core = [{"id": f"row-{index}", **{field: None for field in ()}} for index in range(CORE_ROW_COUNT)]
    # The order check happens before the complete frozen-field comparison.
    depth = list(reversed(core))
    with pytest.raises(ReleaseBuildError, match="order-preserving"):
        assert_core_ordered_subset(core, depth)


def test_frozen_source_artifacts_are_bound():
    assert_frozen_sources(DATASET_ROOT)
