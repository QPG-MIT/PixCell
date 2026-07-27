"""The research-contracts tree honors its own discipline.

Structural invariants (frontmatter, gates, registry, hygiene) plus the
verdict engine's golden cases from each contract's eval.yml. Red gates
are strict xfail: they must fail until an accepted submission's
evidence exists, and a green gate without evidence is a validation
error, never a passing test.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest
import yaml

RC_ROOT = Path(__file__).resolve().parents[1] / "research-contracts"

GATE_OPEN_STATUSES = {"red", "xfail", "blocked", "manual"}
GATE_GREEN_STATUSES = {"green", "pass"}


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validate = _load_module("rc_validate", RC_ROOT / "validate.py")


def _contract_dirs() -> list[Path]:
    return validate.contract_dirs()


def _definitions(wc_dir: Path):
    return _load_module(
        f"rc_defs_{wc_dir.name.replace('-', '_')}", wc_dir / "contract_definitions.py"
    )


# ── Structural validation ──────────────────────────────────────────────


def test_tree_passes_structural_validation():
    errors = []
    for wc_dir in _contract_dirs():
        errors.extend(validate.validate_contract_dir(wc_dir))
    errors.extend(validate.validate_registry(_contract_dirs()))
    assert errors == []


def test_four_contracts_exist():
    assert [d.name for d in _contract_dirs()] == [
        "rc-01-shape-aware-verification",
        "rc-02-process-faithful-retargeting",
        "rc-03-representation-scale-dataset",
        "rc-04-smallest-qualifying-open-model",
    ]


def test_gate_ids_match_contract_definitions():
    for wc_dir in _contract_dirs():
        config = yaml.safe_load((wc_dir / "config.yaml").read_text(encoding="utf-8"))
        config_gates = [g["id"] for g in config["governing_gates"]]
        assert config_gates == list(_definitions(wc_dir).CONTRACT.gates), wc_dir.name


def test_every_evidence_key_is_consumed_by_a_gate():
    """The manifest is load-bearing: each gate names what it consumes, and
    together the gates consume exactly the declared evidence keys."""
    for wc_dir in _contract_dirs():
        config = yaml.safe_load((wc_dir / "config.yaml").read_text(encoding="utf-8"))
        contract = _definitions(wc_dir).CONTRACT
        consumed: set[str] = set()
        for gate in config["governing_gates"]:
            keys = set(gate.get("consumes", []))
            assert keys, f"{wc_dir.name}:{gate['id']} consumes nothing"
            unknown = keys - contract.evidence_keys
            assert not unknown, f"{wc_dir.name}:{gate['id']} consumes undeclared {unknown}"
            consumed |= keys
        assert consumed == contract.evidence_keys, (
            f"{wc_dir.name}: unconsumed evidence {contract.evidence_keys - consumed}"
        )


# ── Acceptance gates: strict xfail while red ───────────────────────────


def _gate_params():
    params = []
    for wc_dir in _contract_dirs():
        config = yaml.safe_load((wc_dir / "config.yaml").read_text(encoding="utf-8"))
        for gate in config["governing_gates"]:
            marks = ()
            if gate["status"] in GATE_OPEN_STATUSES:
                marks = (
                    pytest.mark.xfail(
                        strict=True,
                        reason=f"RED: {wc_dir.name} gate {gate['id']} has no accepted evidence",
                    ),
                )
            params.append(pytest.param(gate, id=f"{wc_dir.name}:{gate['id']}", marks=marks))
    return params


@pytest.mark.parametrize("gate", _gate_params())
def test_acceptance_gate(gate: dict):
    assert gate["status"] in GATE_GREEN_STATUSES
    assert gate["evidence"]


# ── Verdict engine: golden cases and decision-rule invariants ──────────


def _eval_cases():
    params = []
    for wc_dir in _contract_dirs():
        eval_data = yaml.safe_load((wc_dir / "eval.yml").read_text(encoding="utf-8"))
        for case in eval_data["cases"]:
            params.append(pytest.param(wc_dir, case, id=f"{wc_dir.name}:{case['name']}"))
    return params


@pytest.mark.parametrize("wc_dir, case", _eval_cases())
def test_eval_golden_case(wc_dir: Path, case: dict):
    result = _definitions(wc_dir).evaluate(case)
    for key, expected in case["expected"].items():
        assert result[key] == expected, f"{case['name']}: {key}"


def test_infrastructure_failure_precedes_submission_failure():
    defs = _definitions(_contract_dirs()[0])
    result = defs.verdict({"failures": ["verifier_crash", "syntax_error"]})
    assert result.state == "not_scored"
    assert result.failure_codes == ("verifier_crash",)


def test_unknown_failure_codes_count_against_the_submission():
    defs = _definitions(_contract_dirs()[0])
    result = defs.verdict({"failures": ["some_new_failure_mode"]})
    assert result.state == "rejected"


def test_settlement_requires_every_gate_and_every_evidence_key():
    for wc_dir in _contract_dirs():
        defs = _definitions(wc_dir)
        contract = defs.CONTRACT
        complete = {
            "evidence": {k: f"evidence/{k}" for k in contract.evidence_keys},
            "gates": {g: "pass" for g in contract.gates},
            "failures": [],
        }
        assert defs.verdict(complete).state == "settled", wc_dir.name
        for gate in contract.gates:
            broken = dict(complete, gates={**complete["gates"], gate: "fail"})
            assert defs.verdict(broken).state == "rejected", f"{wc_dir.name}:{gate}"


def test_empty_evidence_values_count_as_missing():
    """A manifest key pointing at nothing is not retained evidence."""
    defs = _definitions(_contract_dirs()[0])
    contract = defs.CONTRACT
    hollow = {
        "evidence": {k: "" for k in contract.evidence_keys},
        "gates": {g: "pass" for g in contract.gates},
        "failures": [],
    }
    result = defs.verdict(hollow)
    assert result.state == "rejected"
    assert set(result.missing_evidence) == contract.evidence_keys


def test_claimant_asserted_verdict_is_ignored():
    """A report carrying nothing but a self-declared success settles nothing."""
    for wc_dir in _contract_dirs():
        defs = _definitions(wc_dir)
        result = defs.verdict({"state": "settled", "evidence": {}, "gates": {}, "failures": []})
        assert result.state == "rejected", wc_dir.name


# ── Shareability hygiene ───────────────────────────────────────────────

SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,})\b"),
    re.compile(r"BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY"),
    re.compile(r"Bearer [A-Za-z0-9_\-.]{16,}"),
)
LOCAL_PATH_PATTERN = re.compile(r"/Users/[A-Za-z0-9._-]+/")


def _tree_text_files():
    return [p for p in RC_ROOT.rglob("*") if p.is_file() and p.suffix in {".md", ".py", ".yml", ".yaml", ".json"}]


def test_no_secret_literals_in_the_public_tree():
    for path in _tree_text_files():
        text = path.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            assert not pattern.search(text), f"{path} matches {pattern.pattern}"


def test_no_local_author_paths_in_the_public_tree():
    for path in _tree_text_files():
        assert not LOCAL_PATH_PATTERN.search(
            path.read_text(encoding="utf-8")
        ), f"{path} embeds a local workstation path"
