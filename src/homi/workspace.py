"""Run-owned worker workspaces — where agents spawn, structurally.

The invariant (release spec D6): **a run owns its workspace; workers spawn
only into a workspace the run created — never beside the caller, never
adopted, never reused.** ``pane spawn`` is not used anywhere in homi: it can
only split beside the caller's pane (no window/session targeting), which is
how workers used to land in whatever window the conductor happened to occupy.

Two backends behind one interface:

- ``tmux-session`` (lab): each run creates a NEW tmux session on the DEFAULT
  server (visible in the user's cockpit — a dedicated ``-L`` server would hide
  workers from viz and break every ``pane`` verb). Workers get one window
  each; pane ids come from ``tmux … -P -F '#{pane_id}'`` structured output.
  Delivery/status ride anu's ``pane`` verbs, which accept explicit ``%id``s
  server-wide and work with ``$TMUX`` unset.
- ``headless`` (portable): claude ``-p --resume`` / codex ``exec resume``
  subprocess sessions in a per-run directory, log-first. This is what an
  outsider without anu gets; plain-tmux-without-anu also lands here (pane's
  delivery machinery is the value of the tmux backend — re-implementing it
  against arbitrary TUIs is the fragile surface we refuse to ship).

Success is never judged here — the conductor gate judges artifacts. This
module only places workers and moves text.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

RUN_PREFIX = "homi-"

# Worker panes run on the HOST — never contained boxes (2026-07-09 mandate) —
# and codex workers are PINNED to gpt-5.5 medium fast: a bare `codex --yolo`
# inherits ~/.codex/config.toml (whatever the human last set it to), so an
# unpinned alias silently drifts to the wrong model. MCP is disabled per the
# RUNBOOK: a hanging personal MCP server blocks codex's first turn.
DEFAULT_WORKER_CLI = "auto"

_CODEX_PIN = (
    "codex --yolo -m gpt-5.5 -c model_reasoning_effort=medium"
    " -c service_tier=fast -c mcp_servers={}"
)


@dataclass(frozen=True)
class WorkerCLI:
    """One worker CLI flavor: how to launch it in a pane, and headlessly.

    ``pane_launch`` is a real shell command (not an anu alias) — the run
    session's shell may not have the user's interactive aliases.
    """

    alias: str
    kind: str  # "codex" | "claude"
    pane_launch: str

    def headless_argv(
        self,
        prompt: str,
        *,
        model: str | None = None,
        effort: str | None = None,
        resume: str | None = None,
        last_msg_file: str | None = None,
    ) -> list[str]:
        if self.kind == "claude":
            cmd = ["claude", "-p", prompt, "--output-format", "json",
                   "--permission-mode", "bypassPermissions"]
            if resume:
                cmd += ["--resume", resume]
            if model:
                cmd += ["--model", model]
            if effort:
                cmd += ["--effort", effort]
            return cmd
        # codex: `exec` first turn, `exec resume <id>` after; the reply rides
        # -o/--output-last-message (clean text — never parse JSONL for content).
        cmd = ["codex", "exec"]
        if resume:
            cmd += ["resume", resume]
        cmd += [prompt, "--yolo", "--json",
                "-m", model or "gpt-5.5",
                "-c", f"model_reasoning_effort={effort or 'medium'}",
                "-c", "mcp_servers={}"]
        if last_msg_file:
            cmd += ["-o", last_msg_file]
        return cmd


WORKER_CLIS: dict[str, WorkerCLI] = {
    "codex": WorkerCLI("codex", "codex", _CODEX_PIN),
    "claude": WorkerCLI("claude", "claude", "claude --dangerously-skip-permissions"),
    # lab-era alias compat (recorded commands and campaign transcripts use these)
    "cdxx": WorkerCLI("cdxx", "codex", _CODEX_PIN),
    "cdxxs": WorkerCLI("cdxxs", "codex", "codex --full-auto"),
    "cxx": WorkerCLI("cxx", "claude", "claude --dangerously-skip-permissions"),
    "cxc": WorkerCLI("cxc", "claude", "claude --dangerously-skip-permissions"),
}


def worker_cli(alias: str | None) -> WorkerCLI:
    alias = alias or DEFAULT_WORKER_CLI
    if alias == "auto":
        # codex-first preserves the recorded default; if neither CLI is
        # installed, return the codex spec so dispatch raises its usual
        # "no agent backend" error at launch time.
        import shutil as _shutil

        if _shutil.which("codex"):
            alias = "codex"
        elif _shutil.which("claude"):
            alias = "claude"
        else:
            alias = "codex"
    if alias in WORKER_CLIS:
        return WORKER_CLIS[alias]
    # escape hatch: an unknown alias passes through verbatim (the run
    # session's shell must resolve it); headless falls back to claude/codex.
    kind = "codex" if alias.startswith("cd") else "claude"
    return WorkerCLI(alias, kind, alias)


@dataclass
class RunInfo:
    run_id: str
    stage: str
    backend: str
    run_dir: Path
    session: str | None = None            # tmux session name (None headless)
    workers: dict[str, str] = field(default_factory=dict)
    dispatcher_pid: int = 0
    status: str = "running"

    def to_json(self) -> dict:
        d = dict(self.__dict__)
        d["run_dir"] = str(self.run_dir)
        return d


def _state_dir() -> Path:
    root = os.environ.get("HOMI_STATE_DIR") or os.path.join(
        os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state"), "homi"
    )
    return Path(root)


def _registry_dir() -> Path:
    d = _state_dir() / "runs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _slugify(text: str, limit: int = 20) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "run").lower()).strip("-")[:limit]
    return s.strip("-") or "run"


def resolve_backend(*, probe: bool = True) -> str:
    """The ladder. ``$TMUX`` is deliberately NOT required: pane verbs accept
    explicit ``%id``s from outside tmux, so a studio launched from a plain
    terminal still gets a visible, attachable run session.

    ``probe=False`` skips the live server check (dry runs, planning).
    """
    override = os.environ.get("HOMI_BACKEND", "")
    if override:
        return "tmux-session" if override.startswith("tmux") else "headless"
    if shutil.which("pane") and shutil.which("tmux"):
        if not probe:
            return "tmux-session"
        try:
            check = subprocess.run(["tmux", "list-sessions"],
                                   capture_output=True, text=True, timeout=10)
            if check.returncode == 0:
                return "tmux-session"
        except Exception:  # noqa: BLE001 — unreachable server == no tmux backend
            pass
    return "headless"


def await_pane_ready(target: str, deadline_s: int = 120) -> bool:
    """Block until the pane's agent composer is accepting input.

    Text sent into a booting TUI is swallowed by the raw tty — echoed in
    scrollback, never submitted. ``pane status`` is the authoritative boot
    classifier. Once the pane is idle, an agent composer marker anchored at
    the start of a screen line is the final readiness signal. The anchoring is
    load-bearing: the launch shell's ``path branch ❯`` prompt can remain in
    scrollback while Codex is still drawing its startup screen.
    """
    end = time.time() + deadline_s
    while time.time() < end:
        status_result = subprocess.run(
            ["pane", "status", target],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # anu reports a vanished target as a failed status command with empty
        # stdout (rather than the literal word ``dead``).  Treat either form
        # as terminal so a lost pane cannot hold a web capacity slot until the
        # full readiness deadline expires.
        if status_result.returncode != 0:
            return False
        status = status_result.stdout.strip()
        if status == "dead":
            return False
        if status != "idle":
            time.sleep(2)
            continue
        # read the WHOLE visible region: on tall daemon-created windows the
        # composer sits well above the last few lines (the tail is the
        # status line plus trailing blanks — measured 2026-07-21, where an
        # 8-line probe never saw a perfectly ready composer)
        screen = subprocess.run(["pane", "read", target, "60"],
                                capture_output=True, text=True, timeout=30).stdout
        if re.search(
                r"(?m)^[^\S\r\n]*(?:›|❯|⏵|❮)(?:[^\S\r\n]|$)", screen):
            return True
        time.sleep(2)
    return False


def _ensure_turn_started(target: str) -> None:
    """Nudge until the sent brief actually RUNS (staged paste reads idle)."""
    for _ in range(6):
        time.sleep(3)
        st = subprocess.run(["pane", "status", target],
                            capture_output=True, text=True, timeout=30).stdout
        if (st.strip().split() or ["gone"])[0] in ("working", "approval"):
            return
        subprocess.run(["pane", "send", target, ""],
                       capture_output=True, text=True, timeout=30)


def _tmux(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(["tmux", *args], capture_output=True, text=True, timeout=timeout)


class TmuxWorker:
    def __init__(self, ws: "TmuxRunWorkspace", role: str, target: str, cli: WorkerCLI):
        self.ws = ws
        self.role = role
        self.target = target
        self.cli = cli
        self._sends = 0

    def send(self, text: str) -> None:
        self._sends += 1
        if self._sends == 1 and not await_pane_ready(self.target, deadline_s=180):
            raise RuntimeError(
                f"worker pane {self.target} never became ready ({self.cli.alias})"
            )
        msg = self.ws.info.run_dir / "briefs" / f".msg_{self.role}_{self._sends:03d}.md"
        msg.parent.mkdir(parents=True, exist_ok=True)
        msg.write_text(text)
        sent = subprocess.run(["pane", "send", self.target, "-f", str(msg)],
                              capture_output=True, text=True, timeout=60)
        if sent.returncode != 0:
            raise RuntimeError(
                f"pane send to {self.target} failed: "
                f"{(sent.stderr or sent.stdout)[-300:]}"
            )
        _ensure_turn_started(self.target)

    def wait(self, timeout_s: int = 3600) -> str:
        # pane's own default caps at 240 s — pass the stage timeout explicitly
        # or long thinkers return early and get judged failed on absent
        # artifacts (found 2026-07-11).
        proc = subprocess.run(["pane", "wait", self.target, str(int(timeout_s))],
                              capture_output=True, text=True, timeout=timeout_s + 60)
        return (proc.stdout or "")[-4000:]

    def status(self) -> str:
        out = subprocess.run(["pane", "status", self.target],
                             capture_output=True, text=True, timeout=30).stdout
        return (out.strip().split() or ["gone"])[0]

    def read(self, lines: int = 40) -> str:
        return subprocess.run(["pane", "read", self.target, str(lines)],
                              capture_output=True, text=True, timeout=30).stdout


class TmuxRunWorkspace:
    backend = "tmux-session"

    def __init__(self, info: RunInfo, workdir: str):
        self.info = info
        self.workdir = workdir
        self._owned_session = False

    def spawn(self, role: str = "worker", cli: str | None = None, *,
              cwd: str | None = None, model: str | None = None,
              effort: str | None = None,
              env: dict[str, str] | None = None) -> TmuxWorker:
        del model, effort  # pane launches carry their pin in the launch string
        spec = worker_cli(cli)
        cwd = cwd or self.workdir
        # env vars must ride the LAUNCH COMMAND: tmux session environment set
        # after the fact never reaches an already-running process (measured
        # 2026-07-21), so ownership stamps would be silently absent.
        launch = spec.pane_launch
        if env:
            exports = " ".join(
                f"{k}={shlex.quote(str(v))}" for k, v in env.items())
            launch = f"env {exports} {launch}"
        if not self._owned_session:
            proc = _tmux("new-session", "-d", "-s", self.info.session,
                         "-c", cwd, "-P", "-F", "#{pane_id}")
            if proc.returncode != 0:
                raise RuntimeError(f"tmux new-session failed: {proc.stderr[-300:]}")
            self._owned_session = True
            _tmux("set-option", "-t", self.info.session, "@homi_run", self.info.run_id)
            target = proc.stdout.strip().splitlines()[0]
            _tmux("rename-window", "-t", target, role)
        else:
            proc = _tmux("new-window", "-d", "-t", f"{self.info.session}:",
                         "-n", role, "-c", cwd, "-P", "-F", "#{pane_id}")
            if proc.returncode != 0:
                raise RuntimeError(f"tmux new-window failed: {proc.stderr[-300:]}")
            target = proc.stdout.strip().splitlines()[0]
        # stamp identity so `pane status` classifies boot correctly, viz
        # labels the pane, and reuse checks can verify who this really is.
        # The stamp is the TRUE binary even when an env prefix wraps the launch.
        binary = spec.pane_launch.split()[0]
        _tmux("set-option", "-p", "-t", target, "@anu_expected_cli", binary)
        _tmux("set-option", "-p", "-t", target, "@anu_role", f"homi-{role}")
        log = self.info.run_dir / "logs" / f"{role}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        # the pipe command is shell text — quote the path (a workdir with an
        # apostrophe would otherwise break out of it)
        _tmux("pipe-pane", "-t", target, "-o", f"cat >> {shlex.quote(str(log))}")
        # launch into the pane's shell (a crashed CLI leaves an inspectable shell)
        _tmux("send-keys", "-t", target, launch, "C-m")
        self.info.workers[role] = target
        _persist(self.info)
        return TmuxWorker(self, role, target, spec)

    def close(self, status: str = "ok", *, keep: bool | None = None) -> None:
        self.info.status = status
        keep = bool(os.environ.get("HOMI_KEEP_RUNS")) if keep is None else keep
        discard_failed = bool(os.environ.get("HOMI_DISCARD_FAILED_RUNS"))
        if (self._owned_session and not keep
                and (status == "ok" or discard_failed)):
            _tmux("kill-session", "-t", self.info.session)
        elif self._owned_session and status != "ok":
            print(f"[homi] run {self.info.run_id} kept for inspection: "
                  f"tmux attach -t {self.info.session}")
        _persist(self.info)


class HeadlessWorker:
    def __init__(self, ws: "HeadlessRunWorkspace", role: str, cli: WorkerCLI,
                 cwd: str, model: str | None, effort: str | None):
        self.ws = ws
        self.role = role
        self.cli = cli
        self.cwd = cwd
        self.model = model
        self.effort = effort
        self.target = f"headless:{cli.alias}:{role}"
        self._pending: str | None = None
        self._session_id: str | None = None
        self._turns = 0

    def send(self, text: str) -> None:
        self._pending = text

    def wait(self, timeout_s: int = 3600) -> str:
        if self._pending is None:
            raise RuntimeError("wait() called with no pending turn — send first")
        text, self._pending = self._pending, None
        self._turns += 1
        log = self.ws.info.run_dir / "logs" / f"{self.role}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        last_msg = self.ws.info.run_dir / "logs" / f".{self.role}_last.md"
        # a stale last-message file from the PREVIOUS turn must never be
        # readable as this turn's reply (a failed `codex exec resume` would
        # otherwise replay the prior success — e.g. a spent "PHASE_B DONE")
        last_msg.unlink(missing_ok=True)
        cmd = self.cli.headless_argv(
            text, model=self.model, effort=self.effort,
            resume=self._session_id, last_msg_file=str(last_msg),
        )
        proc = subprocess.run(cmd, cwd=self.cwd, capture_output=True,
                              text=True, timeout=timeout_s)
        stdout = proc.stdout or ""
        if proc.returncode != 0:
            reply = (f"[worker turn failed: {self.cli.alias} exited "
                     f"{proc.returncode}] " + (proc.stderr or stdout)[-1500:])
        else:
            reply = self._extract_reply(stdout, last_msg)
            if not (reply or "").strip() or reply == stdout:
                # an empty result with a zero exit usually means the CLI
                # printed its complaint (login, quota) around the envelope —
                # surface something a human can read, not raw JSON
                hint = (proc.stderr or "").strip()[-800:]
                if hint:
                    reply = f"[worker returned no result] {hint}"
        with log.open("a") as fh:
            fh.write(f"\n----- turn {self._turns} ({self.cli.alias}) -----\n")
            fh.write(reply or stdout or (proc.stderr or "")[-2000:])
            fh.write("\n")
        self.ws.info.workers[self.role] = f"{self.target};sess:{self._session_id or '-'}"
        _persist(self.ws.info)
        return reply

    def _extract_reply(self, stdout: str, last_msg: Path) -> str:
        if self.cli.kind == "claude":
            try:
                out = json.loads(stdout) if stdout.strip() else {}
                self._session_id = out.get("session_id") or self._session_id
                return out.get("result") or stdout
            except (json.JSONDecodeError, ValueError):
                return stdout
        # codex: session id from the JSONL events; reply from the -o file.
        # Event names have churned (session_meta vs thread.started) — match either.
        m = re.search(r'"(?:session_id|thread_id)"\s*:\s*"([0-9a-f-]{36})"', stdout)
        if m:
            self._session_id = m.group(1)
        if last_msg.exists():
            return last_msg.read_text()
        return stdout

    def status(self) -> str:
        return "working" if self._pending is not None else "idle"

    def read(self, lines: int = 40) -> str:
        log = self.ws.info.run_dir / "logs" / f"{self.role}.log"
        if not log.exists():
            return ""
        return "\n".join(log.read_text().splitlines()[-lines:])


class HeadlessRunWorkspace:
    backend = "headless"

    def __init__(self, info: RunInfo, workdir: str):
        self.info = info
        self.workdir = workdir

    def spawn(self, role: str = "worker", cli: str | None = None, *,
              cwd: str | None = None, model: str | None = None,
              effort: str | None = None,
              env: dict[str, str] | None = None) -> HeadlessWorker:
        del env  # headless workers inherit the dispatcher's environment
        spec = worker_cli(cli)
        # headless needs the actual binary: fall back to whichever exists
        if not shutil.which(spec.pane_launch.split()[0]):
            other = "claude" if spec.kind == "codex" else "codex"
            if shutil.which(other):
                spec = worker_cli("cxx" if other == "claude" else "cdxx")
            else:
                raise RuntimeError(
                    "no agent backend available: need `pane`+tmux, or "
                    "`claude`/`codex` on PATH"
                )
        w = HeadlessWorker(self, role, spec, cwd or self.workdir, model, effort)
        self.info.workers[role] = w.target
        _persist(self.info)
        return w

    def close(self, status: str = "ok", *, keep: bool | None = None) -> None:
        del keep
        self.info.status = status
        _persist(self.info)


def _persist(info: RunInfo) -> None:
    payload = json.dumps(info.to_json(), indent=1)
    (info.run_dir / "run.json").parent.mkdir(parents=True, exist_ok=True)
    (info.run_dir / "run.json").write_text(payload)
    (_registry_dir() / f"{info.run_id}.json").write_text(payload)


def open_run(stage: str, workdir: str, *, slug: str | None = None,
             backend: str | None = None) -> TmuxRunWorkspace | HeadlessRunWorkspace:
    """Create the run's workspace (the ONLY way homi places a worker)."""
    backend = backend or resolve_backend()
    now = datetime.now(timezone.utc)
    stage_slug = _slugify(stage)
    name_slug = _slugify(slug or Path(workdir).resolve().name)
    nonce = secrets.token_hex(2)
    run_id = f"{stage_slug}-{name_slug}-{now:%y%m%d-%H%M%S}-{nonce}"
    run_dir = Path(workdir) / ".homi-run" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    info = RunInfo(
        run_id=run_id,
        stage=stage,
        backend=backend,
        run_dir=run_dir,
        # nonce in the session name too: two same-stage/same-slug runs in the
        # same second must not collide at `tmux new-session`
        session=(f"{RUN_PREFIX}{stage_slug}-{name_slug}-{now:%H%M%S}-{nonce}"
                 if backend == "tmux-session" else None),
        dispatcher_pid=os.getpid(),
    )
    ws = (TmuxRunWorkspace if backend == "tmux-session" else HeadlessRunWorkspace)(
        info, str(workdir)
    )
    _persist(info)
    return ws


def list_runs() -> list[RunInfo]:
    infos = []
    for f in sorted(_registry_dir().glob("*.json")):
        try:
            d = json.loads(f.read_text())
            d["run_dir"] = Path(d["run_dir"])
            infos.append(RunInfo(**d))
        except Exception:  # noqa: BLE001 — a corrupt registry entry is skippable
            continue
    return infos


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def gc_runs() -> list[str]:
    """Kill leftover run sessions whose run is finished (or whose dispatcher
    died). Never touches sessions homi didn't create (``homi-`` prefix AND a
    registry entry)."""
    live = subprocess.run(
        ["tmux", "list-sessions", "-F", "#{session_name}"],
        capture_output=True, text=True, timeout=15,
    ).stdout.splitlines()
    killed = []
    for info in list_runs():
        if not info.session or info.session not in live:
            continue
        finished = info.status in ("ok", "failed", "killed")
        if finished or not _pid_alive(info.dispatcher_pid):
            subprocess.run(["tmux", "kill-session", "-t", info.session],
                           capture_output=True, text=True, timeout=15)
            killed.append(info.session)
    return killed
