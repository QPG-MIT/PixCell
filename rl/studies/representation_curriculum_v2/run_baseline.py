#!/usr/bin/env python3
"""Run one frozen, resumable v2 direct-policy baseline wave."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from rl.evaluation.runner import run_baseline


REPO_ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_FILE = Path(__file__).with_name("protocol.json")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--hypothesis",
        required=True,
        choices=("RC-H05", "RC-H06"),
    )
    result.add_argument("--wave", required=True, choices=("smoke", "complete"))
    result.add_argument("--expected-source-sha", required=True)
    result.add_argument("--confirm-spend", default="")
    result.add_argument(
        "--external-root",
        type=Path,
        default=(
            Path(os.environ["PIXCELL_STUDY_ROOT"])
            if os.environ.get("PIXCELL_STUDY_ROOT")
            else None
        ),
    )
    return result


def main() -> None:
    args = parser().parse_args()
    if args.external_root is None:
        raise SystemExit(
            "set PIXCELL_STUDY_ROOT or provide --external-root outside the repository"
        )
    report = asyncio.run(
        run_baseline(
            repo_root=REPO_ROOT,
            protocol_file=PROTOCOL_FILE,
            hypothesis_id=args.hypothesis,
            wave_name=args.wave,
            expected_source_sha=args.expected_source_sha,
            external_root=args.external_root,
            confirmation=args.confirm_spend,
        )
    )
    print(json.dumps(report["summaries"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
