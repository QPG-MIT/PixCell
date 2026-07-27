"""Status-line readback — the only reliable worker-config check.

Measured 2026-07-03 (RUNBOOK anti-cheat appendix): ``claude --model
claude-opus-4-1`` silently remaps to Opus 4.8, and headless ``-p`` probes
answer "ok" under the remapped id. Launch flags therefore do not validate
identity; the pane's status line does. This gate caught three mislabeled
panes on its first sweep outing. Verify BEFORE briefing.
"""

from __future__ import annotations

import re

# codex status line: "gpt-5.4 medium", "gpt-5.3-codex-spark medium"
_CODEX = re.compile(r"\b(gpt-[\w.\-]+?)(?:\s+(low|medium|high|xhigh|max))?\b(?=\s|$)")
# claude status line: "Opus 4.8", "Sonnet 4.5 · medium", "Haiku 4.5"
_CLAUDE = re.compile(
    r"\b(Opus|Sonnet|Haiku|Fable)\s+([\d.]+)(?:\s*[·\-]\s*(low|medium|high|xhigh|max))?"
)
_EFFORT = re.compile(r"\b(low|medium|high|xhigh|max)\b")


def parse_status_line(pane_text: str) -> dict:
    """Extract {model, effort} from a pane screen dump (best-effort)."""
    m = _CLAUDE.search(pane_text)
    if m:
        effort = m.group(3)
        if effort is None:
            e = _EFFORT.search(pane_text)
            effort = e.group(1) if e else None
        return {"model": f"{m.group(1)} {m.group(2)}", "effort": effort}
    m = _CODEX.search(pane_text)
    if m:
        effort = m.group(2)
        if effort is None:
            e = _EFFORT.search(pane_text[m.end():])
            effort = e.group(1) if e else None
        return {"model": m.group(1), "effort": effort}
    return {"model": None, "effort": None}


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def verify(pane_text: str, expect_model: str, expect_effort: str | None = None) -> bool:
    """True iff the pane's status line is consistent with the requested config.

    Model: the shown model must be a normalized substring match of the
    requested id (``Opus 4.8`` ⊂ ``claude-opus-4-8``). Effort: fails only on a
    contradiction — a pane that shows no effort is accepted (some CLIs omit
    it; SWEEP_STATE: verify via /status if ambiguous).
    """
    parsed = parse_status_line(pane_text)
    if not parsed["model"]:
        return False
    shown = _normalize(parsed["model"])
    wanted = _normalize(expect_model)
    if shown not in wanted and wanted not in shown:
        return False
    if expect_effort and parsed["effort"] and parsed["effort"] != expect_effort:
        return False
    return True
