"""Contract tests that do not execute or render dataset programs."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pyarrow.parquet as pq


DEPTH_ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = DEPTH_ROOT.parent
MODULE_PATH = DEPTH_ROOT / "scripts" / "contracts.py"

SPEC = importlib.util.spec_from_file_location("pixcell_depth_contracts", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
contracts = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = contracts
SPEC.loader.exec_module(contracts)


def _semantic_rows() -> list[dict]:
    columns = [
        "id",
        "grammar_id",
        "variation_role",
        "code",
        "parameters_json",
        "footprint_um",
    ]
    rows: list[dict] = []
    for level in ("l0", "l1", "l2", "l3", "l4"):
        path = DATASET_ROOT / "data" / level / "train-00000-of-00001.parquet"
        rows.extend(
            row
            for row in pq.read_table(path, columns=columns).to_pylist()
            if row["variation_role"] == "semantic"
        )
    return rows


def test_rewrite_changes_only_named_top_level_literals() -> None:
    code = """\
import gdsfactory as gf

width_um = 2.0
count = 4
layer = (1, 0)

def device():
    anonymous_width = 9.0
    return gf.components.rectangle(size=(width_um, anonymous_width), layer=layer)
"""
    rewritten = contracts.rewrite_parameters(code, {"width_um": 2.5})
    proof = contracts.prove_literal_rewrite(code, rewritten, {"width_um": 2.5})
    assert proof["changed_names"] == ["width_um"]
    assert proof["grammar_preserved"] is True
    assert "anonymous_width = 9.0" in rewritten


def test_one_axis_schedule_uses_bounded_fallbacks() -> None:
    row = {
        "id": "one-axis",
        "grammar_id": "one-axis",
        "variation_role": "semantic",
        "parameters_json": '{"parameters":{"width_um":2.0}}',
        "footprint_um": [20.0, 2.0],
    }
    contract = contracts.classify_parameters(
        "width_um = 2.0\nlayer = (1, 0)\n", row
    )
    specs = contracts.candidate_specs(contract)
    assert [spec.slot for spec in specs] == [
        "r01",
        "r02",
        "r03",
        "r04",
        "r05",
        "r06",
        "r07",
    ]
    assert len({tuple(spec.updates) for spec in specs}) == 7
    assert specs[2].fallback is True
    assert specs[4].fallback is True


def test_every_core_representation_has_a_proven_schedule() -> None:
    report = contracts.audit_contracts(_semantic_rows())
    assert report["semantic_anchors"] == 547
    assert report["schedulable_anchors"] == 547
    assert report["coverage"] == 1.0
    assert report["rewrite_proofs"] == 547 * 7
    assert report["unschedulable_anchors"] == []
    assert report["parameter_class_histogram"]["realization_repeat_count"] == 6
    assert report["effective_candidates"] == 547 * 7 - 2
    assert report["no_effect_specs"] == [
        {
            "id": "l2_17_composite_cell_2d_array__s03__proposal_a",
            "slot": "r03",
        }
    ]
    assert report["duplicate_specs"] == [
        {
            "id": "l2_17_composite_cell_2d_array__s03__proposal_a",
            "slot": "r05",
            "duplicates_slot": "r01",
        }
    ]


def test_portless_array_counts_are_integer_and_structurally_declared() -> None:
    rows = {
        row["grammar_id"]: row
        for row in _semantic_rows()
        if row["grammar_id"]
        in {
            "l2_17_composite_cell_2d_array__s01",
            "l2_17_composite_cell_2d_array__s02",
            "l2_17_composite_cell_2d_array__s03",
        }
    }
    assert len(rows) == 3
    for row in rows.values():
        contract = contracts.classify_parameters(row["code"], row)
        count_names = {
            parameter.name
            for parameter in contract.assignments
            if parameter.parameter_class
            == contracts.ParameterClass.REPEAT_COUNT.value
        }
        assert count_names == {"rows", "columns"}
        for candidate in contracts.candidate_specs(contract):
            updates = dict(candidate.updates)
            deltas = dict(candidate.structural_count_deltas)
            for name in count_names & updates.keys():
                assert isinstance(updates[name], int)
                assert updates[name] >= 2
                assert deltas[name] in {-1, 0, 1}
