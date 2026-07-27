"""`homi <stage> --detach`: re-exec the stage in a NEW SESSION.

Plain `nohup ... & ` is not conductor-safe: codex kills the whole process
group when a shell tool-call returns (measured 2026-07-09 — the studio
conductor's detached `homi generate` died before its first log write, empty
log, no worker). A new session (start_new_session=True) escapes the group;
measured to survive the same reaper. The detach path must therefore be the
CLI's own responsibility, not a shell trick in a brief.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from homi import cli


def test_spawn_detached_new_session_and_strips_flag(monkeypatch, tmp_path):
    calls = {}

    class _P:
        pid = 4242

    def fake_popen(cmd, **kw):
        calls["cmd"] = cmd
        calls["kw"] = kw
        return _P()

    monkeypatch.setattr(cli.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(sys, "argv",
                        ["homi", "generate", "projects/x", "--detach"])
    log = tmp_path / "out" / "generate.log"
    cli._spawn_detached(log)

    assert calls["kw"]["start_new_session"] is True   # survives the group kill
    assert "--detach" not in calls["cmd"]             # no fork bomb
    assert calls["cmd"][:4] == [sys.executable, "-u", "-m", "homi.cli"]
    assert calls["cmd"][4:] == ["generate", "projects/x"]
    assert log.parent.is_dir()                        # log dir created


def test_detach_log_paths():
    gen = SimpleNamespace(command="generate", project_dir=Path("projects/x"))
    assert cli._detach_log_path(gen) == Path("projects/x/output/generate.log")

    ret = SimpleNamespace(command="retarget", workdir=None,
                          script_path=Path("projects/x/output/best.py"))
    assert cli._detach_log_path(ret) == Path(
        "projects/x/output/retarget/retarget.log")

    ext = SimpleNamespace(command="extract", output=Path("projects/x"))
    assert cli._detach_log_path(ext) == Path("projects/x/extract.log")


def test_detach_extract_requires_output():
    ext = SimpleNamespace(command="extract", output=None)
    with pytest.raises(SystemExit):
        cli._detach_log_path(ext)


def test_detach_flag_wired_into_parsers(capsys, monkeypatch, tmp_path):
    spawned = {}
    monkeypatch.setattr(cli, "_spawn_detached",
                        lambda log: spawned.setdefault("log", log))
    monkeypatch.setattr(sys, "argv",
                        ["homi", "generate", str(tmp_path), "--detach"])
    cli.main()
    assert spawned["log"] == tmp_path / "output" / "generate.log"
