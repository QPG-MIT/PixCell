#!/usr/bin/env python3
"""Structural validation for the PixCell research-contracts tree.

Checks the invariants the registry depends on. Exit code 0 means every
check passed. CI runs the same checks through
``tests/test_research_contracts.py``; this script is the standalone form a
reviewer re-runs.

Usage:
    python research-contracts/validate.py
"""

from __future__ import annotations

import datetime
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent

VALID_STATUSES = {"draft", "red", "open", "in_progress", "green", "certified", "deprecated"}
VALID_CATEGORIES = {"physics", "infrastructure", "process", "meta", "synthesis", "uncategorized"}
GATE_OPEN_STATUSES = {"red", "xfail", "blocked", "manual"}
GATE_GREEN_STATUSES = {"green", "pass"}

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

REQUIRED_FILES = ("SPEC.md", "config.yaml", "contract_definitions.py", "eval.yml")


def parse_frontmatter(spec_path: Path) -> dict | None:
    lines = spec_path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = lines[1:].index("---") + 1
    except ValueError:
        return None
    data = yaml.safe_load("\n".join(lines[1:end]))
    return data if isinstance(data, dict) else None


def contract_dirs() -> list[Path]:
    return sorted(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("rc-"))


def validate_contract_dir(wc_dir: Path) -> list[str]:
    errors: list[str] = []
    name = wc_dir.name

    for req in REQUIRED_FILES:
        if not (wc_dir / req).exists():
            errors.append(f"{name}: missing required file {req}")

    spec_path = wc_dir / "SPEC.md"
    fm = parse_frontmatter(spec_path) if spec_path.exists() else None
    if fm is None:
        errors.append(f"{name}: SPEC.md has no YAML frontmatter")
    else:
        for key in ("uuid", "slug", "version", "status", "created"):
            if key not in fm:
                errors.append(f"{name}: frontmatter missing {key}")
        if "uuid" in fm and not UUID_RE.match(str(fm["uuid"])):
            errors.append(f"{name}: uuid is not a UUID: {fm['uuid']!r}")
        if "slug" in fm and (not SLUG_RE.match(str(fm["slug"])) or fm["slug"] != name):
            errors.append(f"{name}: slug must equal the directory name, got {fm['slug']!r}")
        if "version" in fm and not SEMVER_RE.match(str(fm["version"])):
            errors.append(f"{name}: version is not semver: {fm['version']!r}")
        if "status" in fm and fm["status"] not in VALID_STATUSES:
            errors.append(f"{name}: status {fm['status']!r} not in {sorted(VALID_STATUSES)}")
        if "created" in fm and not isinstance(fm["created"], datetime.date):
            errors.append(f"{name}: created is not an ISO date: {fm['created']!r}")
        if fm.get("category", "uncategorized") not in VALID_CATEGORIES:
            errors.append(f"{name}: category {fm['category']!r} not in {sorted(VALID_CATEGORIES)}")

    config_path = wc_dir / "config.yaml"
    if config_path.exists():
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        contract = config.get("contract", {})
        if fm is not None and contract.get("template") != wc_dir.name:
            errors.append(f"{name}: config contract.template must equal the directory name")
        if fm is not None and contract.get("status") != fm.get("status"):
            errors.append(f"{name}: config status disagrees with SPEC frontmatter")
        if contract.get("status") not in VALID_STATUSES:
            errors.append(f"{name}: config status {contract.get('status')!r} invalid")

        gates = config.get("governing_gates", [])
        if not gates:
            errors.append(f"{name}: no governing_gates declared")
        ids = [g.get("id") for g in gates]
        if len(ids) != len(set(ids)):
            errors.append(f"{name}: gate ids are not unique")
        total = sum(float(g.get("weight", 0)) for g in gates)
        if abs(total - 1.0) > 1e-9:
            errors.append(f"{name}: gate weights sum to {total}, expected 1.0")
        for gate in gates:
            status = gate.get("status")
            if status in GATE_GREEN_STATUSES and not gate.get("evidence"):
                errors.append(f"{name}: green gate {gate.get('id')} carries no evidence")
            if status not in GATE_OPEN_STATUSES | GATE_GREEN_STATUSES:
                errors.append(f"{name}: gate {gate.get('id')} has unknown status {status!r}")

        boundaries = config.get("claim_boundaries")
        if not boundaries or "allowed_current_claims" not in boundaries:
            errors.append(f"{name}: claim_boundaries.allowed_current_claims missing")
        if not (config.get("verification", {}) or {}).get("research_contracts"):
            errors.append(f"{name}: verification.research_contracts commands missing")

    defs_path = wc_dir / "contract_definitions.py"
    if defs_path.exists():
        source = defs_path.read_text(encoding="utf-8")
        try:
            compile(source, str(defs_path), "exec")
        except SyntaxError as exc:
            errors.append(f"{name}: contract_definitions.py does not compile: {exc}")
        for forbidden in ("requests", "urllib", "subprocess", "socket", "http"):
            if re.search(rf"^\s*(import|from)\s+{forbidden}\b", source, re.MULTILINE):
                errors.append(f"{name}: contract_definitions.py imports {forbidden}")

    eval_path = wc_dir / "eval.yml"
    if eval_path.exists():
        eval_data = yaml.safe_load(eval_path.read_text(encoding="utf-8"))
        if not isinstance(eval_data.get("version"), int) or eval_data["version"] < 1:
            errors.append(f"{name}: eval.yml version must be an integer >= 1")
        cases = eval_data.get("cases")
        if not isinstance(cases, list):
            errors.append(f"{name}: eval.yml cases must be a list")
        else:
            for case in cases:
                if "name" not in case:
                    errors.append(f"{name}: eval.yml case without a name")

    return errors


