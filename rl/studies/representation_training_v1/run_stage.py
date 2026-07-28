#!/usr/bin/env python3
"""Run one sealed representation-training stage or continuation wave."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from .launcher import run_training_stage
from .protocol import repository_root


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--stage", required=True)
    result.add_argument("--wave", required=True)
    result.add_argument("--replicate", default="r0")
    result.add_argument("--expected-source-sha", required=True)
    result.add_argument("--confirm-spend", default="")
    result.add_argument(
        "--external-root",
        type=Path,
        default=(
            Path(os.environ["PIXCELL_TRAINING_ROOT"])
            if os.environ.get("PIXCELL_TRAINING_ROOT")
            else None
        ),
    )
    return result


def main() -> None:
    args = parser().parse_args()
    if args.external_root is None:
        raise SystemExit(
            "set PIXCELL_TRAINING_ROOT or pass --external-root outside Git"
        )
    report = asyncio.run(
        run_training_stage(
            repo_root=repository_root(),
            stage_id=args.stage,
            wave_name=args.wave,
            replicate_id=args.replicate,
            expected_source_sha=args.expected_source_sha,
            external_root=args.external_root,
            confirmation=args.confirm_spend,
        )
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
