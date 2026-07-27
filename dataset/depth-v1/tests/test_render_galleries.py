"""Focused tests for depth-v1 gallery coverage schedules."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from render_galleries import _state_rows  # noqa: E402
from render_review_pack import _validate_output_path  # noqa: E402
from schema import ANCHOR_ONLY_PARENT_IDS, GEOMETRY_STATE_COUNT  # noqa: E402


ANCHOR_ONLY_ID = next(iter(ANCHOR_ONLY_PARENT_IDS))
COMPLETE_ID = "l4_complete_test_representation"


def _row(parent_id: str, slot: int) -> dict[str, object]:
    return {
        "grammar_id": parent_id,
        "parent_core_id": parent_id,
        "realization_slot": slot,
    }


def _valid_rows() -> list[dict[str, object]]:
    return [
        _row(ANCHOR_ONLY_ID, 0),
        *(_row(COMPLETE_ID, slot) for slot in range(GEOMETRY_STATE_COUNT)),
    ]


def test_gallery_schedule_keeps_anchor_only_representation_in_overview() -> None:
    grouped = _state_rows(_valid_rows())
    assert set(grouped[ANCHOR_ONLY_ID]) == {0}
    assert set(grouped[COMPLETE_ID]) == set(range(GEOMETRY_STATE_COUNT))


def test_gallery_schedule_rejects_descendant_for_anchor_only_representation() -> None:
    rows = [*_valid_rows(), _row(ANCHOR_ONLY_ID, 1)]
    with pytest.raises(ValueError, match="invalid gallery state schedule"):
        _state_rows(rows)


def test_gallery_schedule_rejects_incomplete_depth_progression() -> None:
    rows = [
        row
        for row in _valid_rows()
        if not (
            row["parent_core_id"] == COMPLETE_ID
            and row["realization_slot"] == GEOMETRY_STATE_COUNT - 1
        )
    ]
    with pytest.raises(ValueError, match="invalid gallery state schedule"):
        _state_rows(rows)


def test_review_pack_rejects_release_root_and_in_tree_aliases(
    tmp_path: Path,
) -> None:
    worktree = (tmp_path / "PixCell").resolve()
    root = worktree / "dataset" / "depth-v1"
    _validate_output_path(root, (tmp_path / "review").resolve())

    for unsafe in (
        worktree,
        worktree.parent,
        root,
        root.parent,
        root / "data" / "review",
        worktree / "dataset" / "data",
        worktree / "dataset" / "metadata",
    ):
        with pytest.raises(ValueError, match="outside the PixCell worktree"):
            _validate_output_path(root, unsafe)
