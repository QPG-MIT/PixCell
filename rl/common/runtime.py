"""Pinned RL runtime validation shared by training and evaluation."""

from __future__ import annotations

import importlib.metadata
import json
import sys
from pathlib import Path
from typing import Any


def validate_runtime_stack(repo_root: Path) -> dict[str, Any]:
    """Return the observed stack only when it matches ``rl/stack.json``."""

    root = repo_root.expanduser().resolve(strict=True)
    expected = json.loads((root / "rl/stack.json").read_text(encoding="utf-8"))
    observed_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    if observed_python != expected["python_major_minor"]:
        raise RuntimeError(
            f"Python {observed_python}, expected {expected['python_major_minor']}"
        )
    observed: dict[str, str] = {}
    for package, expected_version in expected["packages"].items():
        actual = importlib.metadata.version(package)
        observed[package] = actual
        if actual != expected_version:
            raise RuntimeError(
                f"{package}=={actual}, expected {expected_version}"
            )
    return {
        "python": sys.version.split()[0],
        "packages": observed,
        "tinker_cookbook_commit": expected["tinker_cookbook_commit"],
    }
