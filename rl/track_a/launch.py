"""Track A paid-launch guardrails shared by the Tinker entrypoints."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from rl.common.isolation import require_execution_boundary


def bind_execution_boundary() -> dict[str, object]:
    """Bind paid program execution to one immutable local sandbox image."""

    boundary = require_execution_boundary()
    return {
        "runtime_path": str(boundary.runtime_path),
        "daemon_endpoint": boundary.daemon_endpoint,
        "image_ref": boundary.image_ref,
        "image_id": boundary.image_id,
        "workspace_root": str(boundary.workspace_root),
    }


def run_launch_preflight(
    repo_root: Path,
    *,
    dataset_root: Path,
    model_name: str,
    renderer_name: str,
    require_sandbox: bool,
    tokenize_sft: bool = False,
    sft_levels: str = "",
    max_length: int = 6144,
    max_image: int = 1440,
) -> None:
    """Run the complete local gate before any Tinker client can be created."""

    environment = dict(os.environ)
    roots = [str(repo_root / "src"), str(repo_root)]
    existing = environment.get("PYTHONPATH")
    if existing:
        roots.append(existing)
    environment["PYTHONPATH"] = os.pathsep.join(roots)
    command = [
        sys.executable,
        "-m",
        "rl.track_a.preflight",
        "--execute-ground-truth",
        "5",
        "--require-clean",
        "--dataset-root",
        str(dataset_root),
        "--model-name",
        model_name,
        "--renderer-name",
        renderer_name,
        "--max-length",
        str(max_length),
        "--max-image",
        str(max_image),
    ]
    if require_sandbox:
        command.append("--require-sandbox")
    if tokenize_sft:
        command.append("--tokenize-sft")
    if sft_levels:
        command.extend(["--sft-levels", sft_levels])
    subprocess.run(command, cwd=repo_root, env=environment, check=True)
