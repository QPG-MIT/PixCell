"""Shared sacrificial child process for one model-authored program."""

from __future__ import annotations

import os
import resource
import runpy
import sys
import traceback
from pathlib import Path


def _set_limit(
    kind: int,
    requested: tuple[int, int],
    *,
    required: bool,
) -> None:
    try:
        current_soft, current_hard = resource.getrlimit(kind)
        requested_soft, requested_hard = requested
        hard = (
            requested_hard
            if current_hard == resource.RLIM_INFINITY
            else min(requested_hard, current_hard)
        )
        soft = min(requested_soft, hard)
        resource.setrlimit(kind, (soft, hard))
    except (OSError, ValueError) as exc:
        if required:
            raise RuntimeError(f"failed to install required rlimit {kind}") from exc


def _apply_limits() -> None:
    cpu_seconds = int(os.environ.get("PIXCELL_EVAL_CPU_SECONDS", "18"))
    file_bytes = int(os.environ.get("PIXCELL_EVAL_FILE_BYTES", str(16 * 1024 * 1024)))
    open_files = int(os.environ.get("PIXCELL_EVAL_OPEN_FILES", "128"))
    address_bytes = int(
        os.environ.get("PIXCELL_EVAL_ADDRESS_BYTES", str(4 * 1024 * 1024 * 1024))
    )
    process_count = int(os.environ.get("PIXCELL_EVAL_PROCESS_COUNT", "32"))
    required = os.environ.get("PIXCELL_EVAL_REQUIRE_LIMITS") == "1"
    limits_to_apply = [
        (resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1)),
        (resource.RLIMIT_FSIZE, (file_bytes, file_bytes)),
        (resource.RLIMIT_NOFILE, (open_files, open_files)),
        (resource.RLIMIT_AS, (address_bytes, address_bytes)),
        (resource.RLIMIT_CORE, (0, 0)),
    ]
    if required:
        limits_to_apply.append(
            (resource.RLIMIT_NPROC, (process_count, process_count))
        )
    for kind, limits in limits_to_apply:
        _set_limit(kind, limits, required=required)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: execute.py DEVICE_PY", file=sys.stderr)
        return 64
    _apply_limits()
    script = Path(sys.argv[1]).resolve()
    try:
        runpy.run_path(str(script), run_name="__main__")
    except BaseException as exc:
        traceback.print_exception(type(exc), exc, exc.__traceback__, limit=8)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
