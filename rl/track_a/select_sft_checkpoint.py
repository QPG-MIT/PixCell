#!/usr/bin/env python3
"""Select a Track A SFT checkpoint from executable reports, never NLL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rl.track_a.checkpoint_selection import select_sft_checkpoint


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--geometry-reports",
        nargs="+",
        required=True,
        type=Path,
        help="full depth/validation k=1 reports",
    )
    parser.add_argument(
        "--behavioral-reports",
        nargs="+",
        required=True,
        type=Path,
        help="paired small balanced unmastered-level G4 reports",
    )
    args = parser.parse_args()
    geometry = [
        (str(path), json.loads(path.read_text(encoding="utf-8")))
        for path in args.geometry_reports
    ]
    behavior = [
        (str(path), json.loads(path.read_text(encoding="utf-8")))
        for path in args.behavioral_reports
    ]
    try:
        result = select_sft_checkpoint(geometry, behavior)
    except (KeyError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
