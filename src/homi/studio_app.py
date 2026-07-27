# PixCell studio — chat-first: a conversation with the conductor, the light
# table beside it. Spec: the design notes (kept with the lab record)
# (studio addendum). Run: `homi studio` (marimo run on this file).
#
# The chat IS the driver: drop a PDF, ask for extraction/recreation/retarget;
# the conductor is a persistent headless Claude session working in this repo
# with the normal control plane (dispatch, gate, skills). The table is the
# shared light-table widget; the right column shows the newest gate-verified
# device live (same measure-only math as the gate).

import marimo

__generated_with = "0.23.13"
app = marimo.App(width="full")


@app.cell
def _():
    import base64
    import json
    import re
    import subprocess
    import tempfile
    from pathlib import Path

    import anywidget
    import marimo as mo
    import traitlets

    from homi.paths import projects_dir, workspace_root
    from homi.workbench import (
        DESIGN_CSS, INK_TABLE_ESM, KNOB_PANEL_ESM, LIGHT_TABLE_ESM,
    )

    # The workspace anchor: the checkout when running from one, else the
    # platformdirs user dir — never None, safe for .studio/ state + worker cwd.
    REPO = workspace_root()
    PROJECTS = projects_dir()
    return (
        DESIGN_CSS,
        INK_TABLE_ESM,
        KNOB_PANEL_ESM,
        LIGHT_TABLE_ESM,
        PROJECTS,
        Path,
        REPO,
        anywidget,
        base64,
        json,
        mo,
        re,
        subprocess,
        tempfile,
        traitlets,
    )


@app.cell
def _(DESIGN_CSS, mo):
    style = mo.Html(
        DESIGN_CSS
        + """
    <style>
    /* mono-first: the interface speaks in the instrument's own voice */
    body { font-family: var(--mono); }
    .wb, .studio-sub, .studio-chatlabel { font-family: var(--mono); }
    .studio-masthead { display:flex; align-items:center; gap:16px;
      padding: 6px 2px 14px 2px; border-bottom: 1px solid var(--hairline); }
    .studio-logo { height: 44px; width: auto; display: block; }
    .studio-name { font-family: var(--mono);
      font-size: 24px; font-weight: 700; letter-spacing: -0.01em;
      color: var(--chrome); }
    .studio-sub { font-size: 12px; color: var(--graphite); opacity: 0.75; }
    .studio-preflight { font-family: var(--mono); font-size: 11.5px;
      color: #8a6d1a; background: #fdf6e3; border: 1px solid #e8d9a0;
      border-radius: 2px; padding: 5px 10px; margin: 8px 0 0 0; }
    .studio-chatlabel { font-size: 11px; letter-spacing: 0.04em;
      color: var(--graphite); opacity: 0.7; margin: 0 0 6px 2px; }
    .studio-history { max-height: 200px; overflow-y: auto; font-size: 11.5px; }
    .studio-history .h-you { color: var(--chrome); margin: 6px 0 2px 0; }
    .studio-history .h-agent { color: var(--graphite); opacity: 0.85; }
    /* stage monitor — evidence on disk, ticked as each stage lands */
    .studio-stages { display: flex; align-items: center; flex-wrap: wrap;
      padding: 10px 2px 2px 2px; }
    .studio-stages .st { display: inline-flex; align-items: center; gap: 6px;
      font-size: 10.5px; letter-spacing: 0.08em; text-transform: uppercase;
      color: var(--graphite); opacity: 0.5; white-space: nowrap; }
    .studio-stages .st i { font-style: normal; width: 15px; height: 15px;
      border-radius: 50%; border: 1px solid var(--hairline);
      display: inline-flex; align-items: center; justify-content: center;
      font-size: 9.5px; line-height: 1; box-sizing: border-box; }
    .studio-stages .st.done { opacity: 1; color: var(--chrome); }
    .studio-stages .st.done i { background: var(--pass); border-color: var(--pass);
      color: var(--table); }
    .studio-stages .st.next { opacity: 0.95; color: var(--chrome); }
    .studio-stages .st.next i { border-color: var(--chrome); }
    .studio-stages .st-sep { width: 22px; height: 1px; background: var(--hairline);
      margin: 0 8px; flex: none; }
    </style>"""
    )
    style
    return


@app.cell
def _(REPO, base64, mo):
    from homi.doctor import missing_for_studio

    _logo = REPO / "assets" / "logo.jpeg"
    _img = ""
    if _logo.exists():
        _b64 = base64.b64encode(_logo.read_bytes()).decode()
        _img = f'<img class="studio-logo" src="data:image/jpeg;base64,{_b64}" alt="" />'
    _warn = "".join(
        f'<div class="studio-preflight">⚠ {w}</div>' for w in missing_for_studio()
    )
    masthead = mo.Html(
        f'<div class="wb studio-masthead">{_img}'
        f'<span class="studio-name">PixCell</span></div>{_warn}'
    )
    masthead
    return


@app.cell
def _(device, fom_plan, mo):
    # Stage monitor — each tick is evidence on disk for the selected device,
    # never a worker's claim: same artifacts the gate and conductor read.
    _done = {}
    if device:
        _proj = device["proj"]
        _out = _proj / "output"
        _gate = device["provenance"].get("iou")
        _ret = _out / "retarget"
        _done = {
            "input": (_proj / "paper.pdf").exists() or (_proj / "device_bw.png").exists(),
            "silhouette": (_proj / "device_bw.png").exists()
                          and (_proj / "footprint.json").exists(),
            "gds": (_out / "best.py").exists(),
            "gate": _gate is not None and _gate >= 0.85,
            "function": fom_plan is not None,
            "retarget": _ret.exists() and any(_ret.rglob("*.gds")),
            "simulate": any(
                (_proj / _d).is_dir() and any((_proj / _d).iterdir())
                for _d in ("simulation", "output/simulation")
            ),
        }
    _order = ["input", "silhouette", "gds", "gate", "function", "retarget", "simulate"]
    _next = next((s for s in _order if not _done.get(s)), None)
    _bits = []
    for _s in _order:
        _cls = "done" if _done.get(_s) else ("next" if _s == _next else "")
        _tick = "✓" if _done.get(_s) else ""
        _bits.append(f'<span class="st {_cls}"><i>{_tick}</i>{_s}</span>')
    stage_strip = mo.Html(
        '<div class="wb studio-stages">'
        + '<span class="st-sep"></span>'.join(_bits)
        + "</div>"
    )
    stage_strip
    return


