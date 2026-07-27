"""The conductor-serviced measurement loop (Phase B) — protocol primitives.

Workers never run cloud jobs. They end a turn with
``MEASURE <stack>: fixture=<path> predicted_T=<x>`` and block; the conductor
gates the request (staleness, caps), runs the capped tier-1 FDTD harness, and
replies with the measured numbers. Promoted from RUNBOOK steps 4-5 and the
anti-cheat appendix.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re

_MEASURE = re.compile(r"MEASURE\s+(\w+):\s*fixture=(\S+)\s+predicted_T=([-+\d.eE]+)")


@dataclass(frozen=True)
class MeasureRequest:
    stack: str
    fixture: str
    predicted: float


def parse_request(text: str) -> MeasureRequest | None:
    """Parse the FRESHEST measurement request in the text (last match).

    Poller discipline: whole-screen greps re-match stale requests in
    scrollback — callers should pass the fresh tail; we additionally take the
    last match.
    """
    matches = list(_MEASURE.finditer(text))
    if not matches:
        return None
    m = matches[-1]
    return MeasureRequest(stack=m.group(1), fixture=m.group(2), predicted=float(m.group(3)))


def staleness_ok(fixture_gds: Path | str, sources: list[Path] | tuple[Path, ...]) -> bool:
    """The fixture GDS must be newer than every source that generates it.

    A stale fixture measures the previous geometry and returns confidently
    identical numbers — void data at full price (RUNBOOK, paid for once).
    """
    gds_mtime = Path(fixture_gds).stat().st_mtime
    return all(gds_mtime > Path(src).stat().st_mtime for src in sources)


class CapLedger:
    """Per-stack tier-1 call caps — the budget is real and set at launch."""

    def __init__(self, per_stack: int = 3):
        self.per_stack = per_stack
        self._spent: Counter[str] = Counter()

    def remaining(self, stack: str) -> int:
        return max(0, self.per_stack - self._spent[stack])

    def spend(self, stack: str) -> bool:
        """Consume one call if the cap allows; False when exhausted."""
        if self.remaining(stack) <= 0:
            return False
        self._spent[stack] += 1
        return True


def _default_sources(fixture: Path) -> list[Path]:
    """The fixture's generating script, when it sits beside the GDS."""
    py = fixture.with_suffix(".py")
    return [py] if py.exists() else []


def service_loop(send, wait, ledger: CapLedger, run_tier1, *, max_rounds: int = 50) -> str:
    """Drive the Phase-B conductor-serviced measurement handshake.

    ``send(text)`` delivers a message into the worker; ``wait()`` blocks until
    the worker's turn ends and returns the fresh output tail; ``run_tier1(req)``
    runs the capped FDTD and returns the measured dict (it may raise — the
    error text is relayed, the call IS consumed). Gates, in order: staleness
    (declined, cap NOT consumed — a stale fixture is void data at full price),
    cap (declined when exhausted). Returns the final output tail (the
    ``PHASE_B DONE`` turn, or the last turn if the worker stops requesting).
    """
    import json as _json

    out = wait()
    for _ in range(max_rounds):
        if "PHASE_B DONE" in out or "PHASE_B BLOCKED" in out:
            return out
        req = parse_request(out)
        if req is None:
            return out
        fixture = Path(req.fixture)
        sources = _default_sources(fixture)
        if not fixture.exists():
            send(f"MEASURE DECLINED {req.stack}: fixture not found at {req.fixture} "
                 "(call not consumed). Fix the path and request again.")
            out = wait()
            continue
        if sources and not staleness_ok(fixture, sources):
            send(f"MEASURE DECLINED {req.stack}: fixture GDS is OLDER than its source "
                 "(stale geometry = void data). Rebuild the fixture and request again "
                 "(call not consumed).")
            out = wait()
            continue
        if not ledger.spend(req.stack):
            send(f"MEASURE DECLINED {req.stack}: per-stack call cap exhausted "
                 f"({ledger.per_stack}). Close the stack honestly with what you have.")
            out = wait()
            continue
        try:
            measured = run_tier1(req)
            send(f"MEASURED {req.stack}: {_json.dumps(measured)} "
                 f"(calls remaining: {ledger.remaining(req.stack)})")
        except Exception as e:  # noqa: BLE001 — relay the failure; the call is consumed
            send(f"MEASURE FAILED {req.stack}: {e} "
                 f"(call consumed; remaining: {ledger.remaining(req.stack)})")
        out = wait()
    return out
