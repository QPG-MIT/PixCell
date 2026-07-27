"""Tests for homi.sweep_evaluation — no cloud access anywhere."""

import json

import pytest

from homi import sweep_evaluation as se

TINY_SCRIPT = '''
import gdsfactory as gf
from pathlib import Path

gap_um = 1.0
length_um = 8.0
width_um = 0.6
layer = (1, 0)

c = gf.Component()
for sign in (+1, -1):
    y = sign * (gap_um + width_um) / 2
    ref = c << gf.components.straight(length=length_um, width=width_um)
    ref.movey(y)
c.flatten()
c.write_gds(Path(__file__).parent / "device.gds")
'''


def test_patch_tunables_replaces_values():
    out = se.patch_tunables(TINY_SCRIPT, {"gap_um": 0.25, "length_um": 12.5})
    assert "gap_um = 0.25" in out
    assert "length_um = 12.5" in out
    assert "width_um = 0.6" in out


def test_patch_tunables_missing_name_raises():
    with pytest.raises(ValueError, match="not found"):
        se.patch_tunables(TINY_SCRIPT, {"nonexistent_knob": 1.0})


def test_build_gds_and_guide_centers(tmp_path):
    gds = se.build_gds(TINY_SCRIPT, tmp_path)
    assert gds.exists()
    centers = se.guide_centers(gds, x=4.0)
    assert len(centers) == 2
    assert centers[0] > 0 > centers[1]  # top first
    assert abs(centers[0] - 0.8) < 0.05 and abs(centers[1] + 0.8) < 0.05


def test_dry_run_builds_full_grid(tmp_path):
    script = tmp_path / "dev.py"
    script.write_text(TINY_SCRIPT)
    out = tmp_path / "matrix.json"
    res = se.run_sweep(str(script), _stack(tmp_path), fom="coupling_ratio",
                       sweep={"gap_um": [0.4, 0.6], "length_um": [6.0, 8.0, 10.0]},
                       budget_fc=1.0, out_path=str(out), dry_run=True)
    assert res["status"] == "dry_run"
    assert len(res["cells"]) == 6
    assert res["cells"][0]["params"] == {"gap_um": 0.4, "length_um": 6.0}
    assert json.loads(out.read_text())["axes"]["length_um"] == [6.0, 8.0, 10.0]


def test_budget_abort_starts_nothing(tmp_path, monkeypatch):
    script = tmp_path / "dev.py"
    script.write_text(TINY_SCRIPT)
    started = []
    monkeypatch.setattr(se, "_make_simulation", lambda gds, stack, key: object())
    monkeypatch.setattr(se, "_read_api_key", lambda: "k")
    import flex.core.cloud as cloud
    monkeypatch.setattr(cloud, "upload_simulation",
                        lambda sim, task_name: (f"tid_{task_name}", "url"))
    monkeypatch.setattr(cloud, "estimate_simulation_cost", lambda tid: 0.4)
    monkeypatch.setattr(cloud, "run_simulation",
                        lambda tid: started.append(tid))
    res = se.run_sweep(str(script), _stack(tmp_path), fom="coupling_ratio",
                       sweep={"gap_um": [0.4, 0.6]}, budget_fc=0.5)
    assert res["status"] == "aborted_budget"
    assert res["total_estimate_fc"] == pytest.approx(0.8)
    assert started == []


def test_unsupported_fom_rejected(tmp_path):
    script = tmp_path / "dev.py"
    script.write_text(TINY_SCRIPT)
    with pytest.raises(ValueError, match="unsupported fom"):
        se.run_sweep(str(script), _stack(tmp_path), fom="magic",
                     sweep={"gap_um": [0.4]}, budget_fc=1.0)


def _stack(tmp_path) -> str:
    p = tmp_path / "stack.json"
    p.write_text(json.dumps({"core_n": 1.996, "clad_n": 1.444, "thickness_um": 0.4,
                             "single_mode_width_um": 1.0}))
    return str(p)
