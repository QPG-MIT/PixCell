"""Shared sacrificial child process for one model-authored program."""

from __future__ import annotations

import os
import resource
import runpy
import sys
import traceback
from pathlib import Path


def _apply_limits() -> None:
    cpu_seconds = int(os.environ.get("PIXCELL_EVAL_CPU_SECONDS", "18"))
    file_bytes = int(os.environ.get("PIXCELL_EVAL_FILE_BYTES", str(16 * 1024 * 1024)))
    open_files = int(os.environ.get("PIXCELL_EVAL_OPEN_FILES", "128"))
    for kind, limits in (
        (resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1)),
        (resource.RLIMIT_FSIZE, (file_bytes, file_bytes)),
        (resource.RLIMIT_NOFILE, (open_files, open_files)),
    ):
        try:
            resource.setrlimit(kind, limits)
        except (OSError, ValueError):
            pass


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
