"""Focused corruption tests for the depth-v1 release validator."""

from __future__ import annotations

import hashlib
import io
import json
import sys
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
CORE_SCRIPTS = ROOT.parent / "scripts"
sys.path.insert(0, str(CORE_SCRIPTS))
sys.path.insert(0, str(SCRIPTS))

from _shared import normalized_d4_sha256, primitive_calls, sha256_bytes  # noqa: E402
from contracts import normalized_grammar_hash, rewrite_parameters  # noqa: E402
from runtime import PortGateReport, PortWitness  # noqa: E402
from schema import (  # noqa: E402
    CORE_SCHEMA_VERSION,
    DEPTH_ROW_COLUMNS,
    DEPTH_SCHEMA_VERSION,
    FROZEN_LOGICAL_RELEASE_SHA256,
    bind_logical_row_sha256,
    canonical_json,
    depth_features,
)
from validate import (  # noqa: E402
    DepthValidationError,
    _changes_repeat_count,
    _reject_control_keys,
    _runtime_port_signature,
    _validate_arrow_schema,
    _validate_controlled_relationship,
    _validate_frozen_logical_release,
    _validate_parameter_payload,
    _validate_repeated_element_counts,
    _validate_runtime_port_evidence,
    _validate_row_static,
)


ANCHOR_CODE = """\
import gdsfactory as gf

length_um = 10.0
width_um = 1.0
layer = (1, 0)

@gf.cell
def device():
    return gf.components.rectangle(size=(length_um, width_um), layer=layer)
"""


def _png() -> tuple[bytes, Image.Image]:
    image = Image.new("L", (32, 32), 255)
    ImageDraw.Draw(image).rectangle((4, 12, 27, 19), fill=0)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue(), image


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _row(code: str = ANCHOR_CODE) -> dict:
    image_bytes, image = _png()
    code_hash = sha256_bytes(code.encode("utf-8"))
    values = {
        "fixed_context": {"layer": [1, 0]},
        "parameters": {
            "length_um": 10.0,
            "width_um": 1.0,
        },
    }
    row = {
        "schema_version": CORE_SCHEMA_VERSION,
        "id": "l0_rectangle__s01",
        "level": "L0",
        "curriculum_order": 0,
        "image": {"bytes": image_bytes, "path": "image.png"},
        "target_image": {"bytes": image_bytes, "path": "target.png"},
        "code": code,
        "code_language": "python",
        "instruction": "Recreate the shown geometry.",
        "label": "rectangle",
        "family": "primitive",
        "concept_id": "rectangle",
        "representation_id": "rectangle",
        "grammar_id": "l0_rectangle__s01",
        "leakage_group_id": "rectangle",
        "variation_role": "semantic",
        "primitive_calls": primitive_calls(code),
        "prerequisite_ids": [],
        "port_signature_json": '{"count":0,"names":[],"ports":[]}',
        "footprint_um": [10.0, 1.0],
        "parameters_json": canonical_json(values),
        "topology_json": "{}",
        "metadata_json": "{}",
        "image_sha256": sha256_bytes(image_bytes),
        "target_image_sha256": sha256_bytes(image_bytes),
        "code_sha256": code_hash,
        "normalized_d4_sha256": normalized_d4_sha256(image),
        "view_policy": "maximum_visibility",
        "source_dataset_digest_sha256": "c" * 64,
        "source_generator_version": "core-v1",
        "depth_schema_version": DEPTH_SCHEMA_VERSION,
        "parent_core_id": "l0_rectangle__s01",
        "parent_code_sha256": code_hash,
        "parent_core_digest_sha256": "c" * 64,
        "geometry_id": "dgeo_test",
        "realization_id": "r00",
        "realization_slot": 0,
        "transform_kind": "anchor",
        "controlled_axes": [],
        "parameter_delta_json": "{}",
        "dependency_group": "ddep_test",
        "split_role": "train",
        "pose_id": "canonical",
        "render_id": "maximum_visibility",
        "verification_evidence_json": "{}",
        "depth_generator_version": "depth-test-v1",
        "logical_row_sha256": "",
    }
    self_ordered = {column: row[column] for column in DEPTH_ROW_COLUMNS}
    return bind_logical_row_sha256(self_ordered)