@app.cell
def _(INK_TABLE_ESM, KNOB_PANEL_ESM, LIGHT_TABLE_ESM, anywidget, traitlets):
    class LightTable(anywidget.AnyWidget):
        _esm = LIGHT_TABLE_ESM
        polygons = traitlets.List([]).tag(sync=True)
        layer_polygons = traitlets.Dict({}).tag(sync=True)
        footprint_um = traitlets.List(allow_none=True).tag(sync=True)
        violation = traitlets.Bool(False).tag(sync=True)
        show_ghost = traitlets.Bool(True).tag(sync=True)
        ghost_data_uri = traitlets.Unicode("").tag(sync=True)
        calib = traitlets.Dict(allow_none=True).tag(sync=True)
        iou = traitlets.Float(allow_none=True).tag(sync=True)
        gate_iou = traitlets.Float(allow_none=True).tag(sync=True)
        fits = traitlets.Bool(allow_none=True).tag(sync=True)
        height = traitlets.Int(420).tag(sync=True)

    class InkTable(anywidget.AnyWidget):
        _esm = INK_TABLE_ESM
        ink_data_uri = traitlets.Unicode("").tag(sync=True)
        stroke_width = traitlets.Int(10).tag(sync=True)
        clear_nonce = traitlets.Int(0).tag(sync=True)
        height = traitlets.Int(420).tag(sync=True)

    class KnobPanel(anywidget.AnyWidget):
        _esm = KNOB_PANEL_ESM
        knobs = traitlets.List([]).tag(sync=True)
        values = traitlets.Dict({}).tag(sync=True)

    class ChatChrome(anywidget.AnyWidget):
        """Invisible: marimo's chat chrome lives in shadow DOM with no props —
        rewrite it in place. Three jobs: (1) the empty state becomes a concise
        how-this-works explainer, (2) the entry placeholder shrinks to a verb,
        (3) the chat column is held at the height of the device column (or the
        viewport, whichever is taller) so history has real room to scroll."""

        _esm = r"""
    const PLACEHOLDER = "message the agent";
    const EXPLAINER = `
    <div style="font-family:var(--mono);font-size:12px;line-height:1.85;color:var(--graphite);
     text-align:left;padding:26px 28px;max-width:58ch">
      <div>drop a PDF or a sketch here (or switch to Draw) — the agent extracts the
    silhouette, recreates it as a parametric GDS, and the gate verifies it
    before it reaches the table.</div>
      <div style="margin-top:10px">then just say what you want, in plain words:
    turn knobs, assign layers per primitive, state the device's function
    (&ldquo;hit 8&thinsp;nm FSR&rdquo;), retarget to another stack, simulate.</div>
    </div>`;
    function* all(root) {
      const w = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
      let n;
      while ((n = w.nextNode())) { yield n; if (n.shadowRoot) yield* all(n.shadowRoot); }
    }
    function hasCanvas(root) {
      for (const n of all(root)) if (n.tagName === "CANVAS") return true;
      return false;
    }
    function findChat() {
      for (const n of all(document.body)) {
    if (n.dataset && n.dataset.pxChatRoot) return n;
    if (n.classList && n.classList.contains("flex-col")
        && getComputedStyle(n).maxHeight === "2000px") {
      n.dataset.pxChatRoot = "1";
      return n;
    }
      }
      return null;
    }
    function syncHeight() {
      const chatEl = findChat();
      if (!chatEl) return;
      let rightCol = null;
      let branch = chatEl;
      while (!rightCol) {
    const root = branch.getRootNode();
    const parent = branch.parentElement
      || (root instanceof ShadowRoot ? root.host : null);
    if (!parent || parent === document.documentElement) break;
    if (branch.parentElement) {
      for (const sib of parent.children) {
        if (sib !== branch && hasCanvas(sib)) { rightCol = sib; break; }
      }
    }
    branch = parent;
      }
      const top = chatEl.getBoundingClientRect().top + window.scrollY;
      const vh = Math.max(window.innerHeight - top - 28, 560);
      const rh = rightCol ? rightCol.getBoundingClientRect().height : 0;
      const h = Math.round(Math.max(rh, vh));
      if (chatEl.style.height !== h + "px") {
    chatEl.style.height = h + "px";
    chatEl.style.maxHeight = h + "px";
      }
    }
    function fix() {
      for (const n of all(document.body)) {
    const t = (n.textContent || "").trim();
    if (t === "No messages yet" && n.parentElement
        && !n.parentElement.dataset.pxExplainer) {
      const p = n.parentElement;          // icon + both lines share this parent
      p.dataset.pxExplainer = "1";
      p.innerHTML = EXPLAINER;
    }
    if (n.classList?.contains("cm-placeholder")) {
      if (n.textContent !== PLACEHOLDER) n.textContent = PLACEHOLDER;
    }
      }
      syncHeight();
    }
    function render({ el }) {
      el.style.display = "none";
      fix();
      const mo = new MutationObserver(() => fix());
      mo.observe(document.body, { childList: true, subtree: true });
      window.addEventListener("resize", syncHeight);
      setTimeout(fix, 400);
      setTimeout(fix, 1500);
      setInterval(syncHeight, 2000);   // knob panels grow after fonts/layout settle
    }
    export default { render };
    """

    return ChatChrome, InkTable, KnobPanel, LightTable


