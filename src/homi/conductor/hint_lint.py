"""Pre-dispatch hint lint — *workers derive; conductors never teach.*

Promoted from RUNBOOK step 8 (anti-cheat appendix): before any brief, spec,
or stack file reaches a worker, grep it for the conductor's own device-class /
mechanism / formula vocabulary. Any hit blocks dispatch — the blind protocol's
measurement is void if the conductor names what the worker is supposed to
derive.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

#: Device-class and mechanism vocabulary the conductor knows and must not leak.
DEFAULT_FORBIDDEN: tuple[str, ...] = (
    "mzi",
    "mach-zehnder",
    "ring",
    "racetrack",
    "resonator",
    "coupler",
    "splitter",
    "mmi",
    "bragg",
    "grating",
    "crossing",
    "interferometer",
    "fsr",
    "free spectral range",
    "evanescent",
    "supermode",
    "beat length",
)


def lint(text: str, forbidden: Sequence[str] = DEFAULT_FORBIDDEN) -> list[str]:
    """Return forbidden terms present in ``text`` (case-insensitive, whole-word).

    Empty list = clean = dispatchable. Multi-word terms match literally;
    single words match on word boundaries (so ``splitter_meta.json`` — an
    identifier, not a classification — does not trip ``splitter``).
    """
    low = text.lower()
    hits: list[str] = []
    for term in forbidden:
        if re.search(rf"\b{re.escape(term)}\b", low):
            hits.append(term)
    return hits
