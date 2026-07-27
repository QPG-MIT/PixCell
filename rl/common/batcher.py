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
        if max_batch_size < 1:
            raise ValueError("max_batch_size must be positive")
        if flush_delay_seconds < 0:
            raise ValueError("flush_delay_seconds must be non-negative")
        self.evaluator = evaluator
        self.max_batch_size = max_batch_size
        self.flush_delay_seconds = flush_delay_seconds
        self._pending: list[_Pending] = []
        self._lock = asyncio.Lock()
        self._close_lock = asyncio.Lock()
        self._flush_wakeup = asyncio.Event()
        self._flush_task: asyncio.Task[None] | None = None
        self._closed = False
        self._evaluator_closed = False

    async def submit(
        self,
        reference: VerifierReference,
        completion: str,
    ) -> EvaluationResult:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[EvaluationResult] = loop.create_future()
        async with self._lock:
            if self._closed:
                raise RuntimeError("evaluation batcher is closed")
            self._pending.append(_Pending(reference, completion, future))
            if self._flush_task is None or self._flush_task.done():
                self._flush_wakeup.clear()
                self._flush_task = asyncio.create_task(
                    self._drain(
                        after_delay=len(self._pending) < self.max_batch_size
                    )
                )
            elif len(self._pending) >= self.max_batch_size:
                self._flush_wakeup.set()
        return await future

    async def _drain(self, *, after_delay: bool) -> None:
        current = asyncio.current_task()
        if after_delay:
            try:
                await asyncio.wait_for(
                    self._flush_wakeup.wait(),
                    timeout=self.flush_delay_seconds,
                )
            except TimeoutError:
                pass
            self._flush_wakeup.clear()
        try:
            while True:
                async with self._lock:
                    batch = self._pending[: self.max_batch_size]
                    del self._pending[: self.max_batch_size]
                if not batch:
                    return
                try:
                    results = await asyncio.to_thread(
                        self.evaluator.evaluate_batch,
                        [(item.reference, item.completion) for item in batch],
                    )
                    if len(results) != len(batch):
                        raise RuntimeError(
                            "evaluator returned a different number of results "
                            "than requests"
                        )
                except BaseException as exc:
                    for item in batch:
                        if not item.future.done():
                            item.future.set_exception(exc)
                else:
                    for item, result in zip(batch, results, strict=True):
                        if not item.future.done():
                            item.future.set_result(result)
        finally:
            async with self._lock:
                if self._flush_task is current:
                    self._flush_task = None
                # No submit can enqueue after close linearizes. Under normal
                # operation the loop drains everything; this branch also
                # prevents an externally cancelled worker from stranding
                # already accepted futures.
                if self._pending and self._flush_task is None:
                    self._flush_task = asyncio.create_task(
                        self._drain(after_delay=False)
                    )

    async def close(self) -> None:
        async with self._close_lock:
            if self._evaluator_closed:
                return
            while True:
                async with self._lock:
                    self._closed = True
                    self._flush_wakeup.set()
                    if self._pending and (
                        self._flush_task is None or self._flush_task.done()
                    ):
                        self._flush_task = asyncio.create_task(
                            self._drain(after_delay=False)
                        )
                    task = self._flush_task
                    done = not self._pending and (
                        task is None or task.done()
                    )
                if done:
                    break
                if task is not None:
                    await task
            self.evaluator.close()
            self._evaluator_closed = True
