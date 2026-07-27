"""Promoted conductor tooling: tier1 harness + campaign metrics (P2)."""

import json
import subprocess

import pytest
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CAMPAIGN = REPO / "agents" / "experiments" / "paper_swap"
if not CAMPAIGN.is_dir():  # post-P4 location
    CAMPAIGN = REPO / "data" / "agents" / "paper_swap"


def test_tier1_module_cli_help():
    proc = subprocess.run(
        [sys.executable, "-m", "homi.conductor.tier1", "--help"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0
    assert "--ceiling" in proc.stdout


def test_tier1_imports_light():
    import homi.conductor.tier1 as tier1

    assert callable(tier1.main)
    assert "tidy3d" not in dir(tier1)  # heavy imports stay inside main()


@pytest.mark.skipif(not (CAMPAIGN / "sweep_results.json").exists(),
                    reason="campaign record not ported yet")
def test_build_results_reproduces_campaign_grid():
    from homi.conductor.metrics import build_results

    existing = json.loads((CAMPAIGN / "sweep_results.json").read_text())
    rebuilt = build_results(CAMPAIGN, write=False)
    assert len(rebuilt["cells"]) == len(existing["cells"])
    # spot-check the pilot cell survives the rebuild identically
    pilot = [c for c in rebuilt["cells"] if c["device"] == "final1" and c["config"] == "codex55x"]
    assert pilot and abs(pilot[0]["iou"] - 0.9491) < 1e-9


def test_extract_metrics_empty_staging(tmp_path):
    from homi.conductor.metrics import extract_metrics

    result = extract_metrics(tmp_path, write=False)
    assert result == {"cells": []}
