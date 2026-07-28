#!/usr/bin/env python3
"""Approve the exact historical L0-SFT receipt for the current L1-RL smoke."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .promotion import (
    APPROVAL_CONFIRMATION_TOKEN,
    record_parent_receipt_transition_approval,
)
from .protocol import repository_root


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--replicate", default="r0")
    result.add_argument("--expected-source-sha", required=True)
    result.add_argument(
        "--approve-changed-path",
        action="append",
        required=True,
        dest="approved_change_paths",
        help=(
            "one exact path in the historical-parent-to-current committed diff; "
            "repeat once for every changed path"
        ),
    )
    result.add_argument(
        "--confirm-approval",
        default="",
        help=f"must be exactly {APPROVAL_CONFIRMATION_TOKEN}",
    )
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
        raise SystemExit("set PIXCELL_TRAINING_ROOT or pass --external-root outside Git")
    result = record_parent_receipt_transition_approval(
        repo_root=repository_root(),
        external_root=args.external_root,
        stage_id="qwen-l0-rl-l1",
        wave_name="smoke",
        replicate_id=args.replicate,
        expected_source_sha=args.expected_source_sha,
        approved_change_paths=args.approved_change_paths,
        confirmation=args.confirm_approval,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
