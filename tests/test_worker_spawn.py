"""Worker placement: HOST codex pinned to gpt-5.5 medium fast — never boxes.

2026-07-09 mandate: no contained (box/cxc) workers for now, and the codex
worker must be pinned — a bare `codex --yolo` inherits ~/.codex/config.toml,
which drifts (it was gpt-5.6-terra max when this landed).

2026-07-11 structural fix: homi never calls `pane spawn` (it can only split
beside the caller). Placement is `tmux new-session/new-window -P -F
'#{pane_id}'` — structured output, nothing to mis-parse. The old arrow-parse
of `pane spawn` prose (which once sent a worker brief back to the
dispatching pane) is gone along with the call it parsed.
"""

import shutil
import subprocess

from homi import dispatch, workspace


class _R:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


def _lab(monkeypatch):
    monkeypatch.setenv("TMUX", "/tmp/fake-tmux,1,0")
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, **kw: _R("" if cmd[0] != "tmux" else "%201\n")
    )


def test_default_worker_is_pinned_host_codex(monkeypatch):
    _lab(monkeypatch)
    plan = dispatch.dispatch_agent(
        "phase_a", {"GIT_RULE": "", "INPUT_DIR": "x", "WORKDIR": "z"},
        workdir="/tmp/claude-worker-spawn-test", dry_run=True,
    )
    assert plan["backend"] == "anu-pane"
    spawn = plan["launch"]
    assert spawn.startswith("codex --yolo")      # host codex, not a box
    assert "box" not in spawn
    assert "-m gpt-5.5" in spawn                 # pinned, not inherited
    assert "model_reasoning_effort=medium" in spawn
    assert "service_tier=fast" in spawn
    assert "mcp_servers={}" in spawn


def test_placement_is_a_new_session_not_a_split(monkeypatch):
    _lab(monkeypatch)
    plan = dispatch.dispatch_agent(
        "phase_a", {"GIT_RULE": "", "INPUT_DIR": "x", "WORKDIR": "z"},
        workdir="/tmp/claude-worker-spawn-test", dry_run=True,
    )
    assert plan["command"][:3] == ["tmux", "new-session", "-d"]
    joined = " ".join(plan["command"])
    assert "pane spawn" not in joined and "split-window" not in joined


def test_known_alias_maps_to_explicit_launch(monkeypatch):
    # aliases are shell functions in the USER's interactive shell; a run
    # session's shell may not have them, so known aliases map to real commands
    _lab(monkeypatch)
    plan = dispatch.dispatch_agent(
        "phase_a", {"GIT_RULE": "", "INPUT_DIR": "x", "WORKDIR": "z"},
        workdir="/tmp/claude-worker-spawn-test", cli="cxx", dry_run=True,
    )
    assert plan["launch"] == "claude --dangerously-skip-permissions"


def test_unknown_alias_passes_through(monkeypatch):
    _lab(monkeypatch)
    plan = dispatch.dispatch_agent(
        "phase_a", {"GIT_RULE": "", "INPUT_DIR": "x", "WORKDIR": "z"},
        workdir="/tmp/claude-worker-spawn-test", cli="my-custom-agent", dry_run=True,
    )
    assert plan["launch"] == "my-custom-agent"


def test_pane_readiness_ignores_shell_prompt_during_agent_boot(monkeypatch):
    """A run shell also uses ❯; it must never count as an agent composer."""
    states = iter(("idle", "idle"))
    screens = iter((
        "…/output/recreation_agent web-frontdoor ❯ codex --yolo\n",
        "› Summarize recent commits\n",
    ))
    reads = []

    def fake_run(cmd, **_kwargs):
        if cmd[:2] == ["pane", "status"]:
            return _R(next(states) + "\n")
        if cmd[:2] == ["pane", "read"]:
            reads.append(cmd)
            return _R(next(screens))
        raise AssertionError(cmd)

    monkeypatch.setattr(workspace.subprocess, "run", fake_run)
    monkeypatch.setattr(workspace.time, "sleep", lambda _seconds: None)

    assert workspace.await_pane_ready("%201", deadline_s=1)
    assert reads == [
        ["pane", "read", "%201", "60"],
        ["pane", "read", "%201", "60"],
    ]


def test_pane_readiness_fails_when_worker_dies(monkeypatch):
    def fake_run(cmd, **_kwargs):
        assert cmd[:2] == ["pane", "status"]
        # Real `pane status` uses a non-zero exit with empty stdout when the
        # target has vanished.
        return _R(returncode=1)

    monkeypatch.setattr(workspace.subprocess, "run", fake_run)

    assert not workspace.await_pane_ready("%201", deadline_s=1)


def test_pane_readiness_accepts_literal_dead_status(monkeypatch):
    def fake_run(cmd, **_kwargs):
        assert cmd[:2] == ["pane", "status"]
        return _R("dead\n")

    monkeypatch.setattr(workspace.subprocess, "run", fake_run)

    assert not workspace.await_pane_ready("%201", deadline_s=1)


def test_pane_readiness_accepts_claude_nonbreaking_space(monkeypatch):
    def fake_run(cmd, **_kwargs):
        if cmd[:2] == ["pane", "status"]:
            return _R("idle\n")
        if cmd[:2] == ["pane", "read"]:
            return _R("Claude Code v2\n\u276f\u00a0\n")
        raise AssertionError(cmd)

    monkeypatch.setattr(workspace.subprocess, "run", fake_run)

    assert workspace.await_pane_ready("%201", deadline_s=1)
