"""Track A paid-launch guardrails shared by the Tinker entrypoints."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from rl.common.isolation import require_execution_boundary


def bind_execution_boundary(
    resolved_launch: Mapping[str, object],
) -> dict[str, object]:
    """Bind paid program execution to one immutable local sandbox image."""

    binding = dict(resolved_launch)
    if binding.get("kind") not in {"rl", "evaluation"}:
        return binding
    boundary = require_execution_boundary()
    binding["candidate_sandbox"] = {
        "runtime_path": str(boundary.runtime_path),
        "daemon_endpoint": boundary.daemon_endpoint,
        "image_ref": boundary.image_ref,
        "image_id": boundary.image_id,
        "workspace_root": str(boundary.workspace_root),
    }
    return binding


def run_launch_preflight(
    repo_root: Path,
    *,
    resolved_launch: Mapping[str, object],
) -> None:
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
            "--dataset-root",
            str(resolved_launch["dataset_root"]),
            "--config",
            str(resolved_launch["config_path"]),
            "--resolved-launch-json",
            json.dumps(
                dict(resolved_launch),
                sort_keys=True,
                separators=(",", ":"),
            ),
        ],
        cwd=repo_root,
        env=environment,
        check=True,
    )
