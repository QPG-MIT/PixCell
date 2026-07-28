from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from rl.common.dataset_io import load_tasks
from rl.common.evaluator import (
    Attribution,
    EvaluationResult,
    EvaluationStatus,
)
from rl.common.output import extract_code
from rl.track_a.reward import reward_for, reward_for_policy


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


def test_raw_iou_reward_has_no_validity_floor():
    result = EvaluationResult(
        EvaluationStatus.OK,
        Attribution.MODEL,
        iou=0.401234567891,
    )
    assert reward_for_policy(result, policy="raw_iou") == pytest.approx(
        0.401234567891
    )


@pytest.mark.parametrize("iou", [float("nan"), float("inf"), -0.1, 1.1])
def test_raw_iou_reward_rejects_invalid_measurements(iou):
    result = EvaluationResult(
        EvaluationStatus.OK,
        Attribution.MODEL,
        iou=iou,
    )
    with pytest.raises(ValueError):
        reward_for_policy(result, policy="raw_iou")


def test_paid_sample_is_recorded_before_evaluator_failure(monkeypatch) -> None:
    pytest.importorskip("chz", reason="Tinker is an optional RL dependency")
    pytest.importorskip("tinker", reason="Tinker is an optional RL dependency")
    pytest.importorskip(
        "tinker_cookbook",
        reason="Tinker Cookbook is an optional RL dependency",
    )
    from rl.track_a import tinker_data

    repo_root = Path(__file__).resolve().parents[3]
    task = load_tasks(
        repo_root / "dataset",
        configuration="depth",
        split="train",
    )[0]
    sample_records: list[dict] = []
    evaluated_records: list[dict] = []

    class Tokenizer:
        @staticmethod
        def decode(_tokens):
            return "```python\nprint('sample')\n```"

    class Renderer:
        tokenizer = Tokenizer()

        @staticmethod
        def parse_response(_tokens):
            return (
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "```python\nprint('sample')\n```",
                        }
                    ],
                },
                SimpleNamespace(is_clean=True),
            )

    class FailingBatcher:
        @staticmethod
        async def submit(_reference, _completion):
            return EvaluationResult(
                EvaluationStatus.MEASUREMENT_ERROR,
                Attribution.EVALUATOR,
                retryable=True,
                error="unit evaluator failure",
            )

    monkeypatch.setattr(tinker_data, "_batcher", lambda: FailingBatcher())
    env = tinker_data.TrackAEnv(
        task,
        Renderer(),
        max_image=1920,
        attempt_context={"step": 0, "attempt": 1},
        sample_recorder=lambda value: sample_records.append(dict(value)),
        attempt_recorder=lambda value: evaluated_records.append(dict(value)),
        reward_policy="raw_iou",
    )
    env.prompt_tokens = 123
    with pytest.raises(
        tinker_data.EvaluationInfrastructureError,
        match="unit evaluator failure",
    ):
        asyncio.run(
            env.step(
                [1, 2],
                extra=SimpleNamespace(stop_reason="length"),
            )
        )
    assert len(sample_records) == 1
    assert sample_records[0]["sampling"]["raw_token_ids"] == [1, 2]
    assert sample_records[0]["program"] == "print('sample')"
    assert evaluated_records == []


def _ok(iou: float, dice: float, chamfer: float | None) -> EvaluationResult:
    return EvaluationResult(
        EvaluationStatus.OK,
        Attribution.MODEL,
        iou=iou,
        dice=dice,
        metrics={"chamfer_boundary_um": chamfer},
    )


def _baseline(
    iou_rect: float = 0.5,
    dice_rect: float = 0.6,
    chamfer_rect: float | None = 4.0,
    diag_um: float = 20.0,
):
    from rl.common.baselines import TaskBaseline

    return TaskBaseline(
        iou_rect=iou_rect,
        dice_rect=dice_rect,
        chamfer_rect_boundary_um=chamfer_rect,
        diag_um=diag_um,
    )


