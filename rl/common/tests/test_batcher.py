from __future__ import annotations

import asyncio
import hashlib

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


def test_concurrent_rollouts_coalesce_into_one_ordered_batch():
    async def run():
        payload = b"target"
        reference = VerifierReference(
            payload,
            (1.0, 1.0),
            hashlib.sha256(payload).hexdigest(),
        )
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
