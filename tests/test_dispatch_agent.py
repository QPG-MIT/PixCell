"""dispatch_agent — stage-generic, CLI-agnostic, artifact-verified (P1)."""

from homi import dispatch


def _extract_vars(out):
    return {"INPUT": "p.pdf", "OUTPUT_DIR": str(out), "HINT_LINE": "", "INPUT_NOTE": ""}


def test_dry_run_pane_backend_honors_cli(tmp_path, monkeypatch):
    monkeypatch.setenv("TMUX", "x")
    monkeypatch.setattr(dispatch.shutil, "which", lambda c: "/bin/" + c)
    r = dispatch.dispatch_agent(
        "extract", _extract_vars(tmp_path), workdir=str(tmp_path), cli="cdxx", dry_run=True
    )
    assert r["status"] == "planned"
    assert r["backend"] == "anu-pane"
    # cdxx expands to the pinned host-codex launch string (WORKER_CLIS):
    # a bare alias would inherit ~/.codex/config.toml and drift models.
    assert "codex --yolo" in r["launch"] and "gpt-5.5" in r["launch"]
    assert "mcp_servers={}" in r["launch"]


def test_dry_run_headless_codex_for_cd_alias(tmp_path, monkeypatch):
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.setattr(
        dispatch.shutil, "which", lambda c: "/bin/" + c if c in ("codex", "claude") else None
    )
    r = dispatch.dispatch_agent(
        "extract", _extract_vars(tmp_path), workdir=str(tmp_path), cli="cdxx", dry_run=True
    )
    assert r["backend"] == "codex-cli"
    assert r["command"][:2] == ["codex", "exec"]


def test_status_requires_artifacts(tmp_path, monkeypatch):
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.setattr(
        dispatch.shutil, "which", lambda c: "/bin/claude" if c == "claude" else None
    )
    monkeypatch.setattr(
        dispatch.subprocess,
        "run",
        lambda *a, **k: dispatch.subprocess.CompletedProcess(a, 0, stdout="done", stderr=""),
    )
    r = dispatch.dispatch_agent("extract", _extract_vars(tmp_path), workdir=str(tmp_path))
    assert r["status"] == "failed"
    assert r["artifacts"] == {"device_bw.png": False, "footprint.json": False}

    (tmp_path / "device_bw.png").write_bytes(b"x")
    (tmp_path / "footprint.json").write_text("{}")
    r2 = dispatch.dispatch_agent("extract", _extract_vars(tmp_path), workdir=str(tmp_path))
    assert r2["status"] == "ok"
    assert r2["artifacts"] == {"device_bw.png": True, "footprint.json": True}


def test_unknown_stage_raises(tmp_path):
    try:
        dispatch.dispatch_agent("nope", {}, workdir=str(tmp_path), dry_run=True)
        raise AssertionError("should have raised")
    except KeyError:
        pass
