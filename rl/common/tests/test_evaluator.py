from __future__ import annotations

import hashlib
import json

import pytest

from rl.common.contracts import VerifierReference, reference_from_row
from rl.common.evaluator import (
    Attribution,
    EvaluationStatus,
    PixCellEvaluator,
)


@pytest.fixture(scope="module")
def evaluator():
    instance = PixCellEvaluator(
        max_workers=4,
        execution_timeout_seconds=15.0,
        evaluator_retries=1,
    )
    yield instance
    instance.close()


def test_ground_truth_self_scores_at_full_precision(core_row, evaluator):
    result = evaluator.evaluate(reference_from_row(core_row), core_row["code"])
    assert result.status is EvaluationStatus.OK
    assert result.iou is not None and result.iou > 0.98
    assert result.dice is not None and result.dice > 0.98
    assert result.iou != round(result.iou, 4)
    assert len(result.metrics["render_sha256"]) == 64
    json.dumps(result.metrics, allow_nan=False)
    assert all(
        type(value) is bool
        for value in result.metrics["render_info"]["size_match"]
    )


def test_purity_rejection_happens_before_execution(core_row, evaluator, tmp_path):
    marker = tmp_path / "must-not-exist"
    source = (
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('executed')\n"
        "import gdsfactory as gf\n"
        "device = gf.components.mzi()\n"
        "device.write_gds('device.gds')\n"
    )
    result = evaluator.evaluate(reference_from_row(core_row), source)
    assert result.status is EvaluationStatus.SOURCE_REJECTED
    assert result.attribution is Attribution.MODEL
    assert not marker.exists()


@pytest.mark.parametrize(
    ("source", "status"),
    [
        ("def broken(:\n  pass", EvaluationStatus.SYNTAX_ERROR),
        ("import gdsfactory as gf\nprint('no output')", EvaluationStatus.NO_GDS),
        (
            "from pathlib import Path\nPath('device.gds').write_bytes(b'bad')",
            EvaluationStatus.BAD_GDS,
        ),
    ],
)
def test_model_failure_classes_are_attributed_to_model(
    core_row,
    evaluator,
    source,
    status,
):
    result = evaluator.evaluate(reference_from_row(core_row), source)
    assert result.status is status
    assert result.attribution is Attribution.MODEL
    assert not result.mask_from_training


def test_runtime_timeout_does_not_poison_next_evaluation(core_row):
    reference = reference_from_row(core_row)
    with PixCellEvaluator(
        max_workers=1,
        execution_timeout_seconds=0.25,
        evaluator_retries=0,
    ) as evaluator:
        timed_out = evaluator.evaluate(reference, "while True:\n    pass")
        assert timed_out.status is EvaluationStatus.RUNTIME_TIMEOUT
        # Cold GDSFactory import takes about ten seconds on the supported
        # macOS development stack. This remains below the production bound.
        evaluator.execution_timeout_seconds = 15.0
        good = evaluator.evaluate(reference, core_row["code"])
        assert good.status is EvaluationStatus.OK


def test_corrupt_reference_is_masked(core_row, evaluator):
    payload = b"not an image"
    reference = VerifierReference(
        payload,
        tuple(core_row["footprint_um"]),
        hashlib.sha256(payload).hexdigest(),
    )
    result = evaluator.evaluate(reference, "pass")
    assert result.status is EvaluationStatus.REFERENCE_ERROR
    assert result.attribution is Attribution.REFERENCE
    assert result.mask_from_training


def test_group_batch_preserves_order(core_row):
    reference = reference_from_row(core_row)
    sources = [
        core_row["code"],
        "def broken(:\n pass",
        "import gdsfactory as gf\nprint('no gds')",
        core_row["code"],
    ]
    with PixCellEvaluator(max_workers=4, evaluator_retries=0) as evaluator:
        results = evaluator.evaluate_many(reference, sources)
    assert [result.status for result in results] == [
        EvaluationStatus.OK,
        EvaluationStatus.SYNTAX_ERROR,
        EvaluationStatus.NO_GDS,
        EvaluationStatus.OK,
    ]
    assert results[0].iou == pytest.approx(results[3].iou, abs=0.0)
    assert results[0].metrics["render_sha256"] == results[3].metrics["render_sha256"]
