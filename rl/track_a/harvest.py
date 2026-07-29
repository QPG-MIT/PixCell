"""Winner harvesting: sample from a trained checkpoint over TRAIN tasks,
verify with the deterministic evaluator, keep gate-passing winners.

The entropy-preserving warm-start corpus: programs the policy itself wrote
and the verifier approved (iou_n >= threshold, pure, executable). Winners
come only from the train split — validation never enters any SFT corpus.
Old-library law: winner distillation is the healthiest prior; its paper
lineage entered RL at entropy 0.32 on exactly this class of corpus, versus
0.096 for ground-truth canon.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict
from pathlib import Path

import tinker

from rl.common.baselines import cached_rect_baseline
from rl.common.contracts import TaskRecord
from rl.common.dataset_io import load_tasks
from rl.common.evaluator import EvaluationStatus, PixCellEvaluator
from rl.common.output import extract_code
from rl.track_a.reward import norm_excess
from rl.track_a.tinker_data import _message, _renderer


async def _sample(
    tasks: list[TaskRecord],
    *,
    model_name: str,
    renderer_name: str,
    model_path: str | None,
    samples_per_task: int,
    max_tokens: int,
    temperature: float,
) -> list[list[str]]:
    renderer = _renderer(model_name, renderer_name)
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

    async def one(task: TaskRecord) -> list[str]:
        prompt = renderer.build_generation_prompt([_message(task, max_image=1440)])
        response = await client.sample_async(
            prompt=prompt, num_samples=samples_per_task, sampling_params=params
        )
        out = []
        for sequence in response.sequences:
            message, _t = renderer.parse_response(list(sequence.tokens))
            from tinker_cookbook.renderers import get_text_content

            out.append(get_text_content(message))
        return out

    results: list[list[str]] = []
    batch = 24
    for start in range(0, len(tasks), batch):
        chunk = tasks[start : start + batch]
        results.extend(await asyncio.gather(*(one(t) for t in chunk)))
        print(f"[harvest] sampled {min(start+batch, len(tasks))}/{len(tasks)}", flush=True)
    return results


def harvest(
    *,
    dataset_root: str,
    levels: tuple[str, ...],
    model_name: str,
    renderer_name: str,
    model_path: str | None,
    out_path: str,
    samples_per_task: int = 2,
    max_tokens: int = 4096,
    temperature: float = 1.0,
    min_iou_n: float = 0.5,
    degenerate_min_iou: float = 0.9,
    per_representation_cap: int = 8,
) -> dict:
    train = [
        t
        for t in load_tasks(Path(dataset_root), configuration="depth", split="train")
        if t.sampler.level in levels
    ]
    print(f"[harvest] {len(train)} train tasks across {levels}", flush=True)
    completions = asyncio.run(
        _sample(
            train,
            model_name=model_name,
            renderer_name=renderer_name,
            model_path=model_path,
            samples_per_task=samples_per_task,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    )
    pairs = [
        (task, completion)
        for task, batch in zip(train, completions)
        for completion in batch
    ]
    with PixCellEvaluator(max_workers=4, evaluator_retries=3) as evaluator:
        results = evaluator.evaluate_batch(
            [(task.reference, completion) for task, completion in pairs]
        )
    best: dict[str, dict] = {}
    per_rep = defaultdict(int)
    status_counts: dict[str, int] = defaultdict(int)
    kept = examined = 0
    for (task, completion), result in zip(pairs, results):
        examined += 1
        status_counts[result.status.value] += 1
        if result.status is not EvaluationStatus.OK or result.iou is None:
            continue
        baseline = cached_rect_baseline(task.reference)
        iou_n = norm_excess(float(result.iou), baseline.iou_rect)
        degenerate = baseline.iou_rect >= 0.95
        win = (iou_n >= min_iou_n) or (degenerate and float(result.iou) >= degenerate_min_iou)
        if not win:
            continue
        key = task.sampler.opaque_id
        score = iou_n if not degenerate else float(result.iou)
        record = {
            "opaque_id": key,
            "level": task.sampler.level,
            "representation_id": task.sampler.representation_id,
            "iou": float(result.iou),
            "iou_n": float(iou_n),
            "degenerate": degenerate,
            "code": extract_code(completion),
        }
        if key not in best or score > best[key]["iou_n"]:
            best[key] = record
    winners = []
    for record in sorted(best.values(), key=lambda r: -r["iou_n"]):
        if per_rep[record["representation_id"]] >= per_representation_cap:
            continue
        per_rep[record["representation_id"]] += 1
        winners.append(record)
        kept += 1
    by_level = defaultdict(int)
    for w in winners:
        by_level[w["level"]] += 1
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as sink:
        for w in winners:
            sink.write(json.dumps(w) + "\n")
    summary = {
        "examined": examined,
        "status_counts": dict(status_counts),
        "unique_tasks_won": len(best),
        "kept_after_caps": kept,
        "by_level": dict(by_level),
        "out": str(out),
    }
    print("[harvest]", json.dumps(summary), flush=True)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset-root", default=str(Path(__file__).resolve().parents[2] / "dataset"))
    ap.add_argument("--levels", default="L0,L1")
    ap.add_argument("--model-name", default="Qwen/Qwen3.6-35B-A3B")
    ap.add_argument("--renderer-name", default="qwen3_5_disable_thinking")
    ap.add_argument("--model-path", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--samples-per-task", type=int, default=2)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--min-iou-n", type=float, default=0.5)
    ap.add_argument("--max-tokens", type=int, default=4096)
    args = ap.parse_args()
    from rl.track_a.transport import disable_pyqwest_transport

    disable_pyqwest_transport()
    harvest(
        dataset_root=args.dataset_root,
        levels=tuple(x.strip().upper() for x in args.levels.split(",") if x.strip()),
        model_name=args.model_name,
        renderer_name=args.renderer_name,
        model_path=args.model_path or None,
        out_path=args.out,
        samples_per_task=args.samples_per_task,
        temperature=args.temperature,
        min_iou_n=args.min_iou_n,
        max_tokens=args.max_tokens,
    )


if __name__ == "__main__":
    main()


def apply_winner_labels(
    tasks: list[TaskRecord],
    winners_path: str | Path,
) -> list[TaskRecord]:
    """Project TRAIN tasks onto a harvested winner corpus: keep only tasks
    that have a verified winner and replace the GT label with the policy's
    own winning program. The SFT that consumes this distills the model's own
    verified distribution — the entropy-preserving warm start."""

    import dataclasses

    labels: dict[str, str] = {}
    for line in Path(winners_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        code = record.get("code", "").strip()
        if code:
            labels[record["opaque_id"]] = code
    projected = [
        dataclasses.replace(task, label=labels[task.sampler.opaque_id])
        for task in tasks
        if task.sampler.opaque_id in labels
    ]
    if not projected:
        raise ValueError(f"no tasks match winners in {winners_path}")
    return projected
