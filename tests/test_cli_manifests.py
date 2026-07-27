"""CLI manifest, optimize-discovery, simulate, and promotion contracts.

Extracted from the lab's tests/web/test_web_core.py: these four tests exercise
only ported engine code (homi.cli, homi.conductor, homi.flex_integration) and
none of the excluded homi.web module.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

def test_optimize_discovers_web_target_and_recorded_calibration(tmp_path):
    from homi.cli import _discover_optimize_inputs

    project = tmp_path / "projects" / "web_deadbeef"
    output = project / "output"
    output.mkdir(parents=True)
    script = output / "best.py"
    script.write_text("length = 10.0\n")
    target = project / "device_bw.png"
    target.write_bytes(b"frozen-mask")
    footprint = project / "footprint.json"
    footprint.write_text('{"footprint_um": [10, 2]}')

    old = output / "recreation_old"
    new = output / "recreation_agent"
    old.mkdir()
    new.mkdir()
    (old / "component.png").write_bytes(b"old-mask")
    (new / "component.png").write_bytes(b"frozen-mask")
    old_cal = old / "calibration.json"
    new_cal = new / "calibration.json"
    old_cal.write_text('{"scale_px_per_um": [1, 1]}')
    new_cal.write_text('{"scale_px_per_um": [2, 2]}')
    os.utime(old_cal, ns=(1_000_000_000, 1_000_000_000))
    os.utime(new_cal, ns=(2_000_000_000, 2_000_000_000))

    found_target, found_calibration, found_footprint = _discover_optimize_inputs(script)
    assert found_target == target
    assert found_calibration == new_cal.resolve()
    assert found_footprint == footprint

    target.write_bytes(b"replacement-mask")
    _, stale_calibration, _ = _discover_optimize_inputs(script)
    assert stale_calibration is None


def test_stage_manifest_write_and_merge(tmp_path):
    from types import SimpleNamespace

    from homi.cli import (
        _manifest_project_for_args,
        _manifest_stage_for_args,
        _write_stage_manifest,
    )

    _write_stage_manifest(tmp_path, "generate", status="queued", pid=123)
    _write_stage_manifest(tmp_path, "generate", status="running", pid=456)
    m = json.loads((tmp_path / "output" / "stage_generate.json").read_text())
    assert m["status"] == "running" and m["pid"] == 456 and m["stage"] == "generate"

    # parsed args, never argv guessing — option-first orderings included
    assert _manifest_project_for_args(SimpleNamespace(
        command="generate", project_dir=Path("projects/web_x"))) == Path("projects/web_x")
    assert _manifest_project_for_args(SimpleNamespace(
        command="extract", output=Path("projects/web_y"))) == Path("projects/web_y")
    assert _manifest_project_for_args(SimpleNamespace(
        command="optimize", script_path=Path("projects/web_y/output/best.py")
    )) == Path("projects/web_y")
    assert _manifest_project_for_args(SimpleNamespace(
        command="retarget", script_path=Path("projects/web_y/output/best.py")
    )) == Path("projects/web_y")
    assert _manifest_project_for_args(SimpleNamespace(
        command="simulate", gds_path=Path("projects/web_y/output/best.gds")
    )) == Path("projects/web_y")
    assert _manifest_stage_for_args(SimpleNamespace(command="optimize")) == "polish"
    assert _manifest_stage_for_args(SimpleNamespace(command="retarget")) == "retarget"
    assert _manifest_stage_for_args(SimpleNamespace(command="simulate")) == "simulate"
    assert _manifest_project_for_args(SimpleNamespace(command="doctor")) is None
    assert _manifest_project_for_args(None) is None


def test_simulate_returns_truthful_manifest_exit_status(tmp_path, monkeypatch):
    """A failed draft upload must not become a completed simulate stage."""
    from types import SimpleNamespace

    import gdsfactory as gf

    from homi import flex_integration
    from homi.cli import cmd_simulate

    gds = tmp_path / "best.gds"
    gds.write_bytes(b"test fixture")
    args = SimpleNamespace(
        command="simulate", gds_path=gds, material="Silicon (SOI)", thickness=220,
        wavelength=1.55)
    monkeypatch.setenv("TIDY3D_API_KEY", "test-only")
    monkeypatch.setattr(flex_integration, "is_tidy3d_available", lambda: True)
    monkeypatch.setattr(gf, "import_gds", lambda _path: object())

    monkeypatch.setattr(
        flex_integration, "create_and_upload_simulation",
        lambda *_args, **_kwargs: {})
    assert cmd_simulate(args) == 1

    monkeypatch.setattr(
        flex_integration, "create_and_upload_simulation",
        lambda *_args, **_kwargs: {
            "task_id": "draft-1", "web_url": "https://example.test/draft-1",
            "estimated_cost": 0.31,
        })
    assert cmd_simulate(args) == 0
    draft = json.loads((tmp_path / "output" / "simulation" / "draft.json").read_text())
    assert draft == {
        "task_id": "draft-1",
        "url": "https://example.test/draft-1",
        "est_credits": 0.31,
        "state": "awaiting_human_start",
    }


# ---------- promotion strictness (the restored gate) ----------


def test_gate_and_promote_strict_refusals(tmp_path, monkeypatch):
    from homi.conductor import promote as promote_mod
    from homi.conductor.gate import GateResult

    workdir = tmp_path / "work"
    workdir.mkdir()
    (workdir / "device.py").write_text("x = 1")
    (workdir / "component.png").write_bytes(b"png")
    (workdir / "calibration.json").write_text("{}")
    (workdir / "cell.gds").write_bytes(b"gds")

    def fake_verify(gds, target, calibration, script, claimed_iou=None, knob=None):
        matches = None if claimed_iou is None else True
        knob_res = {"ok": True, "param": knob[0]} if knob else None
        return GateResult(iou=0.91, metrics={"IoU": 0.91},
                          iou_matches_claim=matches, purity=[],
                          knob=knob_res, verified=True)

    monkeypatch.setattr(promote_mod, "verify_cell", fake_verify)

    # no submission → protocol-verified but NOT promoted (strict)
    out = promote_mod.gate_and_promote(tmp_path, workdir)
    assert out.gate.verified and not out.promoted
    assert any("strict" in r for r in out.reasons)
    g = json.loads((tmp_path / "output" / "gate.json").read_text())
    assert g["promoted"] is False and g["claim"] == "missing"
    assert not (tmp_path / "output" / "best.py").exists()

    # malformed submission behaves as missing, never crashes
    (workdir / "submission.json").write_text('["not", "an", "object"]')
    out = promote_mod.gate_and_promote(tmp_path, workdir)
    assert not out.promoted

    # full submission → promoted, atomically, with the record written first
    (workdir / "submission.json").write_text(json.dumps(
        {"claimed_iou": 0.91, "knob": {"name": "gap", "width_um": 0.5}}))
    out = promote_mod.gate_and_promote(tmp_path, workdir)
    assert out.promoted and out.claim_status == "ok" and out.knob_status == "ok"
    assert (tmp_path / "output" / "best.py").exists()
    assert (tmp_path / "output" / "best.gds").exists()
    g = json.loads((tmp_path / "output" / "gate.json").read_text())
    assert g["promoted"] is True

