"""Env-first, install-safe path resolution.

Every surface (CLI, studio, MCP servers, API) resolves its roots here — never
by walking ``__file__`` parents, which breaks the moment the package is
installed outside a checkout (uvx / pip / uv tool).

Resolution order, everywhere:
  1. explicit env override (``HOMI_ROOT``, ``HOMI_PROJECTS_DIR``)
  2. the checkout root, when running from one (editable install / repo cwd)
  3. an installed-package fallback (platformdirs user dir; ``~/.pixcell/env``)
"""

import os
from pathlib import Path

# The distribution rename (homi -> pixcell) keeps both markers valid.
_CHECKOUT_MARKERS = ('name = "pixcell"', 'name = "homi"')


def _is_checkout_root(candidate: Path) -> bool:
    pj = candidate / "pyproject.toml"
    if not pj.is_file():
        return False
    try:
        text = pj.read_text(encoding="utf-8")
    except OSError:
        return False
    return any(marker in text for marker in _CHECKOUT_MARKERS)


def _walk_up_for_checkout(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if _is_checkout_root(candidate):
            return candidate
    return None


def _package_anchor() -> Path:
    """Where the homi package actually lives (separable for tests)."""
    return Path(__file__).resolve().parent


def repo_root() -> Path | None:
    """Return the checkout root when running from a checkout, else ``None``.

    A checkout is a directory holding a ``pyproject.toml`` whose distribution
    is pixcell/homi, found by walking up from the installed package location
    (editable install) and from the current working directory (repo cwd with
    a non-editable install).
    """
    found = _walk_up_for_checkout(_package_anchor())
    if found is not None:
        return found
    return _walk_up_for_checkout(Path.cwd())


def workspace_root() -> Path:
    """The writable root for projects/state.

    ``$HOMI_ROOT`` -> checkout root -> platformdirs user data dir.
    Always returns a path (unlike :func:`repo_root`).
    """
    override = os.environ.get("HOMI_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    checkout = repo_root()
    if checkout is not None:
        return checkout
    import platformdirs

    return Path(platformdirs.user_data_dir("pixcell"))


def projects_dir() -> Path:
    """The projects directory (created if missing).

    ``HOMI_PROJECTS_DIR`` overrides the default ``workspace_root()/projects``
    — used by the studio test harness to run against a sandbox, and available
    to users who keep device projects outside the workspace.
    """
    override = os.environ.get("HOMI_PROJECTS_DIR")
    if override:
        path = Path(override).expanduser().resolve()
    else:
        path = workspace_root() / "projects"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # unwritable location surfaces at use; doctor reports it
    return path


def dotenv_path() -> Path | None:
    """Locate the ``.env`` file, or ``None``.

    Upward search from cwd (python-dotenv), then the checkout ``.env``,
    then ``~/.pixcell/env``.
    """
    from dotenv import find_dotenv

    found = find_dotenv(usecwd=True)
    if found:
        return Path(found)
    checkout = repo_root()
    if checkout is not None and (checkout / ".env").is_file():
        return checkout / ".env"
    fallback = Path.home() / ".pixcell" / "env"
    if fallback.is_file():
        return fallback
    return None


def load_env() -> Path | None:
    """Load env vars from :func:`dotenv_path` (no-op when absent).

    Returns the path loaded, or ``None``. Never overrides variables already
    set in the process environment (python-dotenv default).
    """
    path = dotenv_path()
    if path is not None:
        from dotenv import load_dotenv

        load_dotenv(path)
    return path


def stacks_dir() -> Path:
    """Canonical layer-stack JSONs (soi220/sin400/tfln400).

    The lab checkout's ``data/agents/pdk_swap/stacks`` when present (the
    campaign source of truth), else the copies shipped as package data.
    """
    checkout = repo_root()
    if checkout is not None:
        lab = checkout / "data" / "agents" / "pdk_swap" / "stacks"
        if lab.is_dir():
            return lab
    return Path(__file__).resolve().parent / "assets" / "stacks"


def michaelangelo_dir() -> Path:
    """Module-anchored michaelangelo package dir (never a repo-relative path)."""
    import michaelangelo

    return Path(michaelangelo.__file__).parent
