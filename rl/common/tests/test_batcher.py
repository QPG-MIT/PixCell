from __future__ import annotations

import asyncio
import hashlib

import pytest

from rl.common.batcher import AsyncEvaluationBatcher
from rl.common.contracts import VerifierReference
from rl.common.evaluator import (
    Attribution,
    EvaluationResult,
    EvaluationStatus,
)


class _FakeEvaluator:
    def __init__(self):
        self.calls = []
        self.closed = False

    def evaluate_batch(self, requests):
        self.calls.append(list(requests))
        return [
            EvaluationResult(
                EvaluationStatus.OK,
                Attribution.MODEL,
                iou=float(index) / 10,
            )
            for index, _ in enumerate(requests)
        ]

    def close(self):
        self.closed = True


def _reference():
    payload = b"target"
    return VerifierReference(
        payload,
        (1.0, 1.0),
        hashlib.sha256(payload).hexdigest(),
    )


def test_concurrent_rollouts_coalesce_into_one_ordered_batch():
    async def run():
        reference = _reference()
        evaluator = _FakeEvaluator()
        batcher = AsyncEvaluationBatcher(
            evaluator,
            max_batch_size=4,
            flush_delay_seconds=0.02,
        )
        results = await asyncio.gather(
            *(batcher.submit(reference, f"code-{index}") for index in range(4))
        )
        await batcher.close()
        assert len(evaluator.calls) == 1
        assert [request[1] for request in evaluator.calls[0]] == [
            "code-0",
            "code-1",
            "code-2",
            "code-3",
        ]
        assert [result.iou for result in results] == [0.0, 0.1, 0.2, 0.3]
        assert evaluator.closed

    asyncio.run(run())


@pytest.mark.parametrize("value", [0, -1])
def test_invalid_batch_sizes_are_rejected(value):
    with pytest.raises(ValueError, match="max_batch_size"):
        AsyncEvaluationBatcher(_FakeEvaluator(), max_batch_size=value)


def test_negative_flush_delay_is_rejected():
    with pytest.raises(ValueError, match="flush_delay_seconds"):
        AsyncEvaluationBatcher(_FakeEvaluator(), flush_delay_seconds=-0.01)


def test_close_drains_a_delayed_partial_batch_and_is_idempotent():
    async def run():
        evaluator = _FakeEvaluator()
        batcher = AsyncEvaluationBatcher(
            evaluator,
            max_batch_size=4,
            flush_delay_seconds=60,
        )
        submitted = asyncio.create_task(
            batcher.submit(_reference(), "accepted-before-close")
        )
        await asyncio.sleep(0)
        await batcher.close()
        result = await submitted
        await batcher.close()
        assert result.status is EvaluationStatus.OK
        assert len(evaluator.calls) == 1
        assert evaluator.closed
        with pytest.raises(RuntimeError, match="closed"):
            await batcher.submit(_reference(), "too-late")

    asyncio.run(run())


def test_close_and_submit_have_one_locked_linearization_point():
    async def run():
        evaluator = _FakeEvaluator()
        batcher = AsyncEvaluationBatcher(evaluator, flush_delay_seconds=0)
        await batcher._lock.acquire()
        accepted = asyncio.create_task(
            batcher.submit(_reference(), "accepted")
        )
        await asyncio.sleep(0)
        closing = asyncio.create_task(batcher.close())
        await asyncio.sleep(0)
        batcher._lock.release()
        result = await accepted
        await closing
        assert result.status is EvaluationStatus.OK
        assert evaluator.closed

    asyncio.run(run())


def test_close_wins_locked_race_and_later_submit_is_rejected():
    async def run():
        evaluator = _FakeEvaluator()
        batcher = AsyncEvaluationBatcher(evaluator, flush_delay_seconds=0)
        await batcher._lock.acquire()
        closing = asyncio.create_task(batcher.close())
        await asyncio.sleep(0)
        submitted = asyncio.create_task(
            batcher.submit(_reference(), "must-not-run")
        )
        await asyncio.sleep(0)
        batcher._lock.release()
        await closing
        with pytest.raises(RuntimeError, match="closed"):
            await submitted
        assert evaluator.calls == []
        assert evaluator.closed

    asyncio.run(run())


def test_wrong_result_count_faults_every_accepted_future():
    class _ShortEvaluator(_FakeEvaluator):
        def evaluate_batch(self, requests):
            self.calls.append(list(requests))
            return []

    async def run():
        evaluator = _ShortEvaluator()
        batcher = AsyncEvaluationBatcher(
            evaluator,
            max_batch_size=2,
            flush_delay_seconds=0,
        )
        results = await asyncio.gather(
            batcher.submit(_reference(), "a"),
            batcher.submit(_reference(), "b"),
            return_exceptions=True,
        )
        await batcher.close()
        assert len(results) == 2
        assert all(
            isinstance(result, RuntimeError)
            and "different number" in str(result)
            for result in results
        )

    asyncio.run(run())
