"""Release-level regression tests using only the published package."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _shared import (  # noqa: E402
    LEVELS,
    ReleaseError,
    SCHEMA_VERSION,
    canonical_sha256,
    iter_release_files,
    read_json,
    sha256_file,
)
from build_release import (  # noqa: E402
    ROW_COLUMNS,
    _validate_l4_source_port_evidence,
    release_features,
)
from validate_release import (  # noqa: E402
    _validate_runtime_port_contract,
    validate_release,
)
from pack_core_v1_source import write_deterministic_archive  # noqa: E402


class ReleaseTests(unittest.TestCase):
    def test_public_schema_is_stable(self) -> None:
        self.assertEqual(SCHEMA_VERSION, "pixcell-image-code-curriculum-v1")
        self.assertEqual(LEVELS, ("l0", "l1", "l2", "l3", "l4"))
        self.assertEqual(len(ROW_COLUMNS), 30)
        self.assertEqual(len(ROW_COLUMNS), len(set(ROW_COLUMNS)))
        self.assertEqual(release_features()["footprint_um"].feature.dtype, "float64")

    def test_canonical_hash_ignores_mapping_order(self) -> None:
        self.assertEqual(
            canonical_sha256({"a": 1, "b": [2, 3]}),
            canonical_sha256({"b": [2, 3], "a": 1}),
        )

    def test_host_control_files_are_not_checksum_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / ".gitattributes").write_text("*.parquet filter=lfs\n")
            (root / ".gitignore").write_text("__pycache__/\n")
            (root / "README.md").write_text("release\n")
            for cache in ("__pycache__", ".pytest_cache", ".ruff_cache"):
                directory = root / cache
                directory.mkdir()
                (directory / "cache").write_text("host cache\n")
            self.assertEqual(
                [path.name for path in iter_release_files(root)],
                ["README.md"],
            )

    def test_complete_release(self) -> None:
        report = validate_release(ROOT)
        self.assertEqual(report["total_rows"], sum(report["level_counts"].values()))
        self.assertEqual(report["compiled_programs"], report["total_rows"])
        self.assertEqual(report["purity_clean_programs"], report["total_rows"])
        self.assertEqual(report["embedded_images"], 2 * report["total_rows"])

    def test_core_v1_freeze_matches_catalog(self) -> None:
        freeze = read_json(ROOT / "factory" / "core-v1" / "freeze.json")
        catalog = read_json(ROOT / "metadata" / "catalog.json")
        self.assertEqual(freeze["core_name"], "core-v1")
        self.assertEqual(
            freeze["release_digest_sha256"],
            catalog["release_digest_sha256"],
        )
        self.assertEqual(freeze["row_count"], catalog["total_rows"])
        self.assertEqual(
            freeze["representation_count"],
            catalog["total_representation_ids"],
        )

    def test_core_v1_reference_artifacts_are_byte_identical(self) -> None:
        freeze = read_json(ROOT / "factory" / "core-v1" / "freeze.json")
        references = freeze.get("reference_artifacts")
        self.assertIsInstance(references, dict)
        self.assertTrue(references)
        for relative, expected_sha256 in sorted(references.items()):
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            self.assertEqual(sha256_file(path), expected_sha256, relative)

    def test_source_archive_writer_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "payload.txt"
            source.write_text("deterministic payload\n", encoding="utf-8")
            payload = {"rl/tasks/example/payload.txt": source}
            manifest = {
                "schema_version": "test",
                "files": [
                    {
                        "path": "rl/tasks/example/payload.txt",
                        "bytes": source.stat().st_size,
                        "sha256": sha256_file(source),
                    }
                ],
            }
            first = root / "first.tar.gz"
            second = root / "second.tar.gz"
            write_deterministic_archive(first, payload, manifest)
            write_deterministic_archive(second, payload, manifest)
            self.assertEqual(sha256_file(first), sha256_file(second))

    def test_l4_runtime_ports_must_match_declared_boundary_histogram(self) -> None:
        row = {
            "id": "l4_test",
            "level": "l4",
            "port_signature": "1x2",
            "topology": {"expected_optical_edge_ports": {"left": 1, "right": 2}},
        }
        result = {
            "bbox_um": [[0.0, -2.0], [10.0, 2.0]],
            "port_count": 3,
            "ports": [
                {
                    "center": [0.125, 0.0],
                    "name": "o1",
                    "orientation": 150.0,
                    "port_type": "optical",
                    "width": 0.5,
                },
                {
                    "center": [10.0, -1.0],
                    "name": "o2",
                    "orientation": 0.0,
                    "port_type": "optical",
                    "width": 0.5,
                },
                {
                    "center": [9.875, 1.0],
                    "name": "o3",
                    "orientation": 30.0,
                    "port_type": "optical",
                    "width": 0.5,
                },
            ],
        }
        _validate_runtime_port_contract(row, result)
        result["ports"][2]["center"] = [5.0, 1.0]
        with self.assertRaisesRegex(ReleaseError, "no outward"):
            _validate_runtime_port_contract(row, result)
        result["ports"][2]["center"] = [10.0, 3.0]
        with self.assertRaisesRegex(ReleaseError, "no outward"):
            _validate_runtime_port_contract(row, result)
        result["ports"][2]["center"] = [10.0, 1.0]
        result["ports"][2]["orientation"] = 180.0
        with self.assertRaisesRegex(ReleaseError, "no outward"):
            _validate_runtime_port_contract(row, result)
        result["ports"][2] = {**result["ports"][1], "name": "o3"}
        with self.assertRaisesRegex(ReleaseError, "duplicated physical terminal"):
            _validate_runtime_port_contract(row, result)

    def test_l4_corner_tie_must_still_satisfy_global_histogram(self) -> None:
        offset = 2**0.5 * 0.25 / 2
        result = {
            "bbox_um": [[0.0, 0.0], [10.0, 10.0]],
            "port_count": 1,
            "ports": [
                {
                    "center": [offset, 10.0 - offset],
                    "name": "o1",
                    "orientation": 135.0,
                    "port_type": "optical",
                    "width": 0.5,
                }
            ],
        }
        satisfiable = {
            "id": "l4_corner_left",
            "level": "l4",
            "port_signature": "1x0",
            "topology": {"expected_optical_edge_ports": {"left": 1}},
        }
        _validate_runtime_port_contract(satisfiable, result)
        impossible = {
            "id": "l4_corner_right",
            "level": "l4",
            "port_signature": "0x1",
            "topology": {"expected_optical_edge_ports": {"right": 1}},
        }
        with self.assertRaisesRegex(ReleaseError, "cannot satisfy"):
            _validate_runtime_port_contract(impossible, result)

    def test_l3_runtime_ports_match_full_declared_geometry(self) -> None:
        port = {
            "center": [0.0, 0.0],
            "name": "o1",
            "orientation": 180.0,
            "port_type": "optical",
            "width": 0.5,
        }
        row = {
            "id": "l3_test",
            "level": "l3",
            "port_signature": {
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
            },
            "topology": {},
        }
        result = {
            "bbox_um": [[0.0, -0.25], [10.0, 0.25]],
            "port_count": 1,
            "ports": [port],
        }
        _validate_runtime_port_contract(row, result)
        result["ports"][0]["width"] = 0.6
        with self.assertRaisesRegex(ReleaseError, "width drifted"):
            _validate_runtime_port_contract(row, result)

    def test_l2_runtime_ports_are_finite_positive_and_exact_count(self) -> None:
        row = {
            "id": "l2_test",
            "level": "l2",
            "port_signature": "1x1",
            "topology": {},
        }
        result = {
            "bbox_um": [[0.0, -0.25], [10.0, 0.25]],
            "port_count": 2,
            "ports": [
                {
                    "center": [0.0, 0.0],
                    "name": "o1",
                    "orientation": 180.0,
                    "port_type": "optical",
                    "width": 0.5,
                },
                {
                    "center": [10.0, 0.0],
                    "name": "o2",
                    "orientation": 0.0,
                    "port_type": "optical",
                    "width": 0.5,
                },
            ],
        }
        _validate_runtime_port_contract(row, result)
        result["ports"][1]["width"] = 0.0
        with self.assertRaisesRegex(ReleaseError, "invalid width"):
            _validate_runtime_port_contract(row, result)

    def test_l4_package_build_requires_executed_port_evidence(self) -> None:
        topology = {
            "expected_optical_edge_ports": {"left": 1, "right": 2},
            "runtime_port_evidence": {
                "expected_count": 3,
                "expected_edge_counts": {
                    "left": 1,
                    "right": 2,
                    "bottom": 0,
                    "top": 0,
                },
                "observed_edge_counts": {
                    "left": 1,
                    "right": 2,
                    "bottom": 0,
                    "top": 0,
                },
                "runtime_inspected": True,
                "source_admission_bound": False,
                "machine_checks_passed": True,
            },
        }
        _validate_l4_source_port_evidence("l4_test", topology)
        stale = {
            **topology,
            "runtime_port_evidence": {
                **topology["runtime_port_evidence"],
                "runtime_inspected": False,
                "source_admission_bound": True,
            },
        }
        with self.assertRaisesRegex(ReleaseError, "not runtime-inspected"):
            _validate_l4_source_port_evidence("l4_test", stale)
        mismatched = {
            **topology,
            "runtime_port_evidence": {
                **topology["runtime_port_evidence"],
                "observed_edge_counts": {
                    "left": 2,
                    "right": 1,
                    "bottom": 0,
                    "top": 0,
                },
            },
        }
        with self.assertRaisesRegex(ReleaseError, "differs from topology"):
            _validate_l4_source_port_evidence("l4_test", mismatched)


if __name__ == "__main__":
    unittest.main()
