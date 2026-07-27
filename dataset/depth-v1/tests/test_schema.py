"""Focused regression tests for the isolated depth-v1 release schema."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from schema import (  # noqa: E402
    ANCHOR_ONLY_PARENT_IDS,
    APPROVED_REPRESENTATION_COUNT,
    CORE_EXTRA_ROW_COUNT,
    CORE_ROW_COLUMNS,
    CORE_SCHEMA_VERSION,
    DEPTH_CONTROL_COLUMNS,
    DEPTH_ROW_COLUMNS,
    DEPTH_ROW_COUNT,
    DEPTH_ELIGIBLE_COUNT,
    DEPTH_SCHEMA_VERSION,
    EXPECTED_SPLIT_COUNTS,
    FROZEN_LOGICAL_RELEASE_SHA256,
    MANIFEST_SCHEMA_VERSION,
    DepthSchemaError,
    bind_logical_row_sha256,
    build_freeze,
    build_manifest,
    canonical_sha256,
    depth_features,
    logical_release_sha256,
    logical_row_sha256,
    plan_shards,
    shard_filename,
    validate_depth_population,
    verify_checksums,
    write_checksums,
    write_json,
)


CORE_DIGEST = "c" * 64


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _row(parent: int, slot: int, *, suffix: str = "") -> dict:
    parent_id = (
        next(iter(ANCHOR_ONLY_PARENT_IDS))
        if parent == 0
        else f"core_{parent:03d}"
    )
    if slot == 0:
        row_id = parent_id
    elif slot > 0:
        row_id = f"{parent_id}_r{slot:02d}"
    else:
        row_id = f"{parent_id}_core_extra_{suffix}"
    image_bytes = (
        b"image"
        if slot <= 0
        else f"image/{parent}/{slot}".encode("utf-8")
    )
    target_bytes = (
        b"target"
        if slot <= 0
        else f"target/{parent}/{slot}".encode("utf-8")
    )
    row = {
        "schema_version": CORE_SCHEMA_VERSION,
        "id": row_id,
        "level": "L4",
        "curriculum_order": parent,
        "image": {"bytes": image_bytes, "path": None},
        "target_image": {"bytes": target_bytes, "path": None},
        "code": "import gdsfactory as gf\n",
        "code_language": "python",
        "instruction": f"Recreate the geometry for {row_id}.",
        "label": row_id,
        "family": "test",
        "concept_id": parent_id,
        "representation_id": parent_id,
        "grammar_id": parent_id,
        "leakage_group_id": parent_id,
        "variation_role": "semantic" if slot == 0 else "realization",
        "primitive_calls": ["straight"],
        "prerequisite_ids": [],
        "port_signature_json": '{"count":2}',
        "footprint_um": [20.0, 4.0],
        "parameters_json": "{}",
        "topology_json": "{}",
        "metadata_json": "{}",
        "image_sha256": hashlib.sha256(image_bytes).hexdigest(),
        "target_image_sha256": hashlib.sha256(target_bytes).hexdigest(),
        "code_sha256": _digest("import gdsfactory as gf\n"),
        "normalized_d4_sha256": _digest(f"d4/{row_id}"),
        "view_policy": "max_visible_v1",
        "source_dataset_digest_sha256": CORE_DIGEST,
        "source_generator_version": "core-v1",
        "depth_schema_version": DEPTH_SCHEMA_VERSION,
        "parent_core_id": parent_id,
        "parent_code_sha256": _digest("import gdsfactory as gf\n"),
        "parent_core_digest_sha256": CORE_DIGEST,
        "geometry_id": f"geometry/{row_id}" if slot >= 0 else "",
        "realization_id": f"r{slot:02d}" if slot >= 0 else f"core-extra-{suffix}",
        "realization_slot": slot,
        "transform_kind": "anchor" if slot == 0 else "controlled",
        "controlled_axes": [] if slot <= 0 else ["length_um"],
        "parameter_delta_json": "{}" if slot <= 0 else '{"length_um":1.0}',
        "dependency_group": f"dependency/{parent_id}",
        "split_role": (
            "core-extra" if slot == -1 else ("train" if slot <= 5 else "validation")
        ),
        "pose_id": "base",
        "render_id": "primary",
        "verification_evidence_json": "{}",
        "depth_generator_version": "depth-test-v1",
        "logical_row_sha256": "",
    }
    return bind_logical_row_sha256(row)


def _complete_population() -> list[dict]:
    rows = []
    for parent in range(APPROVED_REPRESENTATION_COUNT):
        slots = (0,) if parent == 0 else range(8)
        rows.extend(_row(parent, slot) for slot in slots)
    rows.extend(
        _row(
            index % APPROVED_REPRESENTATION_COUNT,
            -1,
            suffix=str(index),
        )
        for index in range(CORE_EXTRA_ROW_COUNT)
    )
    return rows


def _shard_records(split: str, row_count: int) -> list[dict]:
    records = []
    for plan in plan_shards(
        row_count,
        max_rows_per_shard=1000,
        split=split,
    ):
        records.append(
            {
                "split": split,
                "index": plan.index,
                "total": plan.total,
                "path": f"data/{split}/{plan.filename}",
                "rows": plan.row_count,
                "bytes": 100 + plan.index,
                "sha256": _digest(f"{split}/{plan.index}"),
            }
        )
    return records


class DepthSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = _complete_population()

    def test_core_columns_are_preserved_before_depth_controls(self) -> None:
        self.assertEqual(
            DEPTH_ROW_COLUMNS,
            (*CORE_ROW_COLUMNS, *DEPTH_CONTROL_COLUMNS),
        )
        self.assertEqual(tuple(depth_features()), DEPTH_ROW_COLUMNS)
        self.assertIn("verification_evidence_json", DEPTH_CONTROL_COLUMNS)
        self.assertNotIn("admission_evidence_json", DEPTH_CONTROL_COLUMNS)

    def test_frozen_logical_release_digest_is_named_and_exact(self) -> None:
        self.assertEqual(
            FROZEN_LOGICAL_RELEASE_SHA256,
            "676c49134d4d044c7d84426cf8eeecf09302e74ca4aa548956f14b7631a4d80b",
        )

    def test_logical_row_digest_excludes_payload_bytes_not_payload_hashes(self) -> None:
        row = _row(0, 0)
        original = logical_row_sha256(row)
        changed_payload = dict(row)
        changed_payload["image"] = {"bytes": b"different", "path": None}
        self.assertEqual(logical_row_sha256(changed_payload), original)
        changed_hash = dict(row)
        changed_hash["image_sha256"] = _digest("different")
        self.assertNotEqual(logical_row_sha256(changed_hash), original)
        changed_schema = dict(row)
        changed_schema["schema_version"] = "unexpected-core-schema"
        with self.assertRaisesRegex(DepthSchemaError, "core row schema"):
            logical_row_sha256(changed_schema)

    def test_logical_release_digest_is_input_order_independent(self) -> None:
        rows = [_row(0, 0), _row(1, 0)]
        self.assertEqual(
            logical_release_sha256(rows),
            logical_release_sha256(reversed(rows)),
        )
        self.assertEqual(
            canonical_sha256({"a": 1, "b": [2]}),
            canonical_sha256({"b": [2], "a": 1}),
        )

    def test_deterministic_shard_names_and_ranges(self) -> None:
        plans = plan_shards(2501, max_rows_per_shard=1000, split="train")
        self.assertEqual(len(plans), 3)
        self.assertEqual(plans[0].filename, "train-00000-of-00003.parquet")
        self.assertEqual(plans[-1].filename, "train-00002-of-00003.parquet")
        self.assertEqual([plan.row_count for plan in plans], [1000, 1000, 501])
        with self.assertRaises(DepthSchemaError):
            shard_filename("../train", 0, 1)

    def test_complete_population_and_manifest_contract(self) -> None:
        summary = validate_depth_population(
            self.rows,
            expected_parent_core_digest_sha256=CORE_DIGEST,
        )
        self.assertEqual(summary["row_count"], DEPTH_ROW_COUNT)
        self.assertEqual(
            summary["approved_representation_count"],
            APPROVED_REPRESENTATION_COUNT,
        )
        self.assertEqual(
            summary["complete_depth_representation_count"],
            DEPTH_ELIGIBLE_COUNT,
        )
        self.assertEqual(
            summary["anchor_only_parent_ids"],
            sorted(ANCHOR_ONLY_PARENT_IDS),
        )
        self.assertEqual(summary["split_counts"], EXPECTED_SPLIT_COUNTS)
        shards = [
            *_shard_records("train", EXPECTED_SPLIT_COUNTS["train"]),
            *_shard_records(
                "validation",
                EXPECTED_SPLIT_COUNTS["validation"],
            ),
        ]
        manifest = build_manifest(
            self.rows,
            shards=shards,
            depth_generator_version="depth-test-v1",
            expected_parent_core_digest_sha256=CORE_DIGEST,
        )
        self.assertEqual(manifest["schema_version"], MANIFEST_SCHEMA_VERSION)
        self.assertEqual(manifest["row_count"], DEPTH_ROW_COUNT)
        self.assertEqual(manifest["split_counts"], EXPECTED_SPLIT_COUNTS)

        non_public = list(self.rows)
        changed = dict(non_public[0])
        changed["verification_evidence_json"] = '{"status":"accepted"}'
        non_public[0] = bind_logical_row_sha256(changed)
        with self.assertRaisesRegex(DepthSchemaError, "non-public control key"):
            validate_depth_population(
                non_public,
                expected_parent_core_digest_sha256=CORE_DIGEST,
            )

    def test_freeze_and_checksum_helpers_are_release_relative(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = {
                "schema_version": MANIFEST_SCHEMA_VERSION,
                "logical_release_sha256": _digest("logical-release"),
                "parent_core_digest_sha256": CORE_DIGEST,
                "row_count": DEPTH_ROW_COUNT,
                "approved_representation_count": APPROVED_REPRESENTATION_COUNT,
                "complete_depth_representation_count": DEPTH_ELIGIBLE_COUNT,
                "anchor_only_representation_count": len(
                    ANCHOR_ONLY_PARENT_IDS
                ),
                "anchor_only_parent_ids": sorted(ANCHOR_ONLY_PARENT_IDS),
                "geometry_state_count": 8,
            }
            write_json(root / "metadata" / "manifest.json", manifest)
            (root / "release.txt").write_text("depth release\n", encoding="utf-8")
            freeze = build_freeze(
                root,
                manifest,
                manifest_path="metadata/manifest.json",
                reference_paths=["release.txt"],
            )
            self.assertEqual(
                freeze["reference_artifacts"].keys(),
                {"release.txt"},
            )
            changed_manifest = dict(manifest)
            changed_manifest["row_count"] = 1
            with self.assertRaisesRegex(DepthSchemaError, "manifest object differs"):
                build_freeze(
                    root,
                    changed_manifest,
                    manifest_path="metadata/manifest.json",
                    reference_paths=["release.txt"],
                )
            write_json(root / "metadata" / "freeze.json", freeze)
            write_checksums(root)
            verify_checksums(root)
            (root / "release.txt").write_text("drift\n", encoding="utf-8")
            with self.assertRaisesRegex(DepthSchemaError, "changed="):
                verify_checksums(root)


if __name__ == "__main__":
    unittest.main()
