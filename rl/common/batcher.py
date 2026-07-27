"""Shared async adapter from independent evaluations to bounded batches."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from .contracts import VerifierReference
from .evaluator import EvaluationResult, PixCellEvaluator


@dataclass
class _Pending:
    reference: VerifierReference
    completion: str
    future: asyncio.Future[EvaluationResult]


class AsyncEvaluationBatcher:
    """Coalesce concurrently arriving rollout scores into ordered worker batches."""

    def __init__(
        self,
        evaluator: PixCellEvaluator,
        *,
        max_batch_size: int = 32,
        flush_delay_seconds: float = 0.01,
    ) -> None:
        self.evaluator = evaluator
        self.max_batch_size = max_batch_size
        self.flush_delay_seconds = flush_delay_seconds
        self._pending: list[_Pending] = []
        self._lock = asyncio.Lock()
        self._flush_task: asyncio.Task[None] | None = None
        self._closed = False

    async def submit(
        self,
        reference: VerifierReference,
        completion: str,
    ) -> EvaluationResult:
        if self._closed:
            raise RuntimeError("evaluation batcher is closed")
        loop = asyncio.get_running_loop()
        future: asyncio.Future[EvaluationResult] = loop.create_future()
        async with self._lock:
            self._pending.append(_Pending(reference, completion, future))
            if len(self._pending) >= self.max_batch_size:
                if self._flush_task is None or self._flush_task.done():
                    self._flush_task = asyncio.create_task(
                        self._flush(after_delay=False)
                    )
            elif self._flush_task is None or self._flush_task.done():
                self._flush_task = asyncio.create_task(self._flush(after_delay=True))
        return await future

    async def _flush(self, *, after_delay: bool) -> None:
        if after_delay:
            await asyncio.sleep(self.flush_delay_seconds)
        async with self._lock:
            batch = self._pending[: self.max_batch_size]
            del self._pending[: self.max_batch_size]
            self._flush_task = None
            if self._pending:
                self._flush_task = asyncio.create_task(self._flush(after_delay=False))
        if not batch:
            return
        try:
            results = await asyncio.to_thread(
                self.evaluator.evaluate_batch,
                [(item.reference, item.completion) for item in batch],
            )
        except BaseException as exc:
            for item in batch:
                if not item.future.done():
                    item.future.set_exception(exc)
            return
        for item, result in zip(batch, results, strict=True):
            if not item.future.done():
                item.future.set_result(result)

    async def close(self) -> None:
        self._closed = True
        task = self._flush_task
        if task is not None and not task.done():
            await task
        if self._pending:
            await self._flush(after_delay=False)
        self.evaluator.close()
