"""Suite-wide guards.

Worker-run registry writes must NEVER land in the developer's real state dir
(~/.local/state/homi) — several dispatch tests execute the real open_run()
persistence path with only subprocess faked (measured 2026-07-11: test-run
entries polluted the live `homi runs ls`).
"""

import pytest


@pytest.fixture(autouse=True)
def _isolated_homi_state(monkeypatch, tmp_path):
    monkeypatch.setenv("HOMI_STATE_DIR", str(tmp_path / "homi-state"))