def validate_registry(dirs: list[Path]) -> list[str]:
    errors: list[str] = []
    registry_path = ROOT / "registry.json"
    if not registry_path.exists():
        return ["registry.json missing"]
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    entries = {e["slug"]: e for e in registry.get("contracts", [])}

    if set(entries) != {d.name for d in dirs}:
        errors.append(
            f"registry slugs {sorted(entries)} disagree with directories {[d.name for d in dirs]}"
        )
    for slug, entry in entries.items():
        wc_dir = ROOT / slug
        spec_path = ROOT / entry.get("spec", "")
        if not spec_path.exists():
            errors.append(f"registry: {slug} spec path does not exist")
        if not (ROOT / entry.get("config", "")).exists():
            errors.append(f"registry: {slug} config path does not exist")
        if not str(entry.get("contract_id", "")).startswith("contract_"):
            errors.append(f"registry: {slug} contract_id malformed")

        fm = parse_frontmatter(wc_dir / "SPEC.md") if (wc_dir / "SPEC.md").exists() else None
        if fm is not None:
            for key in ("status", "uuid", "version"):
                if entry.get(key) != fm.get(key):
                    errors.append(f"registry: {slug} {key} disagrees with SPEC frontmatter")
        if spec_path.exists():
            import hashlib

            digest = hashlib.sha256(spec_path.read_bytes()).hexdigest()
            if entry.get("spec_sha256") != digest:
                errors.append(
                    f"registry: {slug} spec_sha256 does not match SPEC.md; "
                    "amendments must update the registry hash"
                )

        config_path = wc_dir / "config.yaml"
        if config_path.exists():
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            market = config.get("marketplace", {})
            if entry.get("contract_id") != market.get("contract_id"):
                errors.append(f"registry: {slug} contract_id disagrees with config marketplace")
            if entry.get("settlement") != market.get("settlement"):
                errors.append(f"registry: {slug} settlement disagrees with config marketplace")
            if entry.get("payment_type") != market.get("payment_type"):
                errors.append(f"registry: {slug} payment_type disagrees with config marketplace")
    return errors


def main() -> int:
    dirs = contract_dirs()
    errors: list[str] = []
    if not dirs:
        errors.append("no rc-* contract directories found")
    for wc_dir in dirs:
        errors.extend(validate_contract_dir(wc_dir))
    errors.extend(validate_registry(dirs))

    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1
    print(f"ok: {len(dirs)} contracts valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
