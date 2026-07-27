"""conductor.readback + conductor.measure — protocol primitives (P2).

Readback fixtures are the real strings from the July sweep
(data/agents/paper_swap/SWEEP_STATE.md): launch flags can silently
remap models; the status line is the only reliable config check.
"""

import time

from homi.conductor import measure, readback


# --- readback ----------------------------------------------------------------


def test_parse_codex_status_line():
    r = readback.parse_status_line("  gpt-5.4 medium   Context 3% used · 12K")
    assert r["model"] == "gpt-5.4"
    assert r["effort"] == "medium"

    r2 = readback.parse_status_line("gpt-5.3-codex-spark medium")
    assert r2["model"] == "gpt-5.3-codex-spark"


def test_parse_claude_status_line():
    r = readback.parse_status_line("Opus 4.8 · ctx (13k/1.0M)")
    assert r["model"] == "Opus 4.8"
    r2 = readback.parse_status_line("Sonnet 4.5")
    assert r2["model"] == "Sonnet 4.5"


def test_verify_catches_silent_remap():
    pane = "claude  Opus 4.8 · ctx (13k/1.0M)"
    assert readback.verify(pane, "claude-opus-4-8")
    # requested opus-4-1, pane actually runs 4.8 — the sweep's real failure mode
    assert not readback.verify(pane, "claude-opus-4-1")


def test_verify_effort_only_fails_on_contradiction():
    assert readback.verify("gpt-5.5 xhigh", "gpt-5.5", expect_effort="xhigh")
    assert not readback.verify("gpt-5.5 medium", "gpt-5.5", expect_effort="xhigh")
    # claude pane that shows no effort: accept (SWEEP_STATE: haiku may not show effort)
    assert readback.verify("Haiku 4.5", "haiku-4.5", expect_effort="high")


# --- measure -----------------------------------------------------------------


def test_parse_measure_request_takes_freshest():
    text = (
        "MEASURE soi220: fixture=old/fixture.gds predicted_T=0.90\n"
        "...iterating...\n"
        "MEASURE soi220: fixture=phase_b/soi220/fixture_soi220.gds predicted_T=0.96\n"
    )
    req = measure.parse_request(text)
    assert req is not None
    assert req.stack == "soi220"
    assert req.fixture == "phase_b/soi220/fixture_soi220.gds"
    assert abs(req.predicted - 0.96) < 1e-9
    assert measure.parse_request("no requests here") is None


def test_staleness_gate(tmp_path):
    src = tmp_path / "fixture_soi220.py"
    src.write_text("# device")
    gds = tmp_path / "fixture_soi220.gds"
    gds.write_bytes(b"gds")
    # gds written after source -> fresh
    now = time.time()
    import os

    os.utime(src, (now - 100, now - 100))
    os.utime(gds, (now, now))
    assert measure.staleness_ok(gds, [src])
    # source touched after gds -> stale (measures the previous geometry)
    os.utime(src, (now + 10, now + 10))
    assert not measure.staleness_ok(gds, [src])


def test_cap_ledger_exhausts():
    ledger = measure.CapLedger(per_stack=3)
    assert [ledger.spend("soi220") for _ in range(4)] == [True, True, True, False]
    assert ledger.remaining("soi220") == 0
    assert ledger.remaining("sin400") == 3
