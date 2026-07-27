"""Regression: `homi migrate` CLI must work end-to-end.

It previously did `from gg.pdk import pdk_manager` — a symbol that never
existed — so the command crashed on import before doing anything. The fix
drives the same PDKServer handlers the MCP tools use.
"""
import os
import subprocess
import sys
from pathlib import Path

import gdstk

ROOT = Path(__file__).resolve().parent.parent


def _make_gds(path: Path) -> None:
    lib = gdstk.Library()
    cell = lib.new_cell("DEV")
    cell.add(gdstk.rectangle((0, 0), (14.0, 0.9), layer=1, datatype=0))
    lib.write_gds(str(path))


def test_cli_migrate_runs(tmp_path):
    src = tmp_path / "dev.gds"
    _make_gds(src)
    out = tmp_path / "dev_si220.gds"
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    r = subprocess.run(
        [sys.executable, "-m", "homi.cli", "migrate", str(src),
         "--target-pdk", "generic_si220", "-o", str(out), "--drc"],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=300,
    )
    assert r.returncode == 0, f"migrate CLI failed:\nstdout: {r.stdout[-800:]}\nstderr: {r.stderr[-800:]}"
    assert out.exists(), "migrated GDS not written"
    assert "DRC" in r.stdout or "drc" in r.stdout.lower()
