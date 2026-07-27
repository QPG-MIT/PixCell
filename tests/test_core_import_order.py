"""Regression: the historical jee/weber top-level ``core`` package clash.

Both packages have a ``core`` subpackage; they were once imported by the bare
name ``core`` and needed ``sys.modules`` surgery to coexist. The clash was
resolved structurally by the src/ package layout + absolute imports
(``from jee.core import ...`` / ``from weber.core import ...``) — this test
guards that both import orders keep working and no bare-``core`` import creeps
back in. The check is process-global, so each order runs in a fresh interpreter.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _import_order(stmts: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONSAFEPATH": "1", "PYTHONPATH": str(ROOT)}
    return subprocess.run(
        [sys.executable, "-c", f"{stmts}; print('OK')"],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=120,
    )


def test_jee_first_then_weber():
    """raphael / calibration order: jee_integration before weber_integration."""
    r = _import_order("import homi.jee_integration; import homi.weber_integration")
    assert r.returncode == 0, f"jee-first import failed:\n{r.stderr[-1600:]}"
    assert "OK" in r.stdout


def test_weber_first_then_jee():
    """original app order still works."""
    r = _import_order("import homi.weber_integration; import homi.jee_integration")
    assert r.returncode == 0, f"weber-first import failed:\n{r.stderr[-1600:]}"
    assert "OK" in r.stdout
