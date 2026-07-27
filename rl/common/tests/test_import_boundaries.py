from __future__ import annotations

import ast
from pathlib import Path


COMMON_ROOT = Path(__file__).resolve().parents[1]
TRACK_SPECIFIC_ROOTS = (
    "rl.track_a",
    "tinker",
    "tinker_cookbook",
    "chz",
)


def test_common_has_no_track_or_training_runtime_imports():
    violations: list[str] = []
    for path in sorted(COMMON_ROOT.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            for name in names:
                if name.startswith(TRACK_SPECIFIC_ROOTS):
                    violations.append(f"{path.name}:{node.lineno}: {name}")
    assert not violations
