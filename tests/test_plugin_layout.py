"""Parity tests for the distributable plugin (plugins/pixcell).

Guards the single-source rule: product skills/agents LIVE in plugins/pixcell/;
.claude/skills and .claude/agents keep only symlinks (plus lab-internal skills,
which stay real directories). Also checks the dual manifests, the marketplace
file, the MCP server declarations, and the pixcell-engine resolver contract
(stderr-only output, documented resolution order).
"""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugins" / "pixcell"
ENGINE = PLUGIN / "bin" / "pixcell-engine"

PRODUCT_SKILLS = [
    "extract",
    "generate",
    "homi",
    "optimize",
    "migrate",
    "simulate",
    "explore",
    "optimize-to-spec",
]
PRODUCT_AGENTS = ["extractor", "optimizer", "pdk-expert", "synthesizer"]
LAB_SKILLS = ["paper-swap", "paper-swap-sweep", "sweep-feasibility", "draw-to-gds"]
MCP_SERVERS = [
    "homi-mj",
    "homi-michaelangelo",
    "homi-raphael",
    "homi-jee",
    "homi-weber",
    "homi-flex",
    "homi-pdk",
]


# ---------------------------------------------------------------- (a) symlinks


def test_product_skills_are_symlinks_into_plugin():
    skills_root = (PLUGIN / "skills").resolve()
    for name in PRODUCT_SKILLS:
        link = REPO / ".claude" / "skills" / name
        assert link.is_symlink(), f".claude/skills/{name} must be a symlink"
        target = link.resolve()
        assert target.parent == skills_root, (
            f".claude/skills/{name} resolves to {target}, not inside plugins/pixcell/skills"
        )
        assert (target / "SKILL.md").is_file(), f"{name}: SKILL.md missing through the symlink"


def test_product_agents_are_symlinks_into_plugin():
    agents_root = (PLUGIN / "agents").resolve()
    for name in PRODUCT_AGENTS:
        link = REPO / ".claude" / "agents" / f"{name}.md"
        assert link.is_symlink(), f".claude/agents/{name}.md must be a symlink"
        target = link.resolve()
        assert target.parent == agents_root, (
            f".claude/agents/{name}.md resolves to {target}, not inside plugins/pixcell/agents"
        )
        assert target.is_file()


def test_lab_only_skills_are_not_in_the_plugin():
    """Lab campaign skills must never ship inside the plugin — they are lab
    machinery, not product surface."""
    for name in ("paper-swap", "paper-swap-sweep", "sweep-feasibility", "draw-to-gds"):
        assert not (PLUGIN / "skills" / name).exists(), name


def test_plugin_mcp_declares_exactly_the_seven_servers():
    data = json.loads((PLUGIN / ".mcp.json").read_text())
    servers = data.get("mcpServers", data)
    assert sorted(servers) == sorted(MCP_SERVERS)
    for name, cfg in servers.items():
        assert cfg["command"] == "${CLAUDE_PLUGIN_ROOT}/bin/pixcell-engine", name
        assert cfg["args"] == [name], f"{name}: args must be exactly [{name!r}]"
        assert cfg.get("type", "stdio") == "stdio", name


# ---------------------------------------------------------- (c) marketplace.json


def test_marketplace_points_at_plugin_dir():
    mp = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    assert mp["name"] == "pixcell"
    assert mp["owner"]["name"] == "QPG-MIT"
    entries = [p for p in mp["plugins"] if p["name"] == "pixcell"]
    assert len(entries) == 1
    assert entries[0]["source"] == "./plugins/pixcell"
    assert (REPO / "plugins" / "pixcell").is_dir()


def test_old_root_plugin_manifest_is_retired():
    assert not (REPO / ".claude-plugin" / "plugin.json").exists(), (
        "the repo-as-plugin root manifest was retired in favor of marketplace.json"
    )


# ------------------------------------------------------------- (d) dual manifests


@pytest.mark.parametrize("rel", [".claude-plugin/plugin.json", ".plugin/plugin.json"])
def test_plugin_manifests_parse_and_name_is_pixcell(rel):
    manifest = json.loads((PLUGIN / rel).read_text())
    assert manifest["name"] == "pixcell"
    assert manifest["version"]
    assert manifest["license"] == "MIT"


# ------------------------------------------------------- (e) no hardcoded .venv


def test_no_skill_or_agent_hardcodes_venv_interpreters():
    """The old hardcoding was `.venv/bin/python -m …` / `.venv/bin/marimo` as
    THE invocation. The CLI entry points (`.venv/bin/homi`, `.venv/bin/pixcell`)
    are allowed as the documented repo-checkout fallback — they are the same
    console scripts any install provides, just addressed relatively."""
    import re

    offenders = []
    allowed = re.compile(r"\.venv/bin/(homi|pixcell)\b")
    for sub in ("skills", "agents"):
        for path in sorted((PLUGIN / sub).rglob("*")):
            if not path.is_file():
                continue
            text = allowed.sub("", path.read_text(encoding="utf-8"))
            if ".venv/bin/" in text:
                offenders.append(str(path.relative_to(REPO)))
    assert not offenders, f"hardcoded .venv/bin/ interpreter in: {offenders}"


