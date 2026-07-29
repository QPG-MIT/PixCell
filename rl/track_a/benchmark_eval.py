"""The paper's F1-F8 benchmark protocol on a checkpoint: 8 attempts per
target at T=1.0, per-target best-of-8 and mean raw IoU — the exact
evaluation behind the paper's Table III (its trained model: mean 0.254,
best-of-8 0.466). Fixtures are the frozen data/benchmark devices; the model
sees the same raster it is scored against, per the historical protocol.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path

import tinker

from rl.common.contracts import ModelObservation, TaskRecord, SamplerMetadata, VerifierReference
from rl.common.evaluator import EvaluationStatus, PixCellEvaluator
from rl.track_a.tinker_data import _message, _renderer


def _fixture_tasks(benchmark_root: Path) -> list[TaskRecord]:
    tasks = []
    for index in range(1, 9):
        directory = benchmark_root / f"final_{index}"
        payload = (directory / "device_bw.png").read_bytes()
        footprint = tuple(
            json.loads((directory / "footprint.json").read_text())["footprint_um"]
        )
        digest = hashlib.sha256(payload).hexdigest()
        observation = ModelObservation(
            image_bytes=payload, footprint_um=footprint, image_sha256=digest
        )
        reference = VerifierReference(
            target_image_bytes=payload,
            footprint_um=footprint,
            target_image_sha256=digest,
        )
        sampler = SamplerMetadata(
            opaque_id=f"final_{index}",
            level="BENCH",
            representation_id=f"final_{index}",
            leakage_group_id=f"final_{index}",
            realization_slot=None,
            split_role="benchmark",
        )
        tasks.append(
            TaskRecord(
                observation=observation,
                label="",
                reference=reference,
                sampler=sampler,
            )
        )
    return tasks


def run_benchmark(
    *,
    benchmark_root: str,
    model_name: str,
    renderer_name: str,
    model_path: str | None,
    max_tokens: int,
    attempts: int = 8,
    temperature: float = 1.0,
    out_path: str | None = None,
    model_effort: float | None = None,
) -> dict:
    tasks = _fixture_tasks(Path(benchmark_root))
    renderer = _renderer(model_name, renderer_name, effort=model_effort)
    service = tinker.ServiceClient()
    client = (
        service.create_sampling_client(model_path=model_path)
        if model_path
        else service.create_sampling_client(base_model=model_name)
    )
    params = tinker.SamplingParams(
        max_tokens=max_tokens,
        temperature=temperature,
        stop=renderer.get_stop_sequences(),
    )

    async def sample_all() -> list[list[str]]:
        async def one(task: TaskRecord) -> list[str]:
            prompt = renderer.build_generation_prompt(
                [_message(task, max_image=1440)]
            )
            response = await client.sample_async(
                prompt=prompt, num_samples=attempts, sampling_params=params
            )
            from tinker_cookbook.renderers import get_text_content

            out = []
            for sequence in response.sequences:
                message, _t = renderer.parse_response(list(sequence.tokens))
                out.append(get_text_content(message))
            return out

        return list(await asyncio.gather(*(one(t) for t in tasks)))

    completions = asyncio.run(sample_all())
    pairs = [
        (task, completion)
        for task, batch in zip(tasks, completions)
        for completion in batch
    ]
    with PixCellEvaluator(
        max_workers=4, evaluator_retries=3
    ) as evaluator:
        results = evaluator.evaluate_batch(
            [(task.reference, completion) for task, completion in pairs]
        )
    per_target: dict[str, dict] = {}
    cursor = 0
    for task, batch in zip(tasks, completions):
        scores = []
        executable = 0
        for _ in batch:
            result = results[cursor]
            cursor += 1
            if result.status is EvaluationStatus.OK and result.iou is not None:
                executable += 1
                scores.append(float(result.iou))
            else:
                scores.append(0.0)
        per_target[task.sampler.opaque_id] = {
            "executable": executable,
            "attempts": len(batch),
            "mean_iou": sum(scores) / len(scores),
            "best_iou": max(scores),
        }
    targets = list(per_target.values())
    report = {
        "model_name": model_name,
        "model_path": model_path,
        "attempts": attempts,
        "temperature": temperature,
        "per_target": per_target,
        "overall": {
            "executable": sum(t["executable"] for t in targets),
            "total": sum(t["attempts"] for t in targets),
            "mean_iou": sum(t["mean_iou"] for t in targets) / len(targets),
            "mean_best_of_k": sum(t["best_iou"] for t in targets) / len(targets),
        },
    }
    if out_path:
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["overall"], indent=2), flush=True)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    repo = Path(__file__).resolve().parents[2]
    ap.add_argument("--benchmark-root", default=str(repo / "data" / "benchmark"))
    ap.add_argument("--model-name", default="Qwen/Qwen3.6-35B-A3B")
    ap.add_argument("--renderer-name", default="qwen3_5_disable_thinking")
    ap.add_argument("--model-path", default="")
    ap.add_argument("--model-effort", type=float, default=-1.0)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--attempts", type=int, default=8)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    from rl.track_a.transport import disable_pyqwest_transport

    disable_pyqwest_transport()
    run_benchmark(
        benchmark_root=args.benchmark_root,
        model_name=args.model_name,
        renderer_name=args.renderer_name,
        model_path=args.model_path or None,
        max_tokens=args.max_tokens,
        attempts=args.attempts,
        out_path=args.out,
        model_effort=args.model_effort if args.model_effort >= 0 else None,
    )


if __name__ == "__main__":
    main()
