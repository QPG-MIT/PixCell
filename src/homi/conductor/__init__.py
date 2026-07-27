"""Conductor tooling — the paper's protocol, released as code.

The conductor briefs workers, never teaches (hint_lint), verifies the
configuration it launched (readback), services measurement requests under
caps (measure, tier1), and accepts artifacts only through the deterministic
gate. Promoted from ``data/agents/paper_swap/RUNBOOK.md`` prose and
the retired paper-swap Workflow JS.
"""

from homi.conductor.gate import (  # noqa: F401
    GateResult,
    knob_response,
    purity_violations,
    recompute_metrics,
    verify_cell,
)
from homi.conductor.hint_lint import DEFAULT_FORBIDDEN, lint  # noqa: F401
from homi.conductor.measure import CapLedger, MeasureRequest, parse_request, staleness_ok  # noqa: F401
from homi.conductor.readback import parse_status_line, verify as verify_readback  # noqa: F401
