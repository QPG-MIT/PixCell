"""Regression tests for the artifact-bound conductor promotion record."""

import hashlib
import json

from homi.conductor.gate import GateResult


def test_gate_record_hashes_every_measured_artifact(tmp_path, monkeypatch):
    from homi.conductor import promote

    project = tmp_path / "project"
    workdir = tmp_path / "candidate"
    workdir.mkdir()
    artifacts = {
        "script_sha256": workdir / "device.py",
        "gds_sha256": workdir / "device.gds",
        "target_sha256": workdir / "component.png",
        "calibration_sha256": workdir / "calibration.json",
    }
    artifacts["script_sha256"].write_text("width_um = 1.5\n")
    artifacts["gds_sha256"].write_bytes(b"gds candidate")
    artifacts["target_sha256"].write_bytes(b"target pixels")
    artifacts["calibration_sha256"].write_text('{"um_per_px": 0.05}')
    (workdir / "submission.json").write_text(
        json.dumps(
            {
                "claimed_iou": 0.95,
                "knob": {"name": "width_um", "width_um": 2.0},
            }
        )
    )

    monkeypatch.setattr(
        promote,
        "verify_cell",
        lambda *_args, **_kwargs: GateResult(
            iou=0.95,
            metrics={"IoU": 0.95},
            iou_matches_claim=True,
            purity=[],
            knob={"param": "width_um", "ok": True},
            verified=True,
        ),
    )

    outcome = promote.gate_and_promote(project, workdir)

    assert outcome.promoted
    record = json.loads((project / "output" / "gate.json").read_text())
    assert record["artifacts"] == {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in artifacts.items()
    }
    assert hashlib.sha256((project / "output" / "best.py").read_bytes()).hexdigest() == (
        record["artifacts"]["script_sha256"]
    )
    assert hashlib.sha256((project / "output" / "best.gds").read_bytes()).hexdigest() == (
        record["artifacts"]["gds_sha256"]
    )
