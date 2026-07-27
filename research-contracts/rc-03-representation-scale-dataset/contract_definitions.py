"""RC-03 contract data bound to the shared verdict engine."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rclib import Contract, Verdict, evaluate as _evaluate, verdict as _verdict

CONTRACT = Contract(
    slug="rc-03-representation-scale-dataset",
    gates=(
        "T1_corpus_integrity",
        "T2_layer_separation",
        "T3_protected_splits",
        "T4_abstention_enforced",
        "T5_matched_compute_comparison",
    ),
    evidence_keys=frozenset(
        {
            "source_manifest",
            "license_manifest",
            "provenance_records",
            "calibration_records",
            "topology_annotations",
            "scale_evidence",
            "programs_or_reconstructions",
            "split_hashes",
            "leakage_audit",
            "baselines",
            "compute_log",
            "error_taxonomy",
            "rerun_script",
        }
    ),
)


def verdict(report: dict) -> Verdict:
    return _verdict(CONTRACT, report)


def evaluate(case: dict) -> dict:
    return _evaluate(CONTRACT, case)