# ----------------------------------------------------------- (f) engine hygiene


def test_engine_is_executable():
    assert ENGINE.is_file()
    assert os.access(ENGINE, os.X_OK), "bin/pixcell-engine must be executable"


def test_engine_never_writes_to_stdout():
    """stdout belongs to the MCP protocol: every echo/printf must target stderr."""
    for lineno, line in enumerate(ENGINE.read_text().splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.search(r"(^|[;&|`(\s])(echo|printf)\b", stripped):
            assert ">&2" in stripped, f"line {lineno} writes to stdout: {line!r}"


def test_legacy_hooks_are_retired():
    """The June-era hooks (host-python baseline guards) were deliberately
    dropped from the public plugin; nothing may reintroduce them silently."""
    assert not (PLUGIN / "hooks").exists()


def _fake_engine_venv(root: Path, tag: str) -> Path:
    """Create <root>/.venv with a python stub that accepts -c 'import homi'
    and a fake `homi` console script that announces which venv resolved."""
    bindir = root / ".venv" / "bin"
    bindir.mkdir(parents=True)
    python = bindir / "python"
    python.write_text('#!/bin/sh\nif [ "$1" = "-c" ]; then exit 0; fi\nexit 0\n')
    python.chmod(0o755)
    homi = bindir / "homi"
    homi.write_text(f'#!/bin/sh\necho "RESOLVED:{tag} $*"\n')
    homi.chmod(0o755)
    return bindir


def _run_engine(args, cwd, env_extra):
    env = {
        "PATH": "/usr/bin:/bin",  # no uv, no python3.13 shims
        **env_extra,
    }
    return subprocess.run(
        [str(ENGINE), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_engine_resolves_walkup_venv(tmp_path):
    """Order 2: nearest .venv above cwd that imports homi wins (no uv needed)."""
    _fake_engine_venv(tmp_path / "proj", "walkup")
    nested = tmp_path / "proj" / "deep" / "er"
    nested.mkdir(parents=True)
    home = tmp_path / "home"
    home.mkdir()
    result = _run_engine(["homi", "doctor"], nested, {"HOME": str(home)})
    assert result.returncode == 0, result.stderr
    assert "RESOLVED:walkup doctor" in result.stdout


def test_engine_prefers_pixcell_python_over_walkup(tmp_path):
    """Order 1: $PIXCELL_PYTHON beats a walk-up venv in cwd."""
    _fake_engine_venv(tmp_path / "proj", "walkup")
    explicit_bin = _fake_engine_venv(tmp_path / "explicit", "explicit")
    home = tmp_path / "home"
    home.mkdir()
    result = _run_engine(
        ["homi", "doctor"],
        tmp_path / "proj",
        {"HOME": str(home), "PIXCELL_PYTHON": str(explicit_bin / "python")},
    )
    assert result.returncode == 0, result.stderr
    assert "RESOLVED:explicit doctor" in result.stdout


def test_engine_falls_back_to_cached_plugin_venv(tmp_path):
    """Order 3: ${CLAUDE_PLUGIN_DATA}/venv is used when no project venv exists."""
    data_dir = tmp_path / "plugdata"
    bindir = data_dir / "venv" / "bin"
    bindir.mkdir(parents=True)
    python = bindir / "python"
    python.write_text('#!/bin/sh\nif [ "$1" = "-c" ]; then exit 0; fi\nexit 0\n')
    python.chmod(0o755)
    homi = bindir / "homi"
    homi.write_text('#!/bin/sh\necho "RESOLVED:cached $*"\n')
    homi.chmod(0o755)
    bare = tmp_path / "bare"
    bare.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    result = _run_engine(
        ["homi", "doctor"],
        bare,
        {"HOME": str(home), "CLAUDE_PLUGIN_DATA": str(data_dir)},
    )
    assert result.returncode == 0, result.stderr
    assert "RESOLVED:cached doctor" in result.stdout


def test_engine_python_special_case_execs_interpreter(tmp_path):
    """`pixcell-engine python ...` execs the resolved venv's python itself."""
    bindir = _fake_engine_venv(tmp_path / "proj", "walkup")
    python = bindir / "python"
    python.write_text(
        '#!/bin/sh\n'
        'if [ "$1" = "-c" ] && [ "$2" = "import homi" ]; then exit 0; fi\n'
        'echo "PYTHON-EXEC $*"\n'
    )
    python.chmod(0o755)
    home = tmp_path / "home"
    home.mkdir()
    result = _run_engine(
        ["python", "-m", "homi.spec_optimization"], tmp_path / "proj", {"HOME": str(home)}
    )
    assert result.returncode == 0, result.stderr
    assert "PYTHON-EXEC -m homi.spec_optimization" in result.stdout
