"""Harness for the studio Playwright suite.

Launches `marimo run src/homi/studio_app.py` against a sandboxed projects
directory (HOMI_PROJECTS_DIR) and isolated session state
(HOMI_STUDIO_STATE_DIR), with TMUX stripped so the studio takes the headless
(outsider) conductor path, and a fake `claude` shim on PATH so chat turns are
deterministic and free. Skips cleanly when playwright or its chromium build
is not installed (install: `pip install -e .[dev] && playwright install
chromium`).
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DEVTEST = REPO / "projects" / "devtest7"
# devtest7 is an untracked lab artifact; example_mmi_splitter is TRACKED and
# structurally identical (gate-verified best.py + recreation dir with
# metrics/calibration) — fresh clones run the verified-device tests on it.
EXAMPLE = REPO / "projects" / "example_mmi_splitter"
FIXTURE = DEVTEST if (DEVTEST / "output" / "best.py").exists() else EXAMPLE

# A tiny but structurally valid single-page PDF — the studio only saves the
# bytes; nothing in the upload path parses them.
MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 72 72]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def make_fake_claude(bindir: Path, capture: Path) -> None:
    """A `claude` stand-in: records the -p prompt, answers instantly."""
    bindir.mkdir(parents=True, exist_ok=True)
    shim = bindir / "claude"
    shim.write_text(
        "#!/bin/bash\n"
        f"printf '%s\\n' \"$2\" >> {capture}\n"
        + "echo '"
        + json.dumps({"result": "fake-conductor reply: received.",
                      "session_id": "test-session"})
        + "'\n"
    )
    shim.chmod(0o755)


def seed_verified_project(projects: Path) -> None:
    """Minimal copy of a real gate-verified project (devtest7 or the tracked example)."""
    src = FIXTURE
    dst = projects / "devtest7"
    (dst / "output").mkdir(parents=True)
    for f in ("device_bw.png", "footprint.json", "function.json"):
        if (src / f).exists():
            shutil.copy(src / f, dst / f)
    shutil.copy(src / "output" / "best.py", dst / "output" / "best.py")
    for rd in sorted((src / "output").glob("recreation_*")):
        rdd = dst / "output" / rd.name
        rdd.mkdir()
        for f in ("metrics_abs.json", "calibration.json", "component.png",
                  "recreation_log.json"):
            if (rd / f).exists():
                shutil.copy(rd / f, rdd / f)
        break


def seed_inflight_project(projects: Path) -> None:
    """A project mid-pipeline: task pair on disk, nothing promoted."""
    dst = projects / "inflight_smoke"
    dst.mkdir(parents=True)
    shutil.copy(FIXTURE / "device_bw.png", dst / "device_bw.png")
    shutil.copy(FIXTURE / "footprint.json", dst / "footprint.json")


class StudioServer:
    def __init__(self, url: str, projects: Path, capture: Path):
        self.url = url
        self.projects = projects
        self.capture = capture


@pytest.fixture(scope="module")
def studio_factory(tmp_path_factory):
    """Start a sandboxed studio; one server per requested seeding."""
    procs = []

    def start(seed=None, fake_claude=True) -> StudioServer:
        root = tmp_path_factory.mktemp("studio")
        projects = root / "projects"
        projects.mkdir()
        state = root / "state"
        shim = root / "bin"
        capture = root / "claude_prompts.log"
        if fake_claude:
            make_fake_claude(shim, capture)
        else:
            shim.mkdir(parents=True, exist_ok=True)
        if seed:
            seed(projects)
        port = _free_port()
        env = dict(os.environ)
        env.pop("TMUX", None)
        # outsider mode must be PINNED, not inferred: the backend ladder no
        # longer needs $TMUX (pane verbs drive explicit %ids), so on a lab
        # machine an unpinned studio would find the real tmux server and
        # spawn a REAL conductor session mid-test (happened 2026-07-11).
        env["HOMI_BACKEND"] = "headless"
        env["HOMI_PROJECTS_DIR"] = str(projects)
        env["HOMI_STUDIO_STATE_DIR"] = str(state)
        env["HOMI_STATE_DIR"] = str(root / "homi-state")  # run registry sandbox
        if fake_claude:
            env["PATH"] = f"{shim}:{env['PATH']}"
        else:
            # strip every dir that carries an agent CLI — the no-backend case
            import shutil as _sh
            keep = []
            for d in env["PATH"].split(":"):
                if any((Path(d) / b).exists() for b in ("claude", "codex", "pane")):
                    continue
                keep.append(d)
            env["PATH"] = ":".join(keep)
        proc = subprocess.Popen(
            [sys.executable, "-m", "marimo", "run", "src/homi/studio_app.py",
             "--port", str(port), "--headless", "--no-token"],
            cwd=str(REPO), env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        procs.append(proc)
        url = f"http://127.0.0.1:{port}/"
        import urllib.request
        for _ in range(60):
            try:
                urllib.request.urlopen(url, timeout=1)
                break
            except Exception:
                time.sleep(1)
        else:
            proc.terminate()
            pytest.fail("studio server did not come up")
        return StudioServer(url, projects, capture)

    yield start
    for p in procs:
        p.terminate()
    for p in procs:
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception:
            pytest.skip("chromium not installed — run `playwright install chromium`")
        yield b
        b.close()


@pytest.fixture()
def page(browser):
    pg = browser.new_page(viewport={"width": 1680, "height": 1050})
    yield pg
    pg.close()


def deep_text(page) -> str:
    """innerText plus every shadow root's text (anywidget/marimo chrome)."""
    return page.evaluate(
        """() => {
        const out = [document.body.innerText];
        for (const n of document.querySelectorAll('*'))
          if (n.shadowRoot) out.push(n.shadowRoot.textContent || '');
        return out.join('\\n');
        }"""
    )
