"""Regression tests for the visual-only expansion proposal boundary."""

from __future__ import annotations

import json
import sys
import unittest
from collections import Counter
from pathlib import Path

import gdsfactory as gf
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _shared import ReleaseError, normalized_d4_sha256  # noqa: E402
from build_expansion_proposals import (  # noqa: E402
    SPEC_SCHEMA_VERSION,
    _load_scene_module,
    _runtime_ports,
    render_component_max_visible,
    safe_generated_output,
    snapshot_frozen_core,
    validate_proposal_specs,
)
from expansion_nearest import (  # noqa: E402
    aligned_mask_similarity,
    load_core_semantic_anchors,
)


class ExpansionProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.core = snapshot_frozen_core(ROOT)
        cls.anchors = load_core_semantic_anchors(ROOT)

    def test_semantic_index_matches_frozen_representations(self) -> None:
        self.assertEqual(len(self.anchors), self.core.representation_count)
        self.assertEqual(
            Counter(anchor.level for anchor in self.anchors),
            Counter({"L0": 93, "L1": 127, "L2": 99, "L3": 120, "L4": 108}),
        )
        self.assertEqual(
            len({anchor.representation_id for anchor in self.anchors}),
            len(self.anchors),
        )

    def test_core_snapshot_covers_every_reference_artifact(self) -> None:
        self.assertEqual(self.core.core_name, "core-v1")
        self.assertEqual(self.core.row_count, 738)
        self.assertEqual(self.core.representation_count, 547)
        self.assertIn(
            "factory/core-v1/source.tar.gz",
            self.core.file_sha256,
        )
        self.assertIn(
            "data/l4/train-00000-of-00001.parquet",
            self.core.file_sha256,
        )
        self.assertGreater(len(self.core.core_anchor_aliases), len(self.anchors))

    def test_output_guard_allows_only_wave_generated_directory(self) -> None:
        expected = (ROOT / "factory" / "expansion" / "wave-1" / "generated").resolve()
        self.assertEqual(safe_generated_output(ROOT, "wave-1"), expected)
        self.assertEqual(
            safe_generated_output(ROOT, "wave-1", requested=expected),
            expected,
        )
        with self.assertRaisesRegex(ReleaseError, "must be exactly"):
            safe_generated_output(
                ROOT,
                "wave-1",
                requested=ROOT / "factory" / "core-v1",
            )
        with self.assertRaisesRegex(ReleaseError, "unsafe expansion wave"):
            safe_generated_output(ROOT, "../core-v1")

    def test_aligned_similarity_is_rotation_and_reflection_stable(self) -> None:
        image = Image.new("L", (180, 120), 255)
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 20, 42, 100), fill=0)
        draw.rectangle((20, 78, 145, 100), fill=0)
        rotated = image.rotate(90, expand=True)
        mirrored = rotated.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        comparison = aligned_mask_similarity(image, mirrored)
        self.assertEqual(comparison["aligned_raw_iou"], 1.0)
        self.assertEqual(comparison["aligned_dilated_iou"], 1.0)

    def _minimal_specs(self) -> dict:
        nearest = self.anchors[0].example_id
        return {
            "schema_version": SPEC_SCHEMA_VERSION,
            "wave_id": "wave-1",
            "core_release_digest_sha256": self.core.release_digest_sha256,
            "status": "proposal_only_requires_human_approval",
            "mutates_core": False,
            "candidate_count": 1,
            "level_counts": {"L1": 1},
            "candidates": [
                {
                    "candidate_id": "test_new_grammar",
                    "representation_id": "test_new_grammar",
                    "label": "Test new grammar",
                    "level": "L1",
                    "family_id": "test_family",
                    "family_label": "Test family",
                    "mechanism": "ported_test_mechanism",
                    "path_grammar": "one body to two explicit terminal leads",
                    "port_signature": "1x1",
                    "roles": [
                        {"role": "body", "count": 1},
                        {"role": "lead", "count": 2},
                    ],
                    "structural_witnesses": {
                        "bodies": 1,
                        "terminals": 2,
                    },
                    "nearest_core_ids": [nearest],
                    "representation_deltas": [
                        "adds a port-aware relation absent from the nearest anchor"
                    ],
                    "prerequisite_ids": ["l0_01_rectangle"],
                    "scene_id": "test_scene",
                    "scene_parameters": {"body_width_um": 20.0},
                    "scene": {
                        "archetype": "l1_port_operation",
                        "variant": 0,
                    },
                }
            ],
        }

    def test_spec_validator_resolves_only_real_semantic_anchors(self) -> None:
        validated = validate_proposal_specs(
            self._minimal_specs(),
            wave_id="wave-1",
            core=self.core,
            anchors=self.anchors,
        )
        self.assertEqual(len(validated), 1)
        self.assertEqual(
            validated[0]["nearest_core_ids"],
            [self.anchors[0].example_id],
        )

        dangling = self._minimal_specs()
        dangling["candidates"][0]["nearest_core_ids"] = ["missing_core_row"]
        with self.assertRaisesRegex(ReleaseError, "dangling nearest core ID"):
            validate_proposal_specs(
                dangling,
                wave_id="wave-1",
                core=self.core,
                anchors=self.anchors,
            )

        nonsemantic_id, representation_id = next(
            (example_id, grammar_id)
            for example_id, grammar_id in self.core.core_anchor_aliases.items()
            if example_id not in {anchor.example_id for anchor in self.anchors}
        )
        aliased = self._minimal_specs()
        aliased["candidates"][0]["nearest_core_ids"] = [nonsemantic_id]
        validated = validate_proposal_specs(
            aliased,
            wave_id="wave-1",
            core=self.core,
            anchors=self.anchors,
        )
        anchor_by_representation = {
            anchor.representation_id: anchor for anchor in self.anchors
        }
        self.assertEqual(
            validated[0]["nearest_core_ids"],
            [anchor_by_representation[representation_id].example_id],
        )

    def test_registry_counts_and_proposal_only_boundary_are_mandatory(self) -> None:
        wrong_status = self._minimal_specs()
        wrong_status["status"] = "approved"
        with self.assertRaisesRegex(ReleaseError, "status must be"):
            validate_proposal_specs(
                wrong_status,
                wave_id="wave-1",
                core=self.core,
                anchors=self.anchors,
            )

        mutating = self._minimal_specs()
        mutating["mutates_core"] = True
        with self.assertRaisesRegex(ReleaseError, "mutates_core=false"):
            validate_proposal_specs(
                mutating,
                wave_id="wave-1",
                core=self.core,
                anchors=self.anchors,
            )

        admitted = self._minimal_specs()
        admitted["admission_status"] = "pending"
        with self.assertRaisesRegex(ReleaseError, "cannot contain admission"):
            validate_proposal_specs(
                admitted,
                wave_id="wave-1",
                core=self.core,
                anchors=self.anchors,
            )

        candidate_admitted = self._minimal_specs()
        candidate_admitted["candidates"][0]["admitted"] = False
        with self.assertRaisesRegex(ReleaseError, "candidates cannot contain"):
            validate_proposal_specs(
                candidate_admitted,
                wave_id="wave-1",
                core=self.core,
                anchors=self.anchors,
            )

        bad_counts = self._minimal_specs()
        bad_counts["level_counts"] = {"L1": 2}
        with self.assertRaisesRegex(ReleaseError, "level_counts differ"):
            validate_proposal_specs(
                bad_counts,
                wave_id="wave-1",
                core=self.core,
                anchors=self.anchors,
            )

    def test_prerequisites_must_resolve_and_l4_must_bridge_from_l3(self) -> None:
        dangling = self._minimal_specs()
        dangling["candidates"][0]["prerequisite_ids"] = ["not_a_core_grammar"]
        with self.assertRaisesRegex(ReleaseError, "dangling prerequisite ID"):
            validate_proposal_specs(
                dangling,
                wave_id="wave-1",
                core=self.core,
                anchors=self.anchors,
            )

        no_l3_bridge = self._minimal_specs()
        no_l3_bridge["candidates"][0]["level"] = "L4"
        no_l3_bridge["level_counts"] = {"L4": 1}
        with self.assertRaisesRegex(ReleaseError, "must bridge from L3"):
            validate_proposal_specs(
                no_l3_bridge,
                wave_id="wave-1",
                core=self.core,
                anchors=self.anchors,
            )

        l3_concept = next(
            identifier
            for identifier, level in self.core.core_prerequisite_levels.items()
            if level == "L3" and identifier.startswith("l3_")
        )
        bridged = self._minimal_specs()
        bridged["candidates"][0]["level"] = "L4"
        bridged["candidates"][0]["prerequisite_ids"] = [l3_concept]
        bridged["level_counts"] = {"L4": 1}
        validated = validate_proposal_specs(
            bridged,
            wave_id="wave-1",
            core=self.core,
            anchors=self.anchors,
        )
        self.assertEqual(validated[0]["prerequisite_ids"], [l3_concept])

    def test_max_visible_renderer_preserves_footprint_metadata(self) -> None:
        component = gf.Component()
        component.add_ref(
            gf.components.rectangle(
                size=(30.0, 2.0),
                layer=(1, 0),
                port_type=None,
            )
        )
        image, footprint, calibration = render_component_max_visible(component)
        self.assertAlmostEqual(footprint[0], 30.0)
        self.assertAlmostEqual(footprint[1], 2.0)
        self.assertGreaterEqual(calibration["bbox_size_px"][1], 220)
        self.assertEqual(calibration["footprint_um"], list(footprint))
        self.assertGreater(image.size[0], image.size[1])

    def test_central_scene_module_satisfies_compiler_interface(self) -> None:
        candidate = self._minimal_specs()["candidates"][0]
        _module, build_proposal = _load_scene_module(SCRIPTS / "proposal_scenes.py")
        component = build_proposal(candidate)
        self.assertEqual(len(_runtime_ports(component)), 2)
        image, footprint, _calibration = render_component_max_visible(component)
        self.assertGreater(min(image.size), 0)
        self.assertGreater(min(footprint), 0)

    def test_real_wave_scenes_execute_and_are_d4_unique(self) -> None:
        specs_path = ROOT / "factory" / "expansion" / "wave-1" / "specs.json"
        payload = json.loads(specs_path.read_text(encoding="utf-8"))
        candidates = validate_proposal_specs(
            payload,
            wave_id="wave-1",
            core=self.core,
            anchors=self.anchors,
        )
        self.assertEqual(len(candidates), 100)
        _module, build_proposal = _load_scene_module(SCRIPTS / "proposal_scenes.py")
        seen: dict[str, str] = {}
        for candidate in candidates:
            component = build_proposal(candidate)
            expected_ports = sum(
                int(value) for value in candidate["port_signature"].split("x")
            )
            self.assertEqual(
                len(_runtime_ports(component)),
                expected_ports,
                candidate["candidate_id"],
            )
            image, footprint, _calibration = render_component_max_visible(component)
            self.assertGreater(min(footprint), 0, candidate["candidate_id"])
            digest = normalized_d4_sha256(image)
            self.assertNotIn(
                digest,
                seen,
                f"{candidate['candidate_id']} aliases {seen.get(digest)}",
            )
            seen[digest] = candidate["candidate_id"]


if __name__ == "__main__":
    unittest.main()
