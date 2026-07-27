"""RC-02 contract data bound to the shared verdict engine."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rclib import Contract, Verdict, evaluate as _evaluate, verdict as _verdict

CONTRACT = Contract(
    slug="rc-02-process-faithful-retargeting",
    gates=(
        "T1_one_program_four_stacks",
        "T2_explicit_3d_geometry",
        "T3_preregistered_gates_met",
        "T4_audits_recomputed",
        "T5_control_and_reproduction",
    ),
    evidence_keys=frozenset(
        {
            "program_source",
            "named_parameters",
            "stack_manifests",
            "preregistration_commit",
            "generated_geometry",
            "simulation_inputs",
            "field_records",
            "sparameter_results",
            "mesh_audit",
            "conservation_audit",
            "control_results",
            "task_identifiers",
            "cost_ledger",
            "rerun_script",
        }
    ),
)


def verdict(report: dict) -> Verdict:
    return _verdict(CONTRACT, report)


def evaluate(case: dict) -> dict:
    return _evaluate(CONTRACT, case)
