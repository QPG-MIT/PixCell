"""Dispatch a pipeline stage to a worker agent — the control plane.

Every human surface (CLI / REST / studio / chat pane) funnels through
``dispatch_agent``: render the stage's brief from ``homi.briefs``, spawn a
worker in a RUN-OWNED workspace (``homi.workspace`` — a dedicated tmux
session in the lab, a headless claude/codex session anywhere else), and judge
success ONLY by the artifacts the worker produced — never by a send/exit
status. Downstream, ``homi.conductor`` gates the artifacts deterministically.

Placement is structural: homi never calls ``pane spawn`` (it can only split
beside the caller), so a worker can never land in the dispatcher's window and
a brief can never be sent back to the dispatcher itself.

Result dicts keep the historical backend names (``anu-pane``, ``claude-cli``,
``codex-cli``) so callers and records stay comparable across the change.
"""

from __future__ import annotations

import os
import re
import shutil  # noqa: F401 — kept importable here: callers/tests patch dispatch.shutil
import subprocess  # noqa: F401 — same: dispatch.subprocess is a patch point
import time  # noqa: F401 — same
from dataclasses import dataclass, field
from pathlib import Path

from homi import briefs, workspace
from homi.workspace import (  # noqa: F401 — stable public surface (re-exports)
    DEFAULT_WORKER_CLI,
    WORKER_CLIS,
    await_pane_ready,
    worker_cli,
)

_CLAUDE_ALIASES = ("cxc", "cxx")
_CODEX_ALIASES = ("cdxx", "cdxxs")


@dataclass(frozen=True)
class StageSpec:
    brief: str
    expected_artifacts: tuple[str, ...]
    timeout_s: int = 1800
    marker: str | None = None
    extra_vars: dict = field(default_factory=dict)


STAGES: dict[str, StageSpec] = {
    "extract": StageSpec(
        brief="extract",
        expected_artifacts=("device_bw.png", "footprint.json"),
        timeout_s=1800,
        marker=r"EXTRACT DONE: files=[0-9]",
    ),
    "phase_a": StageSpec(
        brief="phase_a_recreation",
        expected_artifacts=("device.py",),
        timeout_s=2700,
        marker=r"PHASE_A DONE: IoU=[0-9]",
    ),
    "phase_b": StageSpec(
        brief="phase_b_retarget",
        expected_artifacts=(),
        timeout_s=3600,
        marker=r"PHASE_B DONE: ",
    ),
}


def _legacy_backend_name(backend: str, cli: str | None) -> str:
    if backend == "tmux-session":
        return "anu-pane"
    return "codex-cli" if workspace.worker_cli(cli).kind == "codex" else "claude-cli"


def _check_artifacts(spec: StageSpec, workdir: str) -> dict[str, bool]:
    return {a: (Path(workdir) / a).exists() for a in spec.expected_artifacts}


def _finalize(result: dict, spec: StageSpec, workdir: str) -> dict:
    """Success is the artifacts, never the transport status."""
    artifacts = _check_artifacts(spec, workdir)
    result["artifacts"] = artifacts
    if spec.marker:
        out = result.get("output_tail") or ""
        result["marker_found"] = bool(re.search(spec.marker, out))
    else:
        result["marker_found"] = None
    result["status"] = "ok" if all(artifacts.values()) else "failed"
    return result


def _headless_cli(cli: str | None) -> str | None:
    """Pick the headless flavor the machine can actually run."""
    import shutil as _shutil

    spec = workspace.worker_cli(cli)
    if _shutil.which(spec.pane_launch.split()[0]):
        return cli
    if spec.kind == "codex" and _shutil.which("claude"):
        return "cxx"
    if spec.kind == "claude" and _shutil.which("codex"):
        return "cdxx"
    raise RuntimeError(
        "no agent backend available: need `pane`+tmux, or `claude`/`codex` on PATH"
    )


