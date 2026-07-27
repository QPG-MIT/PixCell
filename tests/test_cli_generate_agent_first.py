"""homi generate — Phase-A agent recreate loop by default, multi-seed behind --baseline (P3)."""

import argparse
import json

import homi.cli as cli


def _project(tmp_path):
    (tmp_path / "device_bw.png").write_bytes(b"png")
    (tmp_path / "footprint.json").write_text(json.dumps({"footprint_um": [10.0, 2.0]}))
    return tmp_path


def _ns(project_dir, **over):
    base = dict(
        project_dir=project_dir, preset="balanced", model="gemini/gemini-3-flash-preview",
        phase1_only=False, base_seed=1333, baseline=False,
        cli="cxc", worker_model=None, worker_effort=None,
    )
    base.update(over)
    return argparse.Namespace(**base)


def test_default_dispatches_phase_a_and_gates(tmp_path, monkeypatch):
    project = _project(tmp_path)
    seen = {}

    def fake_dispatch(stage, brief_vars, workdir, **kw):
        seen.update(stage=stage, vars=brief_vars, workdir=workdir, cli=kw.get("cli"))
        wd = project / "output" / "recreation_agent"
        (wd / "device.py").write_text("# device")
        (wd / "device.gds").write_bytes(b"gds")
        (wd / "component.png").write_bytes(b"png")  # brief step 1: copy + calibrate
        (wd / "calibration.json").write_text("{}")
        (wd / "submission.json").write_text(json.dumps({
            "claimed_iou": 0.91,
            "knob": {"name": "length", "width_um": 0.5},
        }))
        return {"status": "ok", "backend": "anu-pane", "command": [],
                "artifacts": {"device.py": True}, "output_tail": "PHASE_A DONE: IoU=0.91"}

    gated = {}

    def fake_verify(gds, target, calib, script, claimed_iou=None, knob=None):
        gated.update(gds=str(gds), script=str(script))
        from homi.conductor.gate import GateResult

        return GateResult(iou=0.91, metrics={"IoU": 0.91}, iou_matches_claim=True,
                          purity=[], knob={"param": "length", "ok": True},
                          verified=True)

    monkeypatch.setattr("homi.dispatch.dispatch_agent", fake_dispatch)
    monkeypatch.setattr("homi.conductor.promote.verify_cell", fake_verify)

    rc = cli.cmd_generate(_ns(project))
    assert rc in (0, None)
    assert seen["stage"] == "phase_a"
    assert seen["vars"]["INPUT_DIR"] == str(project)
    assert seen["cli"] == "cxc"
    assert gated["gds"].endswith("device.gds")
    # verified result is promoted to the canonical output contract
    assert (project / "output" / "best.py").exists()
    assert (project / "output" / "best.gds").exists()


def test_baseline_flag_runs_multiseed(tmp_path, monkeypatch):
    project = _project(tmp_path)
    calls = []

    monkeypatch.setattr("homi.gds_generation.setup_component_directory",
                        lambda *a, **k: calls.append("setup"))
    monkeypatch.setattr("homi.gds_generation.run_calibration",
                        lambda *a, **k: calls.append("calib") or True)
    monkeypatch.setattr("homi.gds_generation.run_phase1",
                        lambda *a, **k: calls.append("phase1"))
    monkeypatch.setattr("homi.gds_generation.run_phase2",
                        lambda *a, **k: calls.append("phase2"))
    monkeypatch.setattr("homi.gds_generation.collect_best_output",
                        lambda *a, **k: calls.append("collect") or {})

    rc = cli.cmd_generate(_ns(project, baseline=True))
    assert rc in (0, None)
    assert "phase1" in calls and "phase2" in calls