@app.cell
def _(PROJECTS, REPO, base64, json, mo, subprocess, tempfile):
    import sys
    import os as _os
    import shutil as _shutil
    import time as _time

    from homi.dispatch import await_pane_ready as _await_pane_ready

    STUDIO_SYSTEM = (
        "You are the PixCell conductor inside `homi studio` (a chat panel; the "
        "human also sees a live device table). Workspace root: "
        f"{REPO}. Python interpreter: {sys.executable}.\n\n"
        "YOU ARE THE ORCHESTRATOR, NEVER THE WORKER. You never write device "
        "geometry yourself, never author or iterate a recreation script in "
        "your own session, never run the recreate loop by hand. Every stage "
        "runs through its homi command, which dispatches a separate contained "
        "worker and gates the result over artifacts: extraction (`homi "
        "extract <pdf> -o projects/<name>`), blind recreation + gate (`homi "
        "generate projects/<name>`), retargeting (`homi retarget ...`), "
        "simulation (draft only — the human presses Start; never auto-start "
        "cloud spend). The ONE exception: adjusting a named parameter or a "
        "layer kwarg of an ALREADY gate-verified projects/<name>/output/"
        "best.py when the human asks — that is the two-hands channel, and the "
        "table re-renders it with the gate's own fidelity math. Creating or "
        "restructuring geometry is always a dispatched blind worker.\n\n"
        "LONG STAGES NEVER BLOCK THE CHAT: launch them with the CLI's own "
        "detach — `homi generate projects/<name> --detach` (likewise extract/"
        "retarget) — which re-execs the stage in a NEW SESSION and returns "
        "immediately; progress streams to the stage log (e.g. projects/"
        "<name>/output/generate.log). NEVER use `nohup ... &` (codex-family "
        "conductors kill the whole process group when a shell call returns — "
        "measured 2026-07-09) and NEVER your harness's background-task "
        "feature (in the studio's headless mode your session ends the moment "
        "you reply, and harness-managed background tasks die with it). "
        "For the same reason you will NOT be notified when a stage finishes "
        "— the disk is the only channel. Reply immediately that the worker "
        "is dispatched; the stage strip and table watch the artifacts and "
        "announce completion to the human. On any later turn, report gate "
        "verdicts only after reading the artifacts (metrics, best.py), "
        "never from memory or a worker's claim.\n\n"
        "FUNCTION: FoM selection resolves from three sources with precedence "
        "human > paper > visual (homi.conductor.fom.resolve_fom); extraction "
        "harvests the paper's own words + reported numbers into "
        "projects/<name>/function.json with a `source` field (conductor-side; "
        "workers never read it); when the human states intent in chat, that "
        "overrides everything — write/update function.json (source: human) "
        "and the spec accordingly, hint-lint before anything reaches a "
        "worker. Keep replies short and concrete; the human is watching an "
        "instrument panel, not reading a report."
    )

    # The agent's memory survives page reloads AND server restarts. Transport
    # resolves like the worker dispatch layer: a visible, steerable conductor
    # pane (cxx, role homi-conductor) when anu/tmux is present; headless
    # `claude -p --resume` as the portable fallback for outsiders.
    # HOMI_STUDIO_STATE_DIR isolates session state (tests, parallel studios);
    # default is the repo's .studio/ as always.
    _state_dir = Path(_os.environ.get("HOMI_STUDIO_STATE_DIR") or (REPO / ".studio"))
    _state_file = _state_dir / "session.json"
    try:
        _saved = json.loads(_state_file.read_text())
    except Exception:  # noqa: BLE001 — absent/corrupt state = fresh session
        _saved = {}
    _session = {"id": _saved.get("id"), "pane": _saved.get("pane"),
                "run_session": _saved.get("run_session"),
                "run_id": _saved.get("run_id")}
    prior_turns = list(_saved.get("history") or [])
    _history = list(prior_turns)

    from homi import workspace as _workspace

    # $TMUX is deliberately not required: pane verbs drive explicit %ids
    # server-wide, so a studio launched from a plain terminal still gets a
    # visible, attachable conductor session.
    PANE_MODE = _workspace.resolve_backend() == "tmux-session"

    def _save_state():
        _state_file.parent.mkdir(parents=True, exist_ok=True)
        _state_file.write_text(json.dumps(
            {"id": _session["id"], "pane": _session.get("pane"),
             "run_session": _session.get("run_session"),
             "run_id": _session.get("run_id"),
             "history": _history[-60:]}, indent=1))

    def _pane(*args, timeout=30):
        return subprocess.run(["pane", *args], cwd=str(REPO),
                              capture_output=True, text=True, timeout=timeout)

    def _pane_status(pid):
        return _pane("status", pid).stdout.strip().split()[0] if pid else "gone"

    def _conductor_is_ours(pid, run_session):
        """tmux RECYCLES pane ids — an id that merely exists may be an
        unrelated pane (the studio once adopted whatever %N happened to live
        there after a restart). Only role + session identity counts."""
        if not (pid and run_session):
            return False
        out = subprocess.run(
            ["tmux", "display-message", "-p", "-t", pid,
             "#{@anu_role} #{session_name}"],
            capture_output=True, text=True, timeout=15,
        )
        return out.returncode == 0 and out.stdout.strip() == f"homi-conductor {run_session}"

    # The chat reply is an ARTIFACT, not a screen-scrape: the pane conductor
    # ends every turn by (over)writing .studio/reply.md, and the studio
    # relays that file — the same artifacts-only channel everything else uses.
    _REPLY_FILE = _state_dir / "reply.md"
    PANE_PROTOCOL = (
        "\n\nPANE PROTOCOL (you run as a tmux pane; the human reads a chat "
        "panel, not your screen): end EVERY turn by writing the exact chat "
        f"reply into {_REPLY_FILE} (overwrite; markdown; the reply only). "
        "The studio relays that file to the chat verbatim."
    )

    def _ensure_conductor():
        pid = _session.get("pane")
        if _conductor_is_ours(pid, _session.get("run_session")):
            return pid
        # never adopt: a recycled %id or a stray role-matching pane in
        # someone else's window is not our conductor. Spawn fresh, into a
        # studio-owned run session (visible: `tmux attach -t <session>`).
        ws = _workspace.open_run("studio", str(_state_dir), slug="conductor",
                                 backend="tmux-session")
        try:
            # spawn INSIDE the cleanup scope: a partial tmux failure must
            # still close the run as failed instead of leaving a `running`
            # registry entry (and possibly a live session) with no owner
            worker = ws.spawn(role="conductor", cli="cxx", cwd=str(REPO))
            pid = worker.target
            # persist the run identity BEFORE the boot/brief steps so a
            # crash between here and readiness still has a recorded owner
            _session["pane"] = pid
            _session["run_session"] = ws.info.session
            _session["run_id"] = ws.info.run_id
            _save_state()
            # `pane status` can read idle while the TUI is still booting; a
            # send fired then is swallowed/TRUNCATED by the raw tty (measured
            # 2026-07-09: the brief cut mid-sentence, so the conductor never
            # learned the reply.md protocol and the chat showed "(no reply)").
            # Only the composer marker means the pane accepts input.
            if not _await_pane_ready(pid, deadline_s=120):
                raise RuntimeError(
                    "conductor pane never became ready — composer not up"
                )
            _pane_turn(pid, "SYSTEM BRIEF — read, then acknowledge per the "
                       "pane protocol:\n" + STUDIO_SYSTEM + PANE_PROTOCOL,
                       timeout=240)
        except BaseException:
            _session["pane"] = _session["run_session"] = _session["run_id"] = None
            _save_state()
            ws.close("failed")  # keeps the session, prints the attach hint
            raise
        return pid

    def _pane_turn(pid, prompt, timeout=2400):
        _REPLY_FILE.parent.mkdir(parents=True, exist_ok=True)
        before = _REPLY_FILE.stat().st_mtime_ns if _REPLY_FILE.exists() else 0
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(prompt)
            msgfile = f.name
        sent = _pane("send", pid, "-f", msgfile, timeout=60)
        if sent.returncode != 0:
            _pane("send", pid, prompt, timeout=60)
        # idle is only trusted once the turn has demonstrably run (working
        # seen, or a fresh reply artifact) — a staged-but-unsubmitted paste
        # reads idle too, so idle-without-evidence gets an Enter nudge.
        saw_working = False
        idle_streak = 0
        last_nudge = _time.time()
        deadline = _time.time() + timeout
        _time.sleep(3)
        while _time.time() < deadline:
            fresh = (_REPLY_FILE.exists()
                     and _REPLY_FILE.stat().st_mtime_ns > before)
            st = _pane_status(pid)
            if st == "working":
                saw_working = True
                idle_streak = 0
            elif st == "approval":  # cxx is full-auto; anything left is safe
                _pane("respond", pid, "yes")
                saw_working = True
                idle_streak = 0
            elif st == "idle":
                # the classifier can read idle for a beat BETWEEN tool
                # renders mid-turn — idle only counts when it is stable
                idle_streak += 1
                if fresh and idle_streak >= 2:
                    break
                if saw_working and idle_streak >= 5:
                    break
                if not saw_working and _time.time() - last_nudge > 12:
                    _pane("send", pid, "", timeout=30)  # submit staged input
                    last_nudge = _time.time()
            _time.sleep(3)
        if (_REPLY_FILE.exists()
                and _REPLY_FILE.stat().st_mtime_ns > before):
            return _REPLY_FILE.read_text().strip() or "(empty reply)"
        # fallback: last assistant block from the visible screen, minus chrome
        screen = _pane("read", pid, "60").stdout
        blocks = [b for b in screen.split("⏺") if b.strip()]
        if len(blocks) > 1:
            _junk = ("⎿", "✻", "·", "Tip:", "───", "❯", "[")
            lines = [ln for ln in blocks[-1].splitlines()
                     if ln.strip() and not ln.strip().startswith(_junk)]
            if lines:
                return "\n".join(lines).strip()[:2000]
        return "(no reply — check the conductor pane)"

    # Headless conductor: a persistent claude/codex session via the same
    # workspace machinery workers use (claude -p --resume, or codex exec
    # resume on claude-less machines). The resume id survives restarts in
    # session.json, so the chat keeps its memory either way.
    _headless = {"worker": None}

    def _headless_turn(prompt):
        w = _headless["worker"]
        first_turn = not _session.get("id")
        if w is None:
            if not (_shutil.which("claude") or _shutil.which("codex")):
                raise RuntimeError(
                    "no conductor available — install Claude Code "
                    "(https://claude.com/claude-code) or Codex, sign in, then "
                    "reload. The light table, knobs, and workbench all "
                    "work without it; only the chat needs an agent CLI."
                )
            ws = _workspace.open_run("studio", str(_state_dir),
                                     slug="conductor", backend="headless")
            w = ws.spawn(role="conductor", cli="cxx", cwd=str(REPO))
            w._session_id = _session.get("id")
            _headless["worker"] = w
        if first_turn:
            prompt = ("SYSTEM BRIEF — read, then follow for every turn:\n"
                      + STUDIO_SYSTEM + "\n\n---\n\n" + prompt)
        w.send(prompt)
        reply = w.wait(2400)
        _session["id"] = w._session_id or _session.get("id")
        return (reply or "").strip() or "(no reply)"

    def _uploads(msg):
        """Every file the human attached, from BOTH wire formats.

        marimo delivers uploads as `parts` file entries (its own types mark
        `attachments` as deprecated in favour of parts) — reading only
        `msg.attachments` silently drops every upload, which is the worst
        possible failure for the studio's headline interaction.
        """
        ups = []
        for att in getattr(msg, "attachments", None) or []:
            ups.append((getattr(att, "name", None) or "upload.bin",
                        getattr(att, "url", "") or ""))
        for part in getattr(msg, "parts", None) or []:
            get = (part.get if isinstance(part, dict)
                   else lambda k, _p=part: getattr(_p, k, None))
            if (get("type") or "") == "file":
                ups.append((get("filename") or "upload.bin", get("url") or ""))
        return ups

    def conductor(messages, config):
        """One chat turn = one conductor turn (pane if available, else -p)."""
        msg = messages[-1]
        text = msg.content if isinstance(msg.content, str) else str(msg.content)
        notes = []
        for name, url in _uploads(msg):
            raw = None
            try:
                if url.startswith("data:") and "," in url:
                    raw = base64.b64decode(url.split(",", 1)[1])
                elif url.startswith(("http://", "https://")):
                    import urllib.request
                    raw = urllib.request.urlopen(url, timeout=30).read()
            except Exception:  # noqa: BLE001 — fall through to the visible note
                raw = None
            if raw is None:
                # never drop an upload silently — tell the conductor so it
                # can tell the human instead of hunting the filesystem
                notes.append(f"[the human attached {name!r} but the studio "
                             f"could not read its payload (url prefix "
                             f"{url[:24]!r}) — tell them it did not arrive]")
                continue
            stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in name.rsplit(".", 1)[0]) or "upload"
            if name.lower().endswith(".pdf"):
                dest = PROJECTS / stem / "paper.pdf"
            else:
                dest = PROJECTS / stem / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
            notes.append(f"[the human uploaded a file; saved to {dest}]")
        prompt = text + ("\n\n" + "\n".join(notes) if notes else "")

        try:
            if PANE_MODE:
                reply = _pane_turn(_ensure_conductor(), prompt)
            else:
                reply = _headless_turn(prompt)
        except Exception as e:  # noqa: BLE001 — the chat must never crash the app
            reply = f"conductor error: {e}"
        _history.append({"you": text, "agent": reply})
        _save_state()
        return reply

    # max_height is only a ceiling — ChatChrome pins the real height to the
    # device column so the history has room to scroll.
    chat = mo.ui.chat(
        conductor,
        allow_attachments=["application/pdf", "image/png", "image/jpeg"],
        max_height=2000,
    )
    return chat, prior_turns