def dispatch_agent(
    stage: str,
    brief_vars: dict,
    workdir: str,
    *,
    cli: str | None = None,
    model: str | None = None,
    effort: str | None = None,
    dry_run: bool = False,
    timeout_s: int | None = None,
    run: "workspace.TmuxRunWorkspace | workspace.HeadlessRunWorkspace | None" = None,
) -> dict:
    """Dispatch one stage to a worker agent and verify its artifacts.

    Returns a dict with ``backend``, ``command``, ``status`` (``ok`` iff every
    expected artifact exists in ``workdir``), ``artifacts`` (per-file bool),
    ``output_tail``, ``run_id``/``session``/``target`` (where the worker
    lives) and — when the stage defines one — ``marker_found``
    (informational: pane scrollback can hide a marker that fired; the
    conductor gate, not the marker, is the acceptance check).

    Pass ``run`` to place the worker in an existing workspace (campaigns
    share one session across workers); otherwise the dispatch owns a fresh
    workspace and closes it with the run's status.
    """
    spec = STAGES[stage]  # KeyError on unknown stage is the contract
    timeout = timeout_s or spec.timeout_s
    os.makedirs(workdir, exist_ok=True)
    # PYTHON: the interpreter the worker should use — this dispatch's own env
    # (an installed package has no repo-relative .venv to point at)
    import sys as _sys

    brief = briefs.render(
        spec.brief,
        **{"PYTHON": _sys.executable, **spec.extra_vars, **brief_vars},
    )
    backend = (run.backend if run is not None
               else workspace.resolve_backend(probe=not dry_run))
    legacy = _legacy_backend_name(backend, cli)

    if dry_run:
        if backend == "tmux-session":
            spec_cli = workspace.worker_cli(cli)
            name = f"{workspace.RUN_PREFIX}{stage.replace('_', '-')}-…"
            return {
                "backend": legacy, "status": "planned",
                "command": ["tmux", "new-session", "-d", "-s", name, "-c", workdir],
                "launch": spec_cli.pane_launch,
            }
        cli = _headless_cli(cli)
        spec_cli = workspace.worker_cli(cli)
        cmd = spec_cli.headless_argv(brief, model=model, effort=effort)
        return {"backend": _legacy_backend_name(backend, cli), "status": "planned",
                "command": cmd, "launch": spec_cli.pane_launch}

    owned = run is None
    try:
        if backend != "tmux-session":
            cli = _headless_cli(cli)
            legacy = _legacy_backend_name(backend, cli)
        ws = run or workspace.open_run(stage, workdir)
        worker = ws.spawn(role=stage.replace("_", "-"), cli=cli,
                          model=model, effort=effort)
        worker.send(brief)
        out = worker.wait(timeout)
        result = {
            "backend": legacy,
            "command": [worker.target],
            "target": worker.target,
            "run_id": ws.info.run_id,
            "session": ws.info.session,
            "run_dir": str(ws.info.run_dir),
            "output_tail": (out or "")[-4000:],
        }
        _finalize(result, spec, workdir)
        if owned:
            ws.close(result["status"])
        return result
    except Exception as e:  # noqa: BLE001 — surface any spawn/send failure to the caller
        try:
            if owned and "ws" in locals():
                ws.close("failed")
        except Exception:  # noqa: BLE001
            pass
        return {"backend": legacy, "command": [], "status": "error", "error": str(e)}


def open_worker_session(workdir: str, cli: str | None = None, *,
                        stage: str = "phase_b", model: str | None = None,
                        effort: str | None = None, timeout_s: int = 3600):
    """Multi-turn worker session: ``(send, wait)`` in a run-owned workspace.

    ``homi.conductor.measure.service_loop`` consumes the callables unchanged.
    The workspace closes at interpreter exit — with status ``ok`` unless a
    send/wait raised, in which case the session is kept (with an attach hint)
    for inspection. Callers that can judge the protocol outcome themselves
    (e.g. ``cmd_retarget``) should use ``workspace.open_run`` directly and
    close with the real status. ``HOMI_KEEP_RUNS=1`` always keeps sessions.
    """
    import atexit

    backend = workspace.resolve_backend()
    if backend != "tmux-session":
        cli = _headless_cli(cli)
    ws = workspace.open_run(stage, workdir)
    worker = ws.spawn(role=stage.replace("_", "-"), cli=cli,
                      model=model, effort=effort)
    outcome = {"status": "ok"}
    atexit.register(lambda: ws.close(outcome["status"]))

    def send(text: str) -> None:
        try:
            worker.send(text)
        except Exception:
            outcome["status"] = "failed"
            raise

    def wait() -> str:
        try:
            return worker.wait(timeout_s)
        except Exception:
            outcome["status"] = "failed"
            raise

    return send, wait


def open_headless_session(workdir: str, *, model: str | None = None,
                          effort: str | None = None, timeout_s: int = 3600):
    """Deprecated alias — headless claude multi-turn ``(send, wait)``.

    Kept one release for callers that pinned the old name; new code uses
    ``open_worker_session`` (which also handles codex and the tmux backend).
    """
    ws = workspace.open_run("phase_b", workdir, backend="headless")
    worker = ws.spawn(role="phase-b", cli="cxx", model=model, effort=effort)

    def send(text: str) -> None:
        worker.send(text)

    def wait() -> str:
        return worker.wait(timeout_s)

    return send, wait


# --- extraction wrappers (stable public surface) -----------------------------


def _dispatch_python() -> str:
    import sys as _sys
    return _sys.executable


def build_extractor_brief(pdf_path: str, output_dir: str, hint: str | None = None) -> str:
    """The self-contained brief handed to the extractor agent (pure)."""
    return briefs.render(
        "extract",
        INPUT=pdf_path,
        OUTPUT_DIR=output_dir,
        HINT_LINE=f"Device hint: {hint}\n" if hint else "",
        INPUT_NOTE="",
        PYTHON=_dispatch_python(),
    )


def dispatch_extractor_agent(
    pdf_path: str,
    output_dir: str,
    hint: str | None = None,
    *,
    dry_run: bool = False,
    input_kind: str = "pdf",
    cli: str | None = None,
) -> dict:
    """Stand up an extractor agent to do perception. Returns a status dict."""
    note = (
        "The input is a single device image, not a PDF: skip the PDF steps and go "
        "straight to the B&W conversion + footprint.\n"
        if input_kind == "image"
        else ""
    )
    return dispatch_agent(
        "extract",
        {
            "INPUT": pdf_path,
            "OUTPUT_DIR": output_dir,
            "HINT_LINE": f"Device hint: {hint}\n" if hint else "",
            "INPUT_NOTE": note,
        },
        workdir=output_dir,
        cli=cli,
        dry_run=dry_run,
    )
