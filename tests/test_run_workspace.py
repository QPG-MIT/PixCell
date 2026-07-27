"""RunWorkspace — one run, one run-owned workspace (P0 spawn invariant).

The invariant under test: workers spawn ONLY into a session the run created —
never beside the caller, never adopted from an existing window. Placement is
raw ``tmux new-session``/``new-window`` with structured ``-P -F '#{pane_id}'``
output; anu ``pane`` verbs (send/read/wait/status) drive the pane afterward.
Outsiders without anu get the headless claude/codex session pool.
"""

import json

import pytest

from homi import workspace


class R:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


def _lab(monkeypatch, tmp_path, calls, *, screens=None, wait_out="PHASE_A DONE: IoU=0.9"):
    """anu lab: pane + tmux on PATH, server reachable, caller inside tmux."""
    monkeypatch.setenv("TMUX", "/tmp/fake-tmux,1,0")
    monkeypatch.setenv("TMUX_PANE", "%99")
    monkeypatch.setenv("HOMI_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("HOMI_BACKEND", raising=False)
    monkeypatch.delenv("HOMI_KEEP_RUNS", raising=False)
    monkeypatch.setattr(workspace.shutil, "which", lambda c: f"/usr/bin/{c}")
    monkeypatch.setattr(workspace.time, "sleep", lambda s: None)
    screen_iter = iter(screens or ["› composer"])
    last_screen = {"s": "› composer"}
    brief_sent = {"value": False}
    pane_ids = iter(["%201", "%202", "%203", "%204", "%205"])

    def fake_run(cmd, **kw):
        calls.append(list(cmd))
        if cmd[0] == "tmux":
            if cmd[1] == "new-session":
                return R(next(pane_ids) + "\n")
            if cmd[1] == "new-window":
                return R(next(pane_ids) + "\n")
            if cmd[1] == "list-sessions":
                return R("")
            return R()
        if cmd[0] == "pane":
            if cmd[1] == "read":
                last_screen["s"] = next(screen_iter, last_screen["s"])
                return R(last_screen["s"])
            if cmd[1] == "status":
                return R("working" if brief_sent["value"] else "idle")
            if cmd[1] == "send":
                if "-f" in cmd:
                    brief_sent["value"] = True
                return R()
            if cmd[1] == "wait":
                return R(wait_out)
            return R()
        return R()

    monkeypatch.setattr(workspace.subprocess, "run", fake_run)
    return fake_run


# ---------------------------------------------------------------- placement


def test_never_spawns_beside_caller(monkeypatch, tmp_path):
    calls = []
    _lab(monkeypatch, tmp_path, calls)
    ws = workspace.open_run("phase_a", str(tmp_path), slug="ring-res")
    w = ws.spawn(role="phase-a")
    w.send("brief text")
    joined = [" ".join(c) for c in calls]
    assert not any(c[:2] == ["pane", "spawn"] for c in calls)
    assert not any("split-window" in j for j in joined)
    assert not any("%99" in j for j in joined)          # the caller's own pane
    creates = [c for c in calls if c[0] == "tmux" and c[1] == "new-session"]
    assert creates and "-d" in creates[0]


def test_session_naming_stamps_and_windows(monkeypatch, tmp_path):
    calls = []
    _lab(monkeypatch, tmp_path, calls)
    ws = workspace.open_run("phase_a", str(tmp_path), slug="Ring Res!!")
    a = ws.spawn(role="phase-a")
    b = ws.spawn(role="soi220")
    import re

    # nonce suffix: two same-stage/same-slug runs in one second must not
    # collide at `tmux new-session`
    assert re.fullmatch(r"homi-phase-a-ring-res-\d{6}-[0-9a-f]{4}", ws.info.session)
    ws2 = workspace.open_run("phase_a", str(tmp_path), slug="Ring Res!!")
    assert ws2.info.session != ws.info.session
    assert a.target == "%201" and b.target == "%202"
    joined = [" ".join(c) for c in calls]
    assert any("@homi_run" in j for j in joined)
    assert any("@anu_expected_cli" in j for j in joined)
    wins = [c for c in calls if c[0] == "tmux" and c[1] == "new-window"]
    assert wins and f"{ws.info.session}:" in " ".join(wins[0]) and "-d" in wins[0]
    # per-worker log mirror
    assert any(c[:2] == ["tmux", "pipe-pane"] for c in calls)
    assert (ws.info.run_dir / "logs").exists()


def test_first_send_gated_on_composer_ready(monkeypatch, tmp_path):
    calls = []
    _lab(monkeypatch, tmp_path, calls, screens=["booting banner", "still booting", "› up"])
    ws = workspace.open_run("phase_a", str(tmp_path), slug="d")
    w = ws.spawn(role="phase-a")
    w.send("the brief")
    sends = [c for c in calls if c[:2] == ["pane", "send"] and "-f" in c]
    assert sends and sends[0][2] == "%201"
    reads_before = [c for c in calls[: calls.index(sends[0])] if c[:2] == ["pane", "read"]]
    assert len(reads_before) >= 3                      # waited out the boot
    # the message rode a file (quote-safe), stored under the run dir
    msg = sends[0][sends[0].index("-f") + 1]
    assert str(ws.info.run_dir) in msg


def test_wait_passes_explicit_seconds(monkeypatch, tmp_path):
    calls = []
    _lab(monkeypatch, tmp_path, calls)
    ws = workspace.open_run("phase_a", str(tmp_path), slug="d")
    w = ws.spawn(role="phase-a")
    w.send("brief")
    out = w.wait(2700)
    assert "PHASE_A DONE" in out
    waits = [c for c in calls if c[:2] == ["pane", "wait"]]
    assert waits and waits[0][2:] == ["%201", "2700"]  # not pane's 240s default


# ---------------------------------------------------------------- lifecycle


def test_close_ok_kills_failed_keeps(monkeypatch, tmp_path):
    calls = []
    _lab(monkeypatch, tmp_path, calls)
    ws = workspace.open_run("phase_a", str(tmp_path), slug="d")
    ws.spawn(role="phase-a")
    ws.close("ok")
    assert any(c[:2] == ["tmux", "kill-session"] for c in calls)

    calls.clear()
    ws2 = workspace.open_run("phase_a", str(tmp_path), slug="d2")
    ws2.spawn(role="phase-a")
    ws2.close("failed")
    assert not any(c[:2] == ["tmux", "kill-session"] for c in calls)
    assert ws2.info.status == "failed"

    calls.clear()
    monkeypatch.setenv("HOMI_KEEP_RUNS", "1")
    ws3 = workspace.open_run("phase_a", str(tmp_path), slug="d3")
    ws3.spawn(role="phase-a")
    ws3.close("ok")
    assert not any(c[:2] == ["tmux", "kill-session"] for c in calls)

    calls.clear()
    monkeypatch.delenv("HOMI_KEEP_RUNS")
    monkeypatch.setenv("HOMI_DISCARD_FAILED_RUNS", "1")
    ws4 = workspace.open_run("phase_a", str(tmp_path), slug="d4")
    ws4.spawn(role="phase-a")
    ws4.close("failed")
    assert any(c[:2] == ["tmux", "kill-session"] for c in calls)


def test_run_registry_and_gc(monkeypatch, tmp_path):
    calls = []
    _lab(monkeypatch, tmp_path, calls)
    ws = workspace.open_run("phase_a", str(tmp_path), slug="d")
    ws.spawn(role="phase-a")
    ws.close("ok")
    infos = workspace.list_runs()
    assert any(i.run_id == ws.info.run_id and i.status == "ok" for i in infos)

    # a finished run whose session survived (e.g. crash before kill) is collectable
    stale = workspace.list_runs()[0]
    fake_sessions = f"{stale.session}\nsomeones-real-session\n"

    def fake_run(cmd, **kw):
        calls.append(list(cmd))
        if cmd[:2] == ["tmux", "list-sessions"]:
            return R(fake_sessions)
        return R()

    monkeypatch.setattr(workspace.subprocess, "run", fake_run)
    killed = workspace.gc_runs()
    assert stale.session in killed
    kill_cmds = [" ".join(c) for c in calls if c[:2] == ["tmux", "kill-session"]]
    assert kill_cmds and all("someones-real-session" not in k for k in kill_cmds)


# ---------------------------------------------------------------- headless


def _no_anu(monkeypatch, tmp_path, *, have=("claude", "codex")):
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("HOMI_BACKEND", raising=False)
    monkeypatch.setenv("HOMI_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(
        workspace.shutil, "which", lambda c: f"/usr/bin/{c}" if c in have else None
    )
    monkeypatch.setattr(workspace.time, "sleep", lambda s: None)


def test_headless_claude_threads_resume(monkeypatch, tmp_path):
    _no_anu(monkeypatch, tmp_path, have=("claude",))
    cmds = []

    def fake_run(cmd, **kw):
        cmds.append(list(cmd))
        return R(json.dumps({"session_id": "sess-1", "result": "reply-%d" % len(cmds)}))

    monkeypatch.setattr(workspace.subprocess, "run", fake_run)
    ws = workspace.open_run("phase_b", str(tmp_path), slug="d")
    w = ws.spawn(role="phase-b", cli="cxx")
    w.send("turn one")
    assert "reply-1" in w.wait(600)
    w.send("turn two")
    w.wait(600)
    assert "--resume" not in cmds[0]
    assert "--resume" in cmds[1] and cmds[1][cmds[1].index("--resume") + 1] == "sess-1"
    log = (ws.info.run_dir / "logs" / "phase-b.log").read_text()
    assert "reply-1" in log and "reply-2" in log


@pytest.mark.parametrize("id_key", ["session_id", "thread_id"])
def test_headless_codex_resumes_parsed_session(monkeypatch, tmp_path, id_key):
    _no_anu(monkeypatch, tmp_path, have=("codex",))
    cmds = []
    uuid = "0f0e0d0c-1111-2222-3333-444455556666"

    def fake_run(cmd, **kw):
        cmds.append(list(cmd))
        if "-o" in cmd:
            from pathlib import Path

            Path(cmd[cmd.index("-o") + 1]).write_text("codex says hi")
        return R(f'{{"type":"x","{id_key}":"{uuid}"}}\n')

    monkeypatch.setattr(workspace.subprocess, "run", fake_run)
    ws = workspace.open_run("phase_b", str(tmp_path), slug="d")
    w = ws.spawn(role="phase-b", cli="cdxx")
    w.send("turn one")
    assert "codex says hi" in w.wait(600)
    w.send("turn two")
    w.wait(600)
    assert cmds[0][:2] == ["codex", "exec"] and "resume" not in cmds[0]
    assert "--json" in cmds[0] and "--ephemeral" not in " ".join(cmds[0])
    assert cmds[1][:3] == ["codex", "exec", "resume"] and uuid in cmds[1]


def test_headless_codex_failed_resume_never_replays_prior_reply(monkeypatch, tmp_path):
    """A failed `codex exec resume` must not surface the PREVIOUS turn's
    last-message file as this turn's reply — a stale 'PHASE_B DONE' would
    terminate the measure loop as a success."""
    _no_anu(monkeypatch, tmp_path, have=("codex",))
    uuid = "0f0e0d0c-1111-2222-3333-444455556666"
    calls = {"n": 0}

    def fake_run(cmd, **kw):
        calls["n"] += 1
        from pathlib import Path

        if calls["n"] == 1:
            Path(cmd[cmd.index("-o") + 1]).write_text("PHASE_B DONE: soi220=T0.97")
            return R(f'{{"session_id":"{uuid}"}}\n')
        # resume turn: crashes WITHOUT writing the -o file
        return R("", returncode=1)

    monkeypatch.setattr(workspace.subprocess, "run", fake_run)
    ws = workspace.open_run("phase_b", str(tmp_path), slug="d")
    w = ws.spawn(role="phase-b", cli="cdxx")
    w.send("turn one")
    assert "PHASE_B DONE" in w.wait(600)
    w.send("turn two")
    reply = w.wait(600)
    assert "PHASE_B DONE" not in reply
    assert "failed" in reply.lower()


# ------------------------------------------------------------------ ladder


def test_backend_ladder(monkeypatch, tmp_path):
    calls = []
    # pane + tmux reachable, TMUX UNSET -> still the visible tmux backend
    _lab(monkeypatch, tmp_path, calls)
    monkeypatch.delenv("TMUX", raising=False)
    assert workspace.resolve_backend() == "tmux-session"

    # tmux server unreachable -> headless
    monkeypatch.setattr(
        workspace.subprocess, "run", lambda cmd, **kw: R("no server", returncode=1)
    )
    assert workspace.resolve_backend() == "headless"

    # explicit override wins
    monkeypatch.setenv("HOMI_BACKEND", "headless")
    assert workspace.resolve_backend() == "headless"
    monkeypatch.setenv("HOMI_BACKEND", "tmux")
    assert workspace.resolve_backend() == "tmux-session"

    # no pane at all -> headless
    monkeypatch.delenv("HOMI_BACKEND", raising=False)
    monkeypatch.setattr(workspace.shutil, "which", lambda c: None)
    assert workspace.resolve_backend() == "headless"


def test_worker_cli_table_pins():
    cdxx = workspace.WORKER_CLIS["cdxx"]
    assert cdxx.kind == "codex"
    assert cdxx.pane_launch.startswith("codex --yolo")
    assert "-m gpt-5.5" in cdxx.pane_launch and "mcp_servers={}" in cdxx.pane_launch
    assert "box" not in cdxx.pane_launch                 # host, never contained
    cxx = workspace.WORKER_CLIS["cxx"]
    assert cxx.kind == "claude"
    assert "claude" in cxx.pane_launch
    argv = cdxx.headless_argv("hi", last_msg_file="/tmp/x.md")
    assert argv[:2] == ["codex", "exec"] and "--json" in argv and "hi" in argv
    argv2 = cdxx.headless_argv("again", resume="abc-123", last_msg_file="/tmp/x.md")
    assert argv2[:3] == ["codex", "exec", "resume"] and "abc-123" in argv2
