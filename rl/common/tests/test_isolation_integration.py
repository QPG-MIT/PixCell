from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from rl.common.contracts import reference_from_row
from rl.common.evaluator import Attribution, EvaluationStatus, PixCellEvaluator
from rl.common.isolation import IMAGE_ENV


pytestmark = pytest.mark.skipif(
    not os.environ.get(IMAGE_ENV),
    reason=f"{IMAGE_ENV} is required for the real container-boundary test",
)


def _evaluate(core_row, source: str, *, timeout: float):
    with PixCellEvaluator(
        max_workers=1,
        execution_timeout_seconds=timeout,
        evaluator_retries=0,
        require_isolation=True,
    ) as evaluator:
        return evaluator.evaluate(reference_from_row(core_row), source)


def test_real_candidate_boundary_status_and_cleanup(core_row):
    valid = _evaluate(core_row, core_row["code"], timeout=10)
    assert valid.status is EvaluationStatus.OK
    assert valid.iou is not None and valid.iou > 0.98

    spoof = (
        core_row["code"]
        + "\nfrom pathlib import Path\n"
        + "Path('/work/.pixcell-exit-code').write_text('0')\n"
        + "while True: pass\n"
    )
    timed_out = _evaluate(core_row, spoof, timeout=1)
    assert timed_out.status is EvaluationStatus.RUNTIME_TIMEOUT
    assert timed_out.attribution is Attribution.MODEL
    assert not timed_out.retryable

    protected_status = _evaluate(
        core_row,
        "from pathlib import Path\n"
        "Path('/status/exit-code').write_text('0')\n",
        timeout=5,
    )
    assert protected_status.status is EvaluationStatus.RUNTIME_ERROR
    assert protected_status.attribution is Attribution.MODEL
    assert not protected_status.retryable

    killed = _evaluate(
        core_row,
        "import signal\nsignal.raise_signal(signal.SIGKILL)\n",
        timeout=5,
    )
    assert killed.status is EvaluationStatus.SOURCE_REJECTED
    assert killed.attribution is Attribution.MODEL
    assert not killed.retryable
    # Exercise the boundary below the defense-in-depth source policy as well:
    # a future policy escape still cannot convert SIGKILL into a masked
    # evaluator failure.
    with PixCellEvaluator(
        max_workers=1,
        execution_timeout_seconds=5,
        evaluator_retries=0,
        require_isolation=True,
    ) as evaluator:
        assert evaluator.execution_boundary is not None
        with tempfile.TemporaryDirectory(
            prefix="pixcell-signal-test-",
            dir=evaluator.execution_boundary.workspace_root,
        ) as temporary:
            status, _error = evaluator._run_isolated_candidate(
                "import signal\nsignal.raise_signal(signal.SIGKILL)\n",
                Path(temporary),
            )
    assert status is EvaluationStatus.RUNTIME_ERROR

    unreadable = _evaluate(
        core_row,
        core_row["code"]
        + "\nfrom pathlib import Path\nPath('device.gds').chmod(0)\n",
        timeout=10,
    )
    assert unreadable.status is EvaluationStatus.NO_GDS
    assert unreadable.attribution is Attribution.MODEL
    assert not unreadable.retryable

    leftovers = subprocess.check_output(
        [
            "docker",
            "ps",
            "--all",
            "--quiet",
            "--filter",
            "label=org.qpg-mit.pixcell.candidate",
        ],
        text=True,
    ).strip()
    assert not leftovers
