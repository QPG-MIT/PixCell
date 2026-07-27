"""homi retarget — Phase-B dispatch with the conductor-serviced MEASURE loop (P3)."""

import argparse
import json
import os
import time
from types import SimpleNamespace

import pytest

from homi.conductor import measure


@pytest.mark.parametrize(
    ("passes", "unmeasured", "measured", "expected_verdict"),
    [
        (True, (), 0.97, "pass"),
        (False, (), 0.82, "fail"),
        (False, ("transmission",), None, "unmeasured"),
    ],
)
def test_write_retarget_result_owns_deterministic_verdict(
    tmp_path,
    monkeypatch,
    passes,
    unmeasured,
    measured,
    expected_verdict,
):
    import homi.cli as cli
    from homi import spec_optimization

    workdir = tmp_path / "retarget"
    device_dir = workdir / "soi220"
    device_dir.mkdir(parents=True)
    device = device_dir / "device_soi220.py"
    device.write_text("# measured device\n")
    (device_dir / "measured.json").write_text(
        json.dumps({"transmission_total": 0.97})
    )
    stack = tmp_path / "soi220.json"
    stack.write_text(json.dumps({"label": "SOI 220 nm", "core_n": 3.48}))
    spec = tmp_path / "function.json"
    spec.write_text(json.dumps({"targets": [{"metric": "transmission"}]}))

    verdict = SimpleNamespace(metric="transmission", measured=measured)
    report_dict = {
        "passes": passes,
        "unmeasured": list(unmeasured),
        "metric": "transmission",
    }
    report = SimpleNamespace(
        passes=passes,
        unmeasured=unmeasured,
        verdicts=(verdict,),
        reason="measurement verdict",
        to_dict=lambda: report_dict,
    )
    calls = []

    def fake_evaluate(device_path, stack_payload, spec_payload, **kwargs):
        calls.append((device_path, stack_payload, spec_payload, kwargs))
        return report

    monkeypatch.setattr(spec_optimization, "evaluate", fake_evaluate)

    result = cli._write_retarget_result(
        workdir=workdir,
        stack_path=stack,
        spec_path=spec,
    )

    assert result["verdict"] == expected_verdict
    assert result["stack"] == "soi220"
    assert result["stack_label"] == "SOI 220 nm"
    assert result["spec"] == "function.json"
    assert result["fom"] == (
        {} if measured is None else {"transmission": measured}
    )
    assert result["report"] == report_dict
    assert json.loads((device_dir / "result.json").read_text()) == result
    assert not (device_dir / "result.json.tmp").exists()
    assert len(calls) == 1
    assert calls[0][0] == device
    assert calls[0][1]["label"] == "SOI 220 nm"
    assert calls[0][2]["targets"][0]["metric"] == "transmission"
    assert calls[0][3]["measured_metrics"]["transmission"] == 0.97


def _fresh_fixture(tmp_path, stack="soi220"):
    src = tmp_path / f"fixture_{stack}.py"
    src.write_text("# fixture")
    gds = tmp_path / f"fixture_{stack}.gds"
    gds.write_bytes(b"gds")
    now = time.time()
    os.utime(src, (now - 100, now - 100))
    os.utime(gds, (now, now))
    return gds


def test_service_loop_measures_then_finishes(tmp_path):
    gds = _fresh_fixture(tmp_path)
    turns = iter([
        f"MEASURE soi220: fixture={gds} predicted_T=0.96",
        "PHASE_B DONE: soi220=T0.967/fits=yes",
    ])
    sent = []
    ledger = measure.CapLedger(per_stack=3)

    out = measure.service_loop(
        send=sent.append,
        wait=lambda: next(turns),
        ledger=ledger,
        run_tier1=lambda req: {"split_fraction_t": 0.5, "splitter_il_db": 0.15},
    )
    assert "PHASE_B DONE" in out
    assert len(sent) == 1 and "MEASURED soi220" in sent[0] and "0.5" in sent[0]
    assert ledger.remaining("soi220") == 2


def test_service_loop_declines_stale_without_spending(tmp_path):
    gds = _fresh_fixture(tmp_path)
    os.utime(gds.with_suffix(".py"), None)  # touch source -> fixture now stale
    turns = iter([
        f"MEASURE soi220: fixture={gds} predicted_T=0.9",
        "PHASE_B BLOCKED: could not rebuild",
    ])
    sent = []
    ledger = measure.CapLedger(per_stack=3)
    ran = []

    measure.service_loop(
        send=sent.append, wait=lambda: next(turns), ledger=ledger,
        run_tier1=lambda req: ran.append(req),
    )
    assert not ran  # stale never reaches the harness
    assert "DECLINED" in sent[0] and "stale" in sent[0].lower()
    assert ledger.remaining("soi220") == 3  # not consumed


def test_service_loop_cap_exhaustion(tmp_path):
    gds = _fresh_fixture(tmp_path)
    turns = iter([
        f"MEASURE soi220: fixture={gds} predicted_T=0.9",
        "PHASE_B DONE: soi220=honest-fail",
    ])
    sent = []
    measure.service_loop(
        send=sent.append, wait=lambda: next(turns),
        ledger=measure.CapLedger(per_stack=0),
        run_tier1=lambda req: {"t": 0.5},
    )
    assert "cap exhausted" in sent[0]


def test_cmd_retarget_requires_some_backend(tmp_path, monkeypatch):
    """No pane AND no claude on PATH -> refuse clearly (headless is the
    fallback backend, pane the primary)."""
    import homi.cli as cli

    monkeypatch.delenv("TMUX", raising=False)
    import shutil as _shutil

    monkeypatch.setattr(_shutil, "which", lambda c: None)
    script = tmp_path / "device.py"
    script.write_text("# device")
    stack = tmp_path / "soi220.json"
    stack.write_text(json.dumps({"core_material": "Si", "thickness_um": 0.22}))
    spec = tmp_path / "spec_soi220.json"
    spec.write_text(json.dumps({"transmission_min": 0.95}))

    ns = argparse.Namespace(
        script_path=script, stack=stack, spec=spec,
        tier1_cap=3, cli="cxc", ceiling=0.45, workdir=None,
    )
    rc = cli.cmd_retarget(ns)
    assert rc == 1


def test_headless_session_roundtrip_and_resume(tmp_path, monkeypatch):
    """The headless multi-turn transport: send queues, wait executes against a
    persistent session (--resume carries the id after the first turn)."""
    from homi import dispatch

    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        payload = json.dumps({"session_id": "sess-1",
                              "result": f"reply-{len(calls)}"})
        return dispatch.subprocess.CompletedProcess(cmd, 0, stdout=payload, stderr="")

    monkeypatch.setattr(dispatch.subprocess, "run", fake_run)
    send, wait = dispatch.open_headless_session(str(tmp_path))

    send("the brief")
    assert wait() == "reply-1"
    send("MEASURED soi220: {...}")
    assert wait() == "reply-2"

    assert "--resume" not in calls[0]
    assert "--resume" in calls[1] and "sess-1" in calls[1]
