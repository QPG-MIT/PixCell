"""Preflight checks: what can run on THIS machine, and what to install next.

One measure-only module, three consumers: `homi doctor` (the CLI), the studio
masthead banner, and anyone scripting an environment check. Each check returns
(ok, detail, remedy) — remedy is the exact next command, not advice prose.
"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from homi.paths import dotenv_path, projects_dir

GDSFACTORY_PIN = "9.20.7"


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    remedy: str = ""
    # "core" blocks everything; "agent" blocks dispatched stages;
    # "optional" only blocks the stage named in detail
    tier: str = "core"


def _dotenv_keys() -> set[str]:
    """Key names present in the resolved .env (values never leave this function)."""
    env = dotenv_path()
    keys = set()
    if env is not None and env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if v.strip():
                    keys.add(k.strip())
    return keys


def run_checks() -> list[Check]:
    checks: list[Check] = []

    # the supported range mirrors requires-python (>=3.11,<3.14); 3.13 is
    # what the lab pins and what setup.sh prefers
    checks.append(Check(
        "python", (3, 11) <= sys.version_info[:2] <= (3, 13),
        f"{sys.version_info.major}.{sys.version_info.minor} at {sys.executable}",
        "install Python 3.11-3.13 (3.13 recommended) and re-run ./setup.sh",
    ))

    try:
        import gdsfactory
        ok = gdsfactory.__version__ == GDSFACTORY_PIN
        checks.append(Check(
            "gdsfactory", ok, f"{gdsfactory.__version__} (pin {GDSFACTORY_PIN})",
            "" if ok else "pip install gdsfactory==" + GDSFACTORY_PIN
            + "  # 9.3x+ changes the PDK-activation API",
        ))
    except Exception as e:  # noqa: BLE001
        checks.append(Check("gdsfactory", False, f"import failed: {e}",
                            "./setup.sh"))

    try:
        import marimo  # noqa: F401
        checks.append(Check("marimo", True, "studio + workbench available",
                            tier="core"))
    except Exception:  # noqa: BLE001
        checks.append(Check("marimo", False, "not importable",
                            "pip install 'pixcell[workbench]'"))

    # the harness IS the system: a coding-agent CLI runs the workers.
    # Backend resolution is the workspace ladder's (pane+tmux — $TMUX not
    # required; run sessions are attachable from any terminal).
    from homi import workspace as _workspace

    # live probe: preflight must report what dispatch would ACTUALLY do —
    # pane+tmux on PATH with an unreachable server resolves headless
    resolved = _workspace.resolve_backend()
    have_claude = shutil.which("claude") is not None
    have_codex = shutil.which("codex") is not None
    if resolved == "tmux-session":
        backend = "anu tmux sessions (multi-agent capable)"
    elif have_claude and have_codex:
        backend = "claude + codex (headless)"
    elif have_claude:
        backend = "claude (headless)"
    elif have_codex:
        backend = "codex (headless)"
    else:
        backend = "none"
    checks.append(Check(
        "worker backend", backend != "none", backend,
        "" if backend != "none" else
        "install Claude Code (https://claude.com/claude-code) or Codex — "
        "extract/generate/retarget dispatch agent workers through it",
        tier="agent",
    ))

    keys = _dotenv_keys() | {k for k in
                             ("GEMINI_API_KEY", "TIDY3D_API_KEY",
                              "SIMCLOUD_APIKEY") if os.environ.get(k)}
    checks.append(Check(
        "GEMINI_API_KEY", "GEMINI_API_KEY" in keys,
        "extract's B&W standardization (the one API call in perception)",
        "" if "GEMINI_API_KEY" in keys else
        "add GEMINI_API_KEY to .env (https://aistudio.google.com/apikey) — "
        "only `homi extract` needs it",
        tier="optional",
    ))
    _tidy = ("TIDY3D_API_KEY" in keys or "SIMCLOUD_APIKEY" in keys
             or (Path.home() / ".tidy3d" / "config").exists())
    checks.append(Check(
        "tidy3d credential", _tidy,
        "tier-1/2 cloud FDTD (tier-0 mode solves are free + local)",
        "" if _tidy else
        "add TIDY3D_API_KEY to .env — only cloud physics needs it",
        tier="optional",
    ))

    _proj = projects_dir()
    try:
        _proj.mkdir(parents=True, exist_ok=True)
        ok = os.access(_proj, os.W_OK)
    except Exception:  # noqa: BLE001
        ok = False
    checks.append(Check("projects dir", ok, str(_proj),
                        "" if ok else f"make {_proj} writable"))

    return checks


def missing_for_studio() -> list[str]:
    """One-line warnings for the studio masthead — only what's absent.

    Deliberately cheap (no heavy imports): this runs on every studio load,
    and a running studio already proves the core environment.
    """
    warn = []
    have_pane = shutil.which("pane") is not None and shutil.which("tmux") is not None
    if not (have_pane or shutil.which("claude") or shutil.which("codex")):
        warn.append(
            "no agent CLI on PATH — install Claude Code "
            "(https://claude.com/claude-code) or Codex for the chat and "
            "dispatched stages; the light table and knobs work without it"
        )
    if "GEMINI_API_KEY" not in _dotenv_keys() and not os.environ.get("GEMINI_API_KEY"):
        warn.append(
            "GEMINI_API_KEY not set — paper extraction's B&W standardization "
            "will fail; add it to .env (drawing → recreate works without it)"
        )
    return warn


def main() -> int:
    checks = run_checks()
    width = max(len(c.name) for c in checks)
    failures = 0
    for c in checks:
        mark = "✓" if c.ok else ("·" if c.tier == "optional" else "✗")
        print(f" {mark} {c.name:<{width}}  {c.detail}")
        if not c.ok:
            failures += c.tier != "optional"
            if c.remedy:
                print(f"   {'':<{width}}  → {c.remedy}")
    keyless = ("recreation loop, verifier, gate, workbench, and studio "
               "light table run with no API key at all")
    print(f"\n {keyless}.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
