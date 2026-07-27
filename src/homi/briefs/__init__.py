"""Worker briefs as package data — the single source for all harnesses.

A brief is a payload SENT to a worker agent (pane or headless, Claude or
Codex). Skills and agent definitions are binders that reference these files;
the procedural text lives only here. Brief text is protocol: frozen,
hint-lint-clean (phase briefs), versioned with the verifier it pairs with.
"""

from __future__ import annotations

import re
from importlib import resources
from pathlib import Path

_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


def _root():
    return resources.files(__package__)


def list_briefs() -> list[str]:
    return sorted(p.name[:-3] for p in _root().iterdir() if p.name.endswith(".md"))


def brief_path(name: str) -> Path:
    p = _root() / f"{name}.md"
    if not p.is_file():
        raise KeyError(f"unknown brief: {name} (have: {list_briefs()})")
    return Path(str(p))


def render(name: str, **vars: str) -> str:
    """Render a brief, substituting ``{{VAR}}`` placeholders.

    Raises KeyError for an unknown brief and ValueError listing any
    placeholders left unresolved — a brief is never sent half-rendered.
    """
    text = brief_path(name).read_text()
    text = _PLACEHOLDER.sub(
        lambda m: str(vars[m.group(1)]) if m.group(1) in vars else m.group(0), text
    )
    left = sorted(set(_PLACEHOLDER.findall(text)))
    if left:
        raise ValueError(f"unresolved placeholders in {name}: {left}")
    return text
