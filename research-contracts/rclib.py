"""Shared pure verdict engine for the PixCell research contracts.

Each contract's ``contract_definitions.py`` declares its data (gate ids,
required evidence keys) and binds it to :func:`verdict`. The engine is
deterministic and side-effect free: no network, no subprocess, no
filesystem access, no randomness. Contract-specific content is data this
module operates on, never a clause.

The report graded here is issuer-recomputed. Claimant-reported results
never enter it; the reviewer re-runs the declared checks from the
retained evidence and fills ``gates`` from those reruns.
"""

from __future__ import annotations

from dataclasses import dataclass

NOT_SCORED = "not_scored"
REJECTED = "rejected"
SETTLED = "settled"

GATE_PASS = "pass"

# Failure codes that invalidate the grading run itself. A run that hits
# one of these is regraded; it is never recorded against the submission.
INFRASTRUCTURE_FAILURES = frozenset(
    {
        "verifier_crash",
        "service_outage",
        "reference_artifact_corrupt",
        "evaluator_timeout",
        "environment_mismatch",
    }
)

# Failure codes attributable to the submission. Any failure code that is
# not an infrastructure failure counts as one of these.
SUBMISSION_FAILURES = frozenset(
    {
        "syntax_error",
        "purity_violation",
        "runtime_failure",
        "missing_artifact",
        "non_reproducible",
    }
)


@dataclass(frozen=True)
class Contract:
    """The data of one research contract: identity, gates, evidence keys."""

    slug: str
    gates: tuple[str, ...]
    evidence_keys: frozenset[str]


@dataclass(frozen=True)
class Verdict:
    state: str
    failing_gates: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    failure_codes: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "state": self.state,
            "failing_gates": list(self.failing_gates),
            "missing_evidence": list(self.missing_evidence),
            "failure_codes": list(self.failure_codes),
        }


def verdict(contract: Contract, report: dict) -> Verdict:
    """Apply the decision rule to an issuer-recomputed grading report.

    ``report`` has three keys:

    - ``evidence``: mapping of retained-artifact key to path or URI.
    - ``gates``: mapping of gate id to ``"pass"`` or ``"fail"``, filled
      only from issuer recomputation.
    - ``failures``: failure codes observed while grading.

    Infrastructure failures take precedence: a broken grading run says
    nothing about the submission, so nothing else observed in that run
    is trusted. Submission failures reject. Otherwise the verdict is
    settled only when every declared gate passed and every declared
    evidence key is present. Unknown gate ids in the report are ignored;
    absent gates count as failing.
    """
    failures = tuple(sorted(set(report.get("failures", ()))))
    infra = tuple(f for f in failures if f in INFRASTRUCTURE_FAILURES)
    if infra:
        return Verdict(NOT_SCORED, failure_codes=infra)

    submission = tuple(f for f in failures if f not in INFRASTRUCTURE_FAILURES)
    evidence = report.get("evidence", {})
    present = {k for k, v in evidence.items() if isinstance(v, str) and v.strip()}
    missing = tuple(sorted(contract.evidence_keys - present))
    gates = report.get("gates", {})
    failing = tuple(g for g in contract.gates if gates.get(g) != GATE_PASS)

    if submission or missing or failing:
        return Verdict(
            REJECTED,
            failing_gates=failing,
            missing_evidence=missing,
            failure_codes=submission,
        )
    return Verdict(SETTLED)


def evaluate(contract: Contract, case: dict) -> dict:
    """Run one ``eval.yml`` golden case through the verdict engine."""
    return verdict(contract, case.get("input", {}).get("report", {})).as_dict()
