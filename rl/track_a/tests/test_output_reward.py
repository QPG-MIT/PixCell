from __future__ import annotations

import pytest

from rl.common.evaluator import (
    Attribution,
    EvaluationResult,
    EvaluationStatus,
)
from rl.common.output import extract_code
from rl.track_a.reward import reward_for


def test_extract_code_handles_reasoning_and_last_fence():
    text = (
        "<think>private scratch</think>\n"
        "```python\nprint('wrong')\n```\n"
        "```python\nimport gdsfactory as gf\nc.write_gds('device.gds')\n```"
    )
    assert extract_code(text).startswith("import gdsfactory")


def test_reward_is_full_precision_direct_iou():
    result = EvaluationResult(
        EvaluationStatus.OK,
        Attribution.MODEL,
        iou=0.401234567891,
        dice=0.5,
    )
    assert reward_for(result) == pytest.approx(0.05 + 0.95 * 0.401234567891)


def test_only_model_failures_become_zero():
    model = EvaluationResult(EvaluationStatus.NO_GDS, Attribution.MODEL)
    evaluator = EvaluationResult(
        EvaluationStatus.MEASUREMENT_ERROR,
        Attribution.EVALUATOR,
        retryable=True,
    )
    reference = EvaluationResult(
        EvaluationStatus.REFERENCE_ERROR,
        Attribution.REFERENCE,
    )
    assert reward_for(model) == 0.0
    assert reward_for(evaluator) is None
    assert reward_for(reference) is None