@app.cell
def _(ChatChrome, chat, mo, prior_turns):
    import html as _htm

    _parts = [mo.ui.anywidget(ChatChrome())]
    if prior_turns:
        _rows = "".join(
            f'<div class="h-you">you · {_htm.escape(t.get("you", ""))}</div>'
            f'<div class="h-agent">{_htm.escape(t.get("agent", ""))}</div>'
            for t in prior_turns
        )
        _n = len(prior_turns)
        _parts.append(mo.accordion({
            f"earlier conversation · {_n} turn{'s' if _n != 1 else ''} · same agent session":
                mo.Html(f'<div class="wb studio-history">{_rows}</div>')
        }))
    chat_panel = mo.vstack([*_parts, chat], gap=0.4 if prior_turns else 0.0)
    return (chat_panel,)


@app.cell
def _(mo):
    watch = mo.ui.refresh(default_interval="3s")
    fp_cache = {}
    # mo.state on purpose (the one sanctioned use: breaking tick propagation).
    # The watch drives the fingerprint cell every 3 s; downstream reruns only
    # happen when set_disk fires on a REAL disk change. mo.stop is wrong here
    # — it cancels descendants and blanks their rendered output; and plain
    # propagation recreates every widget per tick, wiping the human's play.
    get_disk, set_disk = mo.state(())
    return fp_cache, get_disk, set_disk, watch


