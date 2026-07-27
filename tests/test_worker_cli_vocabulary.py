"""The public worker-CLI vocabulary: claude | codex | auto (+ lab compat).

`--cli` is user-facing; the public words must resolve to the pinned
full-auto launch commands, `auto` must prefer codex (the recorded default)
and degrade gracefully, and the lab-era aliases that appear in recorded
campaign commands must keep resolving to the same specs.
"""

from homi import workspace


def test_public_names_resolve():
    codex = workspace.worker_cli("codex")
    claude = workspace.worker_cli("claude")
    assert codex.kind == "codex" and codex.pane_launch.startswith("codex ")
    assert "gpt-5.5" in codex.pane_launch  # the pin, not a bare --yolo
    assert claude.kind == "claude"
    assert claude.pane_launch.startswith("claude ")


def test_auto_prefers_codex_then_claude(monkeypatch):
    import shutil

    monkeypatch.setattr(shutil, "which", lambda name: "/x/" + name)
    assert workspace.worker_cli("auto").kind == "codex"

    monkeypatch.setattr(
        shutil, "which", lambda name: "/x/claude" if name == "claude" else None
    )
    assert workspace.worker_cli("auto").kind == "claude"

    # neither installed: still returns a spec (dispatch raises at launch time)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert workspace.worker_cli("auto").kind == "codex"


def test_default_is_auto():
    assert workspace.DEFAULT_WORKER_CLI == "auto"


def test_lab_aliases_stay_compatible():
    assert (
        workspace.worker_cli("cdxx").pane_launch
        == workspace.worker_cli("codex").pane_launch
    )
    assert (
        workspace.worker_cli("cxc").pane_launch
        == workspace.worker_cli("claude").pane_launch
    )
    assert workspace.worker_cli("cxx").kind == "claude"
