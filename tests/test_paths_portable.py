"""Portable path resolution: env-first overrides, checkout detection,
installed-package (no-checkout) fallbacks. Guards the uvx install story —
`pixcell doctor` from a bare install must never derive paths from
``__file__`` walks that assume a repo checkout.
"""

import os
from pathlib import Path

import pytest

from homi import paths

WORKTREE = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- repo_root

def test_repo_root_finds_checkout(monkeypatch):
    """Running from the checkout (editable install), repo_root() is the
    worktree root — the dir holding pyproject.toml with our dist name."""
    monkeypatch.delenv("HOMI_ROOT", raising=False)
    root = paths.repo_root()
    assert root == WORKTREE
    assert (root / "pyproject.toml").is_file()


def test_repo_root_none_outside_checkout(monkeypatch, tmp_path):
    """No checkout above the package or the cwd => None (not a crash)."""
    monkeypatch.chdir(tmp_path)
    # Simulate a wheel install: the package walk finds nothing.
    monkeypatch.setattr(paths, "_package_anchor", lambda: tmp_path / "site-packages" / "homi")
    assert paths.repo_root() is None


# ----------------------------------------------------------- workspace_root

def test_workspace_root_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("HOMI_ROOT", str(tmp_path))
    assert paths.workspace_root() == tmp_path.resolve()


def test_workspace_root_checkout_default(monkeypatch):
    monkeypatch.delenv("HOMI_ROOT", raising=False)
    assert paths.workspace_root() == WORKTREE


