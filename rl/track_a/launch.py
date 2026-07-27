"""Track A paid-launch guardrails shared by the Tinker entrypoints."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def run_launch_preflight(repo_root: Path) -> None:
    """Run the complete local gate before any Tinker client can be created."""

    environment = dict(os.environ)
    roots = [str(repo_root / "src"), str(repo_root)]
    existing = environment.get("PYTHONPATH")
    if existing:
        roots.append(existing)
    environment["PYTHONPATH"] = os.pathsep.join(roots)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "rl.track_a.preflight",
            "--execute-ground-truth",
            "5",
            "--tokenize-sft",
            "--require-clean",
        ],
        cwd=repo_root,
        env=environment,
        check=True,
    )
