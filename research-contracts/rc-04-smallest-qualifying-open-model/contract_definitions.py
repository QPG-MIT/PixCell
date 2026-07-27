"""RC-04 contract data bound to the shared verdict engine."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rclib import Contract, Verdict, evaluate as _evaluate, verdict as _verdict

CONTRACT = Contract(
    slug="rc-04-smallest-qualifying-open-model",
    gates=(
        "T1_frozen_protocol",
        "T2_identical_budgets_full_raw",
        "T3_recomputable_bounds",
        "T4_source_purity",
        "T5_release_and_accounting",
    ),
    evidence_keys=frozenset(
        {
            "candidate_registry",
            "tier_floors",
            "budget_manifest",
            "preregistration_commit",
            "raw_programs",
            "all_attempts",
            "scores",
            "bounds_script",
            "purity_gate_results",
            "release_bundle",
            "parameter_accounting",
            "runtime_accounting",
            "frontier_analysis",
        }
    ),
)


def verdict(report: dict) -> Verdict:
    return _verdict(CONTRACT, report)


def evaluate(case: dict) -> dict:
    return _evaluate(CONTRACT, case)