def test_workspace_root_no_checkout_falls_back_to_user_dir(monkeypatch, tmp_path):
    """tmp cwd + HOMI_ROOT unset + no checkout => platformdirs user data dir."""
    import platformdirs

    monkeypatch.delenv("HOMI_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda: None)
    assert paths.workspace_root() == Path(platformdirs.user_data_dir("pixcell"))


# ------------------------------------------------------------- projects_dir

def test_projects_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("HOMI_PROJECTS_DIR", str(tmp_path / "proj"))
    assert paths.projects_dir() == (tmp_path / "proj").resolve()


def test_projects_dir_under_workspace_root(monkeypatch, tmp_path):
    monkeypatch.delenv("HOMI_PROJECTS_DIR", raising=False)
    monkeypatch.setenv("HOMI_ROOT", str(tmp_path))
    got = paths.projects_dir()
    assert got == tmp_path.resolve() / "projects"
    assert got.is_dir()  # mkdir ok


# ------------------------------------------------------------------- dotenv

def test_dotenv_path_upward_search_from_cwd(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("HOMI_TEST_SENTINEL=1\n")
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    assert paths.dotenv_path() == env


def test_dotenv_path_checkout_fallback(monkeypatch, tmp_path):
    """cwd search misses => the checkout .env (when one exists)."""
    monkeypatch.chdir(tmp_path)
    fake_root = tmp_path / "checkout"
    fake_root.mkdir()
    (fake_root / ".env").write_text("X=1\n")
    monkeypatch.setattr(paths, "repo_root", lambda: fake_root)
    assert paths.dotenv_path() == fake_root / ".env"


def test_dotenv_path_pixcell_home_fallback(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda: None)
    fake_home = tmp_path / "home"
    (fake_home / ".pixcell").mkdir(parents=True)
    (fake_home / ".pixcell" / "env").write_text("Y=1\n")
    monkeypatch.setenv("HOME", str(fake_home))
    assert paths.dotenv_path() == fake_home / ".pixcell" / "env"


def test_dotenv_path_none_when_nothing_exists(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda: None)
    monkeypatch.setenv("HOME", str(tmp_path / "nohome"))
    assert paths.dotenv_path() is None


def test_load_env_loads_values(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("HOMI_TEST_LOAD_ENV_SENTINEL=yes\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("HOMI_TEST_LOAD_ENV_SENTINEL", raising=False)
    loaded = paths.load_env()
    assert loaded == env
    assert os.environ.get("HOMI_TEST_LOAD_ENV_SENTINEL") == "yes"


def test_load_env_no_crash_when_absent(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(paths, "repo_root", lambda: None)
    monkeypatch.setenv("HOME", str(tmp_path / "nohome"))
    assert paths.load_env() is None


# --------------------------------------------------------------- stacks_dir

CANONICAL_STACKS = ["sin400.json", "soi220.json", "tfln400.json"]


def test_packaged_stacks_enumerable():
    """The canonical layer stacks ship as package data (installed runs)."""
    import importlib.resources as ir

    stacks = ir.files("homi") / "assets" / "stacks"
    names = sorted(p.name for p in stacks.iterdir() if p.name.endswith(".json"))
    assert names == CANONICAL_STACKS


@pytest.mark.skipif(
    not (WORKTREE / "data" / "agents" / "pdk_swap" / "stacks").is_dir(),
    reason="lab data/ not present (slimmed export) — packaged fallback covers it",
)
def test_stacks_dir_checkout_prefers_lab_data():
    d = paths.stacks_dir()
    assert d == WORKTREE / "data" / "agents" / "pdk_swap" / "stacks"
    assert sorted(p.name for p in d.glob("*.json")) == CANONICAL_STACKS


def test_stacks_dir_packaged_fallback_without_checkout(monkeypatch):
    """No checkout (no data/ dir) => the packaged assets still glob."""
    monkeypatch.setattr(paths, "repo_root", lambda: None)
    d = paths.stacks_dir()
    assert sorted(p.name for p in d.glob("*.json")) == CANONICAL_STACKS
    assert d != WORKTREE / "data" / "agents" / "pdk_swap" / "stacks"


def test_packaged_example_seed_present():
    """A minimal example project ships with the package (studio first-run)."""
    import importlib.resources as ir

    example = ir.files("homi") / "assets" / "example"
    names = {p.name for p in example.iterdir()}
    assert {"device_bw.png", "footprint.json", "best.py"} <= names


# ------------------------------------------------------------ no stray roots

def test_no_stray_root_derivations():
    """Only homi/paths.py may derive a root from ``__file__`` parent walks.

    ``parents[2]`` / ``parents[3]`` on ``__file__`` is the repo-root
    derivation that breaks installed (non-checkout) runs — every such site
    must route through homi.paths instead.
    """
    src = WORKTREE / "src"
    offenders = []
    for py in src.rglob("*.py"):
        if "egg-info" in py.parts or ".egg-info" in str(py):
            continue
        if py == src / "homi" / "paths.py":
            continue
        text = py.read_text(encoding="utf-8", errors="replace")
        if "parents[2]" in text or "parents[3]" in text:
            offenders.append(str(py.relative_to(src)))
    assert not offenders, f"stray repo-root derivations: {offenders}"


def test_no_relative_venv_spawns():
    """No Python module under src/ spawns a checkout-relative `.venv/bin/...`.

    Subprocess spawns anchor on ``sys.executable`` (its bin dir for console
    scripts like marimo) so installed runs work. Prose-only mentions are
    allowlisted: worker briefs (follow-up var), a docstring, venv-activation
    advice in error messages.
    """
    src = WORKTREE / "src"
    allowed = {
        "homi/studio_app.py",        # conductor brief text, not a spawn
        "homi/conductor/tier1.py",   # module docstring usage line
        "benchmarking/runner.py",    # "source .venv/bin/activate" advice
    }
    offenders = []
    for py in src.rglob("*.py"):
        if "egg-info" in str(py):
            continue
        rel = str(py.relative_to(src))
        if "briefs" in py.parts or rel in allowed:
            continue
        text = py.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if ".venv/bin/" in line and not line.lstrip().startswith("#"):
                offenders.append(f"{rel}:{i}")
    assert not offenders, f"checkout-relative venv spawns: {offenders}"
