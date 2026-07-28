"""The Env pays the shaped reward with the task's own rectangle baseline."""

from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("tinker", reason="Tinker SDK env not installed")
pytest.importorskip("chz", reason="chz env not installed")

from rl.common.baselines import cached_rect_baseline
from rl.common.contracts import task_from_row
from rl.common.evaluator import Attribution, EvaluationResult, EvaluationStatus
from rl.track_a import tinker_data
from rl.track_a.reward import reward_for_policy
from rl.track_a.tinker_data import TrackAEnv


class _Termination:
    is_clean = True


class _StubTokenizer:
    def decode(self, tokens):
        return "```python\nimport gdsfactory as gf\n```"


class _StubRenderer:
    tokenizer = _StubTokenizer()

    def parse_response(self, tokens):
        return (
            {
                "role": "assistant",
                "content": [{"type": "text", "text": self.tokenizer.decode(tokens)}],
            },
            _Termination(),
        )


class _StubBatcher:
    def __init__(self, result: EvaluationResult) -> None:
        self._result = result

    async def submit(self, reference, completion):
        return self._result


def test_env_step_pays_shaped_reward_with_task_baseline(core_row, monkeypatch):
    task = task_from_row(core_row)
    crafted = EvaluationResult(
        EvaluationStatus.OK,
        Attribution.MODEL,
        iou=0.62,
        dice=0.7,
        metrics={"chamfer_boundary_um": 1.5},
    )
    monkeypatch.setattr(tinker_data, "_batcher", lambda: _StubBatcher(crafted))
    env = TrackAEnv(task, _StubRenderer(), 1440, reward_policy="shaped_v3b")
    step = asyncio.run(env.step([1, 2, 3]))
    baseline = cached_rect_baseline(task.reference)
    expected = reward_for_policy(crafted, policy="shaped_v3b", baseline=baseline)
    assert step.reward == pytest.approx(expected)
    assert step.reward > 0.05
    assert step.metrics["iou_n"] == pytest.approx(
        max(0.0, (0.62 - baseline.iou_rect) / (1.0 - baseline.iou_rect))
    )
    assert "teacher_nb" in step.metrics and "degenerate" in step.metrics


def test_env_step_zero_for_model_failure_under_shaped_policy(core_row, monkeypatch):
    task = task_from_row(core_row)
    crafted = EvaluationResult(EvaluationStatus.RUNTIME_ERROR, Attribution.MODEL)
    monkeypatch.setattr(tinker_data, "_batcher", lambda: _StubBatcher(crafted))
    env = TrackAEnv(task, _StubRenderer(), 1440, reward_policy="shaped_v3b")
    step = asyncio.run(env.step([1, 2, 3]))
    assert step.reward == 0.0
    assert step.metrics["iou_n"] == 0.0