@app.cell
def _(PROJECTS, fp_cache, set_disk, watch):
    # fingerprint EVERY project with an input on disk, not only gate-verified
    # ones — a freshly dropped paper must appear (and its stage ticks move)
    # while extract/generate are still running.
    _ = watch.value
    _sig = []
    for _proj in sorted(PROJECTS.iterdir()) if PROJECTS.exists() else []:
        if not _proj.is_dir():
            continue
        _best = _proj / "output" / "best.py"
        _has_input = ((_proj / "paper.pdf").exists()
                      or (_proj / "device_bw.png").exists())
        if not (_has_input or _best.exists()):
            continue
        _mt = [_proj.stat().st_mtime_ns]
        for _f in (_best, _proj / "device_bw.png", _proj / "footprint.json",
                   _proj / "function.json"):
            if _f.exists():
                _mt.append(_f.stat().st_mtime_ns)
        if _best.parent.exists():
            _mt.append(_best.parent.stat().st_mtime_ns)
            for _sub in _best.parent.iterdir():
                if _sub.is_dir() and _sub.name != "__pycache__":
                    _mt.append(_sub.stat().st_mtime_ns)
        _sig.append((_proj.name, tuple(_mt)))
    _sig = tuple(_sig)
    if fp_cache.get("sig") != _sig:
        fp_cache["sig"] = _sig
        set_disk(_sig)
    return


