from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
PREFLIGHT_PATH = REPO_ROOT / "rl" / "track_a" / "preflight.py"


def _preflight_module():
    spec = importlib.util.spec_from_file_location(
        "pixcell_track_a_preflight_test",
        PREFLIGHT_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_paid_launch_clean_gate_includes_untracked_files(monkeypatch, tmp_path):
    module = _preflight_module()
    calls: list[list[str]] = []

    def fake_check_output(command, **_kwargs):
        calls.append(command)
        if command[:2] == ["git", "rev-parse"]:
            return "abc123\n"
        return "?? rl/new_training_code.py\n"

    monkeypatch.setattr(module.subprocess, "check_output", fake_check_output)

    state = module._git_state(tmp_path, require_clean=False)
    assert state == {"head": "abc123", "clean": False}
    assert ["git", "status", "--porcelain", "--untracked-files=all"] in calls

    with pytest.raises(RuntimeError, match="including untracked files"):
        module._git_state(tmp_path, require_clean=True)
