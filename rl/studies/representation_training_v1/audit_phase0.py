#!/usr/bin/env python3
"""Run every initial training preflight without credentials or model spend."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .preflight import stage_preflight
from .protocol import (
    INITIAL_STAGE_IDS,
    load_protocol,
    repository_root,
    stage_spec,
    validate_source_sha,
)


def run_audit(
    *,
    repo_root: Path,
    expected_source_sha: str | None = None,
) -> dict[str, Any]:
    root = repo_root.expanduser().resolve(strict=True)
    protocol = load_protocol(
        root,
        require_committed=expected_source_sha is not None,
    )
    source_git_sha = (
        validate_source_sha(root, expected_source_sha)
        if expected_source_sha is not None
        else None
    )
    reports: dict[str, Any] = {}
    for stage_id in INITIAL_STAGE_IDS:
        stage = stage_spec(protocol, stage_id)
        wave = min(
            stage.waves,
            key=lambda name: int(stage.waves[name]["max_steps"]),
        )
        reports[stage_id] = stage_preflight(
            repo_root=root,
            protocol=protocol,
            stage=stage,
            wave_name=wave,
            require_sandbox=stage.kind == "rl",
        )
    return {
        "schema_version": "pixcell-representation-training-phase0-audit-v1",
        "study_id": protocol["study_id"],
        "source_git_sha": source_git_sha,
        "model_client_created": False,
        "paid_request_made": False,
        "initial_stages": reports,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, default=repository_root())
    result.add_argument("--expected-source-sha")
    return result


def main() -> None:
    args = parser().parse_args()
    print(
        json.dumps(
            run_audit(
                repo_root=args.repo_root,
                expected_source_sha=args.expected_source_sha,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