def test_shaped_normalizes_iou_against_rectangle():
    # dice at its rect value and chamfer at the rect chamfer: only iou_n pays.
    baseline = _baseline(iou_rect=0.5, dice_rect=0.6, chamfer_rect=4.0)
    result = _ok(iou=0.75, dice=0.6, chamfer=4.0)
    reward = reward_for_policy(result, policy="shaped_v3b", baseline=baseline)
    assert reward == pytest.approx(0.05 + 0.40 * ((0.75 - 0.5) / 0.5))


def test_shaped_rect_equivalent_program_earns_exactly_the_floor():
    baseline = _baseline(iou_rect=0.5, dice_rect=0.6, chamfer_rect=4.0)
    result = _ok(iou=0.5, dice=0.6, chamfer=4.0)
    assert reward_for_policy(
        result, policy="shaped_v3b", baseline=baseline
    ) == pytest.approx(0.05)


def test_shaped_degenerate_target_scores_raw():
    import math as _math

    baseline = _baseline(iou_rect=0.96, dice_rect=0.97, chamfer_rect=0.1, diag_um=20.0)
    result = _ok(iou=0.9, dice=0.92, chamfer=0.5)
    tau = 0.05 * 20.0
    expected = 0.05 + 0.40 * 0.9 + 0.15 * 0.92 + 0.40 * _math.exp(-0.5 / tau)
    assert reward_for_policy(
        result, policy="shaped_v3b", baseline=baseline
    ) == pytest.approx(expected)


def test_shaped_teacher_denominator_floor():
    import math as _math

    # tau = 1.0 (diag 20); t2b = 0.9, t2b_rect = 0.8 -> 0.1 / max(0.2, 0.3)
    baseline = _baseline(
        iou_rect=0.5,
        dice_rect=0.6,
        chamfer_rect=-_math.log(0.8),
        diag_um=20.0,
    )
    result = _ok(iou=0.5, dice=0.6, chamfer=-_math.log(0.9))
    assert reward_for_policy(
        result, policy="shaped_v3b", baseline=baseline
    ) == pytest.approx(0.05 + 0.40 * (0.1 / 0.3))


def test_shaped_model_failures_are_zero_and_faults_are_masked():
    baseline = _baseline()
    crash = EvaluationResult(EvaluationStatus.RUNTIME_ERROR, Attribution.MODEL)
    rejected = EvaluationResult(EvaluationStatus.SOURCE_REJECTED, Attribution.MODEL)
    fault = EvaluationResult(
        EvaluationStatus.MEASUREMENT_ERROR, Attribution.EVALUATOR, retryable=True
    )
    assert reward_for_policy(crash, policy="shaped_v3b", baseline=baseline) == 0.0
    assert reward_for_policy(rejected, policy="shaped_v3b", baseline=baseline) == 0.0
    assert reward_for_policy(fault, policy="shaped_v3b", baseline=baseline) is None


def test_shaped_missing_chamfer_scores_teacher_zero():
    baseline = _baseline(iou_rect=0.5, dice_rect=0.6, chamfer_rect=4.0)
    result = _ok(iou=0.5, dice=0.6, chamfer=None)
    assert reward_for_policy(
        result, policy="shaped_v3b", baseline=baseline
    ) == pytest.approx(0.05)


def test_shaped_requires_a_baseline():
    with pytest.raises(ValueError):
        reward_for_policy(_ok(0.5, 0.5, 1.0), policy="shaped_v3b")


def test_shaped_perfect_program_reaches_one():
    baseline = _baseline(iou_rect=0.3, dice_rect=0.4, chamfer_rect=50.0, diag_um=20.0)
    result = _ok(iou=1.0, dice=1.0, chamfer=0.0)
    assert reward_for_policy(
        result, policy="shaped_v3b", baseline=baseline
    ) == pytest.approx(1.0)