@app.cell
def _(PROJECTS, get_disk, mo):
    _ = get_disk()
    _verified = sorted(
        (p for p in PROJECTS.glob("*/output/best.py")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    _ver_names = {p.parent.parent.name for p in _verified}
    # in-flight projects (input on disk, nothing promoted yet) ride the same
    # picker — the table shows their target ghost and the stage strip ticks
    # while the workers run.
    _pending = sorted(
        (d for d in (PROJECTS.iterdir() if PROJECTS.exists() else [])
         if d.is_dir() and d.name not in _ver_names
         and ((d / "device_bw.png").exists() or (d / "paper.pdf").exists())),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    _entries = [(_p.stat().st_mtime, _p.parent.parent.name, _p) for _p in _verified]
    _entries += [(_d.stat().st_mtime, f"{_d.name} · in progress", _d)
                 for _d in _pending]
    _entries.sort(key=lambda e: e[0], reverse=True)
    device_options = {label: path for _mt, label, path in _entries}
    picker = (
        mo.ui.dropdown(
            options=list(device_options), value=next(iter(device_options)), label=""
        )
        if device_options
        else None
    )
    return device_options, picker


@app.cell
def _(mo, picker, watch):
    # the watch must be MOUNTED to tick — an unrendered mo.ui.refresh never
    # fires, and the whole live story (agent edits landing, stage ticks
    # greening) rides on it.
    mode = mo.ui.radio(options=["View", "Draw"], value="View", inline=True)
    _head = [mode]
    if picker is not None:
        _head.append(picker)
    _head.append(watch)
    table_head = mo.hstack(_head, gap=1.0, align="center", justify="start")
    return mode, table_head


@app.cell
def _(Path, device_options, json, picker, re):
    # Load the selected device's everything (script, knobs, target, calibration,
    # provenance) — all integrations, no UI logic.
    from homi.weber_integration import analyze_and_configure, get_parameter_info_for_ui

    device = None
    _sel = (Path(device_options[picker.value])
            if picker is not None and picker.value else None)
    if _sel is not None and _sel.is_dir():
        # in-flight project: input on disk, nothing gate-verified yet — the
        # table shows the target ghost and the stage strip ticks while the
        # dispatched workers run.
        _proj = _sel
        _fp = None
        _fpf = _proj / "footprint.json"
        if _fpf.exists():
            _fp = json.loads(_fpf.read_text()).get("footprint_um")
        _function = {}
        _ff = _proj / "function.json"
        if _ff.exists():
            _function = json.loads(_ff.read_text())
        _target = _proj / "device_bw.png"
        device = {
            "name": _proj.name, "proj": _proj, "script": None, "source": None,
            "main": None, "params": [], "function_knobs": [], "provenance": {},
            "target": _target if _target.exists() else None, "calib": None,
            "footprint": _fp, "analysis": None, "component_map": {},
            "slots": [], "function": _function,
        }
    elif _sel is not None:
        _script = _sel
        _source = _script.read_text()
        _analysis, _slots = analyze_and_configure(_source)
        _params = [
            p for p in get_parameter_info_for_ui(_slots)
            if len(re.findall(rf"\b{re.escape(p['name'])}\b", _source)) > 1
        ]
        _m = re.findall(r"@gf\.cell\s*\ndef\s+(\w+)\s*\(", _source)
        _prov, _knobs, _target, _calib = {}, [], None, None
        for _rd in sorted(_script.parent.glob("recreation_*")):
            if (_rd / "metrics_abs.json").exists():
                _mm = json.loads((_rd / "metrics_abs.json").read_text())
                _prov["iou"] = _mm.get("IoU")
            if (_rd / "recreation_log.json").exists():
                _topo = json.loads((_rd / "recreation_log.json").read_text()).get(
                    "topology_reasoning") or {}
                _prov["ident"] = _topo.get("device_identification")
                _knobs = _topo.get("function_defining_knobs") or []
            if (_rd / "calibration.json").exists():
                _calib = json.loads((_rd / "calibration.json").read_text())
            if (_rd / "component.png").exists():
                _target = _rd / "component.png"
        _fp = None
        _fpf = _script.parent.parent / "footprint.json"
        if _fpf.exists():
            _fp = json.loads(_fpf.read_text()).get("footprint_um")
        _function = {}
        _ff = _script.parent.parent / "function.json"
        if _ff.exists():
            _function = json.loads(_ff.read_text())
        device = {
            "name": picker.value, "proj": _script.parent.parent,
            "script": _script, "source": _source,
            "main": _m[-1] if _m else "device", "params": _params,
            "function_knobs": _knobs, "provenance": _prov,
            "target": _target, "calib": _calib, "footprint": _fp,
            "analysis": _analysis,
            "component_map": {s.slot_id: s.component_ids for s in _slots.slots},
            "slots": [(s.slot_id, s.display_name) for s in _slots.slots],
            "function": _function,
        }
    return (device,)


@app.cell
def _(device, mo):
    # Exploration reset — exists only once a gate-verified device is on the
    # table. Clicking recreates the play widgets (knobs + layer dropdowns)
    # at the program's own values; it never touches files.
    reset_btn = (
        mo.ui.run_button(label="reset — back to the verified GDS")
        if device and device["script"] else None
    )
    return (reset_btn,)


@app.cell
def _(device, mo, reset_btn):
    # layers belong to the BUILT program, per primitive — the whole point:
    # you sketch in black and white; you assign layers to the device's parts.
    _ = reset_btn.value if reset_btn is not None else None
    slot_layers = None
    if device and device["slots"]:
        slot_layers = mo.ui.dictionary({
            slot_id: mo.ui.dropdown(
                options={"(1,0)": 1, "(2,0)": 2, "(3,0)": 3},
                value="(1,0)", label=display.lower(),
            )
            for slot_id, display in device["slots"]
        })
    return (slot_layers,)


@app.cell
def _(KnobPanel, device, mo, reset_btn):
    _ = reset_btn.value if reset_btn is not None else None
    knobs = None
    if device and device["source"]:
        _primary = [p for p in device["params"] if p["name"] in set(device["function_knobs"])]
        _rest = [p for p in device["params"] if p["name"] not in set(device["function_knobs"])]
        if not _primary:
            _primary, _rest = _rest, []
        _ordered = _primary + _rest
        knobs = mo.ui.anywidget(KnobPanel(
            knobs=_ordered,
            values={p["name"]: p["default_value"] for p in _ordered},
        ))
    return (knobs,)


@app.cell
def _(Path, device, knobs, slot_layers, tempfile):
    import gdsfactory as gf

    from homi.weber_integration import layer_call_interceptor

    layer_polygons, bbox_um, gds_path, fidelity_gds = {}, (0.0, 0.0), None, None
    if device and knobs is not None:
        _assignments = {}
        if slot_layers is not None:
            _assignments = {
                slot: (int(v), 0)
                for slot, v in slot_layers.value.items()
                if int(v or 1) != 1
            }
        _values = knobs.value.get("values") or {}

        def _build(with_layers):
            try:
                gf.clear_cache()
            except Exception:
                pass
            _ns = {"gf": gf, "gdsfactory": gf, "__name__": "__studio__"}
            _ctx = layer_call_interceptor(
                device["analysis"], device["component_map"],
                _assignments if with_layers else {},
            )
            with _ctx:
                exec(device["source"], _ns)
                for _k, _v in _values.items():
                    # knob widgets emit floats; a script's int tunable (e.g.
                    # ring_slices used in range()) must stay an int — inject
                    # with the script's own declared type
                    _orig = _ns.get(_k)
                    if (isinstance(_orig, int) and not isinstance(_orig, bool)
                            and isinstance(_v, float) and _v.is_integer()):
                        _v = int(_v)
                    _ns[_k] = _v
                return _ns[device["main"]]()

        _component = _build(with_layers=True)
        _raw = _component.get_polygons()
        if isinstance(_raw, dict):
            for _idx, _plist in _raw.items():
                _info = _component.kcl.layout.get_info(_idx)
                _key = str(_info.layer)
                for _poly in _plist:
                    _pts = [[pt.x / 1000.0, pt.y / 1000.0] for pt in _poly.each_point_hull()]
                    if len(_pts) >= 3:
                        layer_polygons.setdefault(_key, []).append(_pts)
        if layer_polygons:
            # the table draws in the gate's scoring frame — one joint
            # translation across every layer, or the ghost/footprint frame
            # misalign on any script whose bbox is not at the origin
            from michaelangelo.core.compare_absolute import gate_frame_offset

            _flat = [pt for plist in layer_polygons.values()
                     for poly in plist for pt in poly]
            _dx, _dy = gate_frame_offset([_flat], device["footprint"])
            layer_polygons = {
                k: [[[x + _dx, y + _dy] for x, y in poly] for poly in plist]
                for k, plist in layer_polygons.items()
            }
        _all = [pt for plist in layer_polygons.values() for poly in plist for pt in poly]
        if _all:
            _xs = [x for x, _ in _all]
            _ys = [y for _, y in _all]
            bbox_um = (max(_xs) - min(_xs), max(_ys) - min(_ys))
        _dir = Path(tempfile.mkdtemp(prefix="studio_gds_"))
        gds_path = _dir / "device.gds"
        _component.write_gds(str(gds_path))

        # fidelity is measured on the layer-1 silhouette; layer assignment
        # never changes geometry, so measure a clean (unassigned) build.
        if _assignments:
            _clean = _build(with_layers=False)
            fidelity_gds = _dir / "device_fidelity.gds"
            _clean.write_gds(str(fidelity_gds))
        else:
            fidelity_gds = gds_path
    return bbox_um, fidelity_gds, layer_polygons


@app.cell
def _(device, fidelity_gds):
    # Fidelity through the CONDUCTOR'S OWN math — zero reimplementation.
    # Measured on the clean layer-1 build (assignments never change geometry).
    from homi.conductor import recompute_metrics

    iou = None
    fits = None
    if device and fidelity_gds and device["target"] and device["calib"]:
        import json as _json
        import tempfile as _tf
        from pathlib import Path as _P

        _cf = _P(_tf.mkdtemp(prefix="studio_calib_")) / "calibration.json"
        _cf.write_text(_json.dumps(device["calib"]))
        try:
            iou = float(recompute_metrics(fidelity_gds, device["target"], _cf)["IoU"])
        except Exception:
            iou = None
    return (iou,)


@app.cell
def _(bbox_um, device, iou):
    fits2 = None
    if device and device["footprint"] and device["script"]:
        fits2 = (bbox_um[0] <= device["footprint"][0] * 1.005
                 and bbox_um[1] <= device["footprint"][1] * 1.005)
    _ = iou
    return (fits2,)


@app.cell
def _(LightTable, base64, device, fits2, iou, layer_polygons, mo):
    table = None
    if device:
        _ghost = ""
        if device["target"]:
            _ghost = "data:image/png;base64," + base64.b64encode(
                device["target"].read_bytes()).decode()
        _c = device["calib"]
        _calib = None
        if _c:
            _calib = {
                "sx": _c["scale_px_per_um"][0], "sy": _c["scale_px_per_um"][1],
                "offx": _c.get("offset", (0, 0))[0], "offy": _c.get("offset", (0, 0))[1],
                "w": _c["image_size_px"][0], "h": _c["image_size_px"][1],
            }
        table = mo.ui.anywidget(LightTable(
            layer_polygons=layer_polygons,
            footprint_um=list(device["footprint"]) if device["footprint"] else None,
            violation=(fits2 is False),
            ghost_data_uri=_ghost,
            calib=_calib,
            iou=iou,
            gate_iou=device["provenance"].get("iou"),
            fits=fits2,
        ))
    return (table,)


@app.cell
def _(device, mo):
    # FUNCTION gauge: FoM resolved from three evidence sources (human > paper
    # > visual, conflicts surfaced) + a stack picker for the tier-0 baseline.
    from homi.conductor.fom import resolve_fom
    from homi.paths import stacks_dir

    fom_plan = None
    stack_pick = None
    if device:
        _fn = device["function"] or {}
        # a human-confirmed dossier credits the human, not the paper
        _human = _fn.get("device_class_text") if _fn.get("source") == "human" else None
        fom_plan = resolve_fom(
            human=_human,
            paper=_fn.get("device_class_text") or None,
            visual=device["provenance"].get("ident"),
            targets=_fn.get("claims") or None,
        )
        # lab checkout data/ when present, else the packaged stack assets
        _stacks = sorted(stacks_dir().glob("*.json"))
        if _stacks and fom_plan:
            stack_pick = mo.ui.dropdown(
                options={p.stem: str(p) for p in _stacks},
                label="baseline on stack",
            )
    return fom_plan, stack_pick


@app.cell
def _(device, fom_plan, knobs, stack_pick):
    # tier-0 baseline eval — the evaluator's own physics, in-process. Only
    # runs when a stack is picked AND the plan carries a concrete target.
    import json as _json

    function_report = None
    if (device and device["script"] and fom_plan and stack_pick is not None
            and stack_pick.value and knobs is not None):
        _ = knobs.value  # re-evaluate when knobs move: function tracks geometry
        from homi.spec_optimization import evaluate

        _spec = fom_plan.spec_template
        _targets = _spec.get("targets") or [_spec.get("target", {})]
        _has_target = all(
            any(t.get(k) is not None for k in ("value", "min", "max"))
            for t in _targets
        )
        if _has_target:
            _stack = _json.loads(open(stack_pick.value).read())
            try:
                function_report = evaluate(device["script"], _stack, _spec)
            except Exception as _e:  # noqa: BLE001 — show, never crash the gauge
                function_report = _e
    return (function_report,)


@app.cell
def _(device, fom_plan, function_report, mo, stack_pick):
    function_panel = mo.Html("")
    if device and fom_plan:
        _src = {"human": "you set this", "paper": "from the paper",
                "visual": "inferred — confirm with the agent"}[fom_plan.source]
        _conf = (f'<div class="wb-fit fail" style="margin-top:4px">'
                 f"{'; '.join(fom_plan.conflicts)}</div>"
                 if fom_plan.conflicts else "")
        if isinstance(function_report, Exception):
            _readout = (f'<div class="wb-fit fail" style="margin-top:6px">'
                        f"eval failed: {str(function_report)[:90]}</div>")
        elif function_report is not None:
            _bits = []
            for _v in function_report.verdicts:
                _val = f"{_v.measured:.3f}" if _v.measured is not None else "—"
                _col = ("var(--resist)" if _v.verdict == "pass"
                        else "var(--violation)" if _v.verdict == "fail"
                        else "var(--graphite)")
                _bits.append(
                    f'<span class="wb-num" style="color:{_col};font-size:15px">'
                    f'{_val}</span> <span class="wb-fit" style="color:{_col}">'
                    f"{_v.metric} · {_v.verdict}</span>")
            _readout = ('<div style="display:flex;gap:22px;flex-wrap:wrap;'
                        'margin-top:6px;align-items:baseline">'
                        + "".join(f"<span>{b}</span>" for b in _bits) + "</div>")
        elif fom_plan.in_loop_tier == 1:
            _readout = ('<div class="wb-fit" style="margin-top:6px;opacity:0.8">'
                        "needs FDTD (cap-gated) · ask the agent to measure</div>")
        else:
            _readout = ('<div class="wb-fit" style="margin-top:6px;opacity:0.8">'
                        "pick a stack to measure the baseline</div>")
        _box = mo.Html(
            '<div class="wb wb-panel"><div class="wb-label">Function</div>'
            '<div style="display:flex;gap:10px;align-items:baseline;flex-wrap:wrap">'
            f'<span style="font-size:13.5px;color:var(--chrome)">{fom_plan.description}</span>'
            f'<span class="wb-num" style="opacity:0.65;font-size:11px">'
            f"{fom_plan.device_class} · {_src}</span></div>"
            f"{_conf}{_readout}</div>"
        )
        _rows = [_box]
        if stack_pick is not None and fom_plan.in_loop_tier == 0:
            _rows.append(stack_pick)
        function_panel = mo.vstack(_rows, gap=0.4)
    return (function_panel,)


@app.cell
def _(InkTable, mo):
    ink = mo.ui.anywidget(InkTable())
    sketch_len = mo.ui.number(value=20.0, step=0.1, label="length (µm)")
    sketch_wid = mo.ui.number(value=5.0, step=0.1, label="width (µm)")
    sketch_name = mo.ui.text(value="sketch1", label="save as project")
    save_btn = mo.ui.run_button(label="Save sketch as project")
    return ink, save_btn, sketch_len, sketch_name, sketch_wid


@app.cell
def _(
    PROJECTS,
    base64,
    ink,
    json,
    mo,
    save_btn,
    sketch_len,
    sketch_name,
    sketch_wid,
):
    save_note = mo.Html("")
    if save_btn.value:
        if not ink.ink_data_uri:
            save_note = mo.Html('<div class="wb wb-fit fail">Draw something first.</div>')
        else:
            _proj = PROJECTS / sketch_name.value
            _proj.mkdir(parents=True, exist_ok=True)
            (_proj / "device_bw.png").write_bytes(
                base64.b64decode(ink.ink_data_uri.split(",", 1)[1]))
            (_proj / "footprint.json").write_text(
                json.dumps({"footprint_um": [sketch_len.value, sketch_wid.value]}))
            save_note = mo.Html(
                f'<div class="wb wb-fit">Saved projects/{sketch_name.value} — now '
                f"tell the agent: “recreate projects/{sketch_name.value}”.</div>"
            )
    save_note
    return


@app.cell
def _(ink, mo, save_btn, sketch_len, sketch_name, sketch_wid):
    draw_view = mo.vstack([
        ink,
        mo.hstack([sketch_len, sketch_wid, sketch_name, save_btn],
                  gap=0.8, align="end", wrap=True),
    ], gap=0.5)
    return (draw_view,)


@app.cell
def _(
    device,
    draw_view,
    function_panel,
    knobs,
    mo,
    mode,
    reset_btn,
    slot_layers,
    table,
    table_head,
):
    if mode.value == "Draw":
        _surface = draw_view
    elif device and table is not None:
        _sections = [table]
        if knobs is not None:
            _sections.append(knobs)
        else:
            _sections.append(mo.Html(
                '<div class="wb wb-fit" style="opacity:0.75">workers running — '
                "the stage strip above ticks as artifacts land; the device "
                "appears here once the gate verifies it.</div>"
            ))
        if slot_layers is not None:
            _sections.append(
                mo.hstack(list(slot_layers.elements.values()), gap=1.0, wrap=True)
            )
        if reset_btn is not None:
            _sections.append(mo.hstack([reset_btn], justify="end"))
        _sections.append(function_panel)
        _surface = mo.vstack(_sections, gap=0.7)
    else:
        _surface = mo.Html(
            '<div class="wb wb-panel">Nothing on the table yet. Drop a paper or a '
            "drawing into the chat — with its footprint in µm and anything else "
            "the agent should know — and the device will appear here once the "
            "gate verifies it.</div>"
        )
    right = mo.vstack([table_head, _surface], gap=0.6)
    return (right,)


@app.cell
def _(chat_panel, mo, right):
    view = mo.hstack([chat_panel, right], widths=[1, 1.35], gap=1.2, align="start")
    view
    return


if __name__ == "__main__":
    app.run()
