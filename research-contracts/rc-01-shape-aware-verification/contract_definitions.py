"""RC-01 contract data bound to the shared verdict engine.

Pure and deterministic. The gates and evidence keys here are the
contract's data; the decision rule lives once in ``rclib``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rclib import Contract, Verdict, evaluate as _evaluate, verdict as _verdict

CONTRACT = Contract(
    slug="rc-01-shape-aware-verification",
    gates=(
        "T1_pure_deterministic_metric",
        "T2_frozen_perturbation_suite",
        "T3_ordering_improvement",
        "T4_adversarial_pairs_ordered",
        "T5_single_rerun_reproduces",
    ),
    evidence_keys=frozenset(
        {
            "metric_code",
            "metric_definition",
            "calibrated_corpus",
            "perturbation_generator",
            "hidden_split_manifest",
            "annotation_protocol",
            "baseline_analysis",
            "raw_scores",
            "failure_cases",
            "rerun_script",
        }
    ),
)


def verdict(report: dict) -> Verdict:
    return _verdict(CONTRACT, report)


def evaluate(case: dict) -> dict:
    return _evaluate(CONTRACT, case)