class DepthValidatorTests(unittest.TestCase):
    def test_static_row_checks_code_images_and_parameters(self) -> None:
        _validate_row_static(_row())

    def test_frozen_logical_release_rejects_manifest_and_row_drift(self) -> None:
        row = _row()
        with self.assertRaisesRegex(
            DepthValidationError,
            "manifest logical release digest",
        ):
            _validate_frozen_logical_release(
                {"logical_release_sha256": "0" * 64},
                [row],
            )
        with self.assertRaisesRegex(
            DepthValidationError,
            "recomputed logical release digest",
        ):
            _validate_frozen_logical_release(
                {
                    "logical_release_sha256": FROZEN_LOGICAL_RELEASE_SHA256,
                },
                [row],
            )

    def test_arrow_schema_requires_exact_hugging_face_metadata(self) -> None:
        expected = depth_features().arrow_schema
        _validate_arrow_schema("data/train.parquet", expected, expected)
        with self.assertRaisesRegex(
            DepthValidationError,
            "Hugging Face feature metadata",
        ):
            _validate_arrow_schema(
                "data/train.parquet",
                expected.remove_metadata(),
                expected,
            )

    def test_public_control_keys_are_rejected_recursively(self) -> None:
        with self.assertRaisesRegex(DepthValidationError, "forbidden public"):
            _reject_control_keys(
                {"nested": [{"review_status": "accepted"}]},
                label="evidence",
            )

    def test_legacy_core_control_keys_remain_valid_outside_new_evidence(self) -> None:
        row = _row()
        row["metadata_json"] = '{"legacy_status":"accepted"}'
        row["topology_json"] = '{"admission_status":"historical"}'
        _validate_row_static(row)

        row["verification_evidence_json"] = '{"review_status":"accepted"}'
        with self.assertRaisesRegex(DepthValidationError, "forbidden public"):
            _validate_row_static(row)

    def test_controlled_delta_and_normalized_grammar_are_bound(self) -> None:
        anchor = _row()
        candidate_code = rewrite_parameters(ANCHOR_CODE, {"length_um": 12.0})
        candidate = dict(anchor)
        candidate.update(
            {
                "id": "l0_rectangle__s01__depth_r01",
                "code": candidate_code,
                "code_sha256": sha256_bytes(candidate_code.encode("utf-8")),
                "controlled_axes": ["length_um"],
                "parameters_json": canonical_json(
                    {
                        "fixed_context": {"layer": [1, 0]},
                        "parameters": {
                            "length_um": 12.0,
                            "width_um": 1.0,
                        },
                    }
                ),
                "realization_id": "r01",
                "realization_slot": 1,
            }
        )
        delta = {
            "changes": {
                "length_um": {
                    "after": 12.0,
                    "before": 10.0,
                }
            },
            "derived_updates": [],
        }
        evidence = {
            "model_input_signal": {
                "footprint_changed": True,
                "normalized_changed_fraction": None,
            },
            "normalized_grammar_hash": normalized_grammar_hash(ANCHOR_CODE),
        }
        _validate_controlled_relationship(
            candidate,
            anchor,
            parsed_delta=delta,
            evidence=evidence,
        )

        changed_grammar = dict(candidate)
        changed_grammar["code"] = candidate_code.replace(
            "layer=layer",
            "layer=(2, 0)",
        )
        with self.assertRaisesRegex(DepthValidationError, "source grammar"):
            _validate_controlled_relationship(
                changed_grammar,
                anchor,
                parsed_delta=delta,
                evidence=evidence,
            )

        leaked = dict(candidate)
        leaked["leakage_group_id"] = "different-parent-group"
        with self.assertRaisesRegex(DepthValidationError, "leakage_group_id"):
            _validate_controlled_relationship(
                leaked,
                anchor,
                parsed_delta=delta,
                evidence=evidence,
            )

    def test_parameter_contract_preserves_context_and_derived_values(self) -> None:
        code = """\
length_um = 12.0
layer = (1, 0)
optical_port_specs = [('o1', 0.0, 0.0, 180.0, 0.5)]
"""
        anchor_payload = {
            "fixed_context": {"layer": [1, 0]},
            "parameters": {
                "length_um": 10.0,
                "optical_port_specs": [["o1", 0.0, 0.0, 180.0, 0.5]],
            },
        }
        candidate_payload = {
            "fixed_context": {"layer": [1, 0]},
            "parameters": {
                "length_um": 12.0,
                "optical_port_specs": [["o1", 0.0, 0.0, 180.0, 0.5]],
            },
        }
        _validate_parameter_payload(
            "row",
            code,
            candidate_payload,
            anchor_payload=anchor_payload,
        )
        changed_context = json.loads(json.dumps(candidate_payload))
        changed_context["fixed_context"]["layer"] = [2, 0]
        with self.assertRaisesRegex(DepthValidationError, "fixed_context"):
            _validate_parameter_payload(
                "row",
                code,
                changed_context,
                anchor_payload=anchor_payload,
            )
        omitted_derived = json.loads(json.dumps(candidate_payload))
        omitted_derived["parameters"].pop("optical_port_specs")
        with self.assertRaisesRegex(DepthValidationError, "keys differ"):
            _validate_parameter_payload(
                "row",
                code,
                omitted_derived,
                anchor_payload=anchor_payload,
            )

    def test_only_repeat_count_axes_relax_connectivity(self) -> None:
        row = _row()
        row["controlled_axes"] = ["length_um"]
        repeat_names = {row["parent_core_id"]: {"count"}}
        self.assertFalse(_changes_repeat_count(row, repeat_names))
        row["controlled_axes"] = ["length_um", "count"]
        self.assertTrue(_changes_repeat_count(row, repeat_names))

    def test_runtime_port_signature_checks_geometry_bound_records(self) -> None:
        signature = {
            "count": 1,
            "names": ["o1"],
            "ports": [
                {
                    "center": [0.0, 0.0],
                    "name": "o1",
                    "orientation": 180.0,
                    "width": 0.5,
                }
            ],
        }
        runtime = {
            "ports": [
                {
                    "center": [0.0, 0.0],
                    "name": "o1",
                    "orientation": 180.0,
                    "width": 0.5,
                }
            ]
        }
        _runtime_port_signature("legacy-core-row", {}, {"ports": []})
        _runtime_port_signature("row", signature, runtime)
        _runtime_port_signature("row", "1x0", runtime)
        corrupted = json.loads(json.dumps(signature))
        corrupted["ports"][0]["width"] = 0.8
        with self.assertRaisesRegex(DepthValidationError, "port record"):
            _runtime_port_signature("row", corrupted, runtime)

    def test_runtime_port_evidence_binds_exact_witnesses(self) -> None:
        witness = PortWitness(
            name="o1",
            side="left",
            bbox_side="left",
            orientation_deg=180.0,
            width_um=0.5,
            inward_material_fraction=1.0,
            outward_material_fraction=0.0,
            touches_material=True,
        )
        report = PortGateReport(
            passed=True,
            errors=(),
            port_count=1,
            orientation_side_histogram={"left": 1},
            witnesses=(witness,),
        )
        evidence = {
            "port_count": 1,
            "port_orientation_side_histogram": {"left": 1},
            "port_witnesses": [
                {
                    "bbox_side": "left",
                    "inward_material_fraction": 1.0,
                    "name": "o1",
                    "orientation_deg": 180.0,
                    "outward_material_fraction": 0.0,
                    "side": "left",
                    "touches_material": True,
                    "width_um": 0.5,
                }
            ],
        }
        _validate_runtime_port_evidence("row", evidence, report)
        corrupted = json.loads(json.dumps(evidence))
        corrupted["port_witnesses"][0]["touches_material"] = False
        with self.assertRaisesRegex(DepthValidationError, "port witnesses"):
            _validate_runtime_port_evidence("row", corrupted, report)

    def test_repeat_count_evidence_binds_emitted_polygon_count(self) -> None:
        row = _row()
        row.update(
            {
                "code": ANCHOR_CODE + "\nrows = 2\ncolumns = 3\n",
                "controlled_axes": ["rows"],
                "parent_core_id": "count-anchor",
                "realization_slot": 1,
                "verification_evidence_json": json.dumps(
                    {"runtime_structural_metrics": {"polygon_count": 6}}
                ),
            }
        )
        names = {"count-anchor": {"rows", "columns"}}
        _validate_repeated_element_counts([row], names)
        row["verification_evidence_json"] = json.dumps(
            {"runtime_structural_metrics": {"polygon_count": 5}}
        )
        with self.assertRaisesRegex(
            DepthValidationError,
            "geometry witness differs",
        ):
            _validate_repeated_element_counts([row], names)


if __name__ == "__main__":
    unittest.main()
