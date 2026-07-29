"""Fixed cross-run probe evaluation.

One deterministic probe set — the first ``per_level`` validation tasks per
level by sorted opaque id — evaluated identically at campaign start (the
base-model baseline), after every stage, and at the end. Because the set
never changes, every point on the resulting curve is comparable; this is
the discipline the old campaign lost when its eval pool grew mid-run.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from pathlib import Path

import tinker

from rl.common.baselines import cached_rect_baseline
from rl.common.contracts import TaskRecord
from rl.common.dataset_io import load_tasks
from rl.common.evaluator import EvaluationStatus, PixCellEvaluator
from rl.track_a.curriculum import LEVELS
from rl.track_a.reward import reward_for_policy
from rl.track_a.tinker_data import _message, _renderer


def select_probe_tasks(
    dataset_root: str | Path,
    *,
    per_level: int = 16,
) -> list[TaskRecord]:
    """Deterministic: per level, the first ``per_level`` validation tasks by
    sorted opaque id. No seed, no state."""

    validation = load_tasks(Path(dataset_root), configuration="depth", split="validation")
    by_level: dict[str, list[TaskRecord]] = defaultdict(list)
    for task in validation:
        by_level[task.sampler.level].append(task)
    selected: list[TaskRecord] = []
    for level in LEVELS:
        ranked = sorted(by_level[level], key=lambda task: task.sampler.opaque_id)
        if len(ranked) < per_level:
            raise ValueError(f"{level} has only {len(ranked)} validation tasks")
        selected.extend(ranked[:per_level])
    return selected


async def _sample_completions(
    tasks: list[TaskRecord],
    *,
    model_name: str,
    renderer_name: str,
    model_path: str | None,
    max_tokens: int,
    temperature: float,
) -> list[str]:
    from rl.track_a.transport import disable_pyqwest_transport

    disable_pyqwest_transport()
    renderer = _renderer(model_name, renderer_name)
    service = tinker.ServiceClient()
    if model_path:
        client = service.create_sampling_client(model_path=model_path)
    else:
        client = service.create_sampling_client(base_model=model_name)
    params = tinker.SamplingParams(
        max_tokens=max_tokens,
        temperature=temperature,
        stop=renderer.get_stop_sequences(),
    )

    async def one(task: TaskRecord) -> str:
        prompt = renderer.build_generation_prompt(
            [_message(task, max_image=1440)]
        )
        response = await client.sample_async(
            prompt=prompt,
            num_samples=1,
            sampling_params=params,
        )
        tokens = list(response.sequences[0].tokens)
        message, _termination = renderer.parse_response(tokens)
        from tinker_cookbook.renderers import get_text_content

        return get_text_content(message)

    return list(await asyncio.gather(*(one(task) for task in tasks)))


def run_probe(
    *,
    dataset_root: str | Path,
    model_name: str,
    renderer_name: str,
    model_path: str | None,
    max_tokens: int,
    out_path: str | Path | None = None,
    per_level: int = 16,
    temperature: float = 1.0,
    max_workers: int = 8,
) -> dict:
    """Sample one completion per probe task and grade it exactly as training
    does. Returns (and optionally writes) the per-level summary."""

    tasks = select_probe_tasks(dataset_root, per_level=per_level)
    completions = asyncio.run(
        _sample_completions(
            tasks,
            model_name=model_name,
            renderer_name=renderer_name,
            model_path=model_path,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    )
    import os

    with PixCellEvaluator(
        max_workers=int(os.environ.get("PIXCELL_EVAL_WORKERS", str(max_workers))),
        evaluator_retries=3,
        execution_timeout_seconds=float(
            os.environ.get("PIXCELL_EVAL_TIMEOUT", "20")
        ),
        require_isolation=(
            os.environ.get("PIXCELL_REQUIRE_ISOLATION", "0") == "1"
        ),
    ) as evaluator:
        results = evaluator.evaluate_batch(
            [(task.reference, completion) for task, completion in zip(tasks, completions)]
        )

    rows = []
    for task, result in zip(tasks, results):
        baseline = cached_rect_baseline(task.reference)
        shaped = reward_for_policy(result, policy="shaped_v3b", baseline=baseline)
        rows.append(
            {
                "opaque_id": task.sampler.opaque_id,
                "level": task.sampler.level,
                "status": result.status.value,
                "executable": result.status is EvaluationStatus.OK,
                "iou": float(result.iou or 0.0),
                "shaped": float(shaped) if shaped is not None else None,
            }
        )

    per_level_summary: dict[str, dict[str, float]] = {}
    for level in LEVELS:
        level_rows = [row for row in rows if row["level"] == level]
        graded = [row for row in level_rows if row["shaped"] is not None]
        per_level_summary[level] = {
            "n": len(level_rows),
            "executable_rate": (
                sum(row["executable"] for row in level_rows) / len(level_rows)
            ),
            "mean_iou": sum(row["iou"] for row in level_rows) / len(level_rows),
            "mean_shaped": (
                sum(row["shaped"] for row in graded) / len(graded) if graded else 0.0
            ),
        }
    graded = [row for row in rows if row["shaped"] is not None]
    report = {
        "model_name": model_name,
        "renderer_name": renderer_name,
        "model_path": model_path,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "per_level": per_level_summary,
        "overall": {
            "n": len(rows),
            "executable_rate": sum(row["executable"] for row in rows) / len(rows),
            "mean_iou": sum(row["iou"] for row in rows) / len(rows),
            "mean_shaped": (
                sum(row["shaped"] for row in graded) / len(graded) if graded else 0.0
            ),
        },
        "rows": rows,
    }
    if out_path is not None:
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
