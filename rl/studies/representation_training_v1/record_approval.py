#!/usr/bin/env python3
"""Record one reviewed checkpoint report as an immutable wave approval."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .promotion import (
    APPROVAL_CONFIRMATION_TOKEN,
    record_wave_approval,
)
from .protocol import repository_root


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--stage", required=True)
    result.add_argument("--wave", required=True)
    result.add_argument("--replicate", default="r0")
    result.add_argument("--evaluation-stage", required=True)
    result.add_argument("--evaluation-wave", required=True)
    result.add_argument("--evaluation-checkpoint", required=True)
    result.add_argument("--evaluation-report-record-sha256", required=True)
    result.add_argument(
        "--entry-baseline-report-record-sha256",
        default=None,
        help=(
            "second report required by the pure-base L1-L4 transition gate: "
            "the exact parent checkpoint evaluated on the incoming level"
        ),
    )
    result.add_argument("--expected-source-sha", required=True)
    result.add_argument(
        "--evidence-source-sha",
        default=None,
        help=(
            "exact ancestor commit that produced the evaluation report; "
            "omit for the unchanged same-source v1 approval path"
        ),
    )
    result.add_argument(
        "--approve-changed-path",
        action="append",
        default=None,
        dest="approved_change_paths",
        help=(
            "one exact producer-to-consumer changed path reviewed for a v2 "
            "transition; repeat for every changed path and omit for v1"
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
    result = record_wave_approval(
        repo_root=repository_root(),
        external_root=args.external_root,
        stage_id=args.stage,
        wave_name=args.wave,
        replicate_id=args.replicate,
        evaluation_stage_id=args.evaluation_stage,
        evaluation_wave=args.evaluation_wave,
        evaluation_checkpoint_name=args.evaluation_checkpoint,
        evaluation_report_record_sha256=(args.evaluation_report_record_sha256),
        entry_baseline_report_record_sha256=(
            args.entry_baseline_report_record_sha256
        ),
        expected_source_sha=args.expected_source_sha,
        evidence_source_sha=args.evidence_source_sha,
        approved_change_paths=args.approved_change_paths,
        confirmation=args.confirm_approval,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
