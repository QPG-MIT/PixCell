"""The iterative deployment loop on the F1-F8 benchmark: attempt, measure,
revise. A faithful minimal port of the private library's agent loop —
init round of k attempts, then revision rounds seeded by the current
champion plus deterministic, number-redacted feedback (closeness bucket,
material direction from chamfer asymmetry, error class). The teacher
directs attention; it never dictates values.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path

import tinker

from rl.common.baselines import cached_rect_baseline
from rl.common.contracts import TaskRecord
from rl.common.evaluator import EvaluationResult, EvaluationStatus, PixCellEvaluator
from rl.common.output import extract_code
from rl.track_a.benchmark_eval import _fixture_tasks
from rl.track_a.reward import norm_excess
from rl.track_a.tinker_data import _message, _renderer


def _scrub(text: str) -> str:
    return re.sub(r"[0-9]+(?:\.[0-9]+)?", "#", text)


def _feedback(result: EvaluationResult, task: TaskRecord) -> str:
    if result.status is not EvaluationStatus.OK or result.iou is None:
        reason = _scrub(str(result.error or result.status.value))[:300]
        return (
            "Your previous program FAILED to produce a valid device "
            f"({result.status.value}): {reason}\n"
            "Fix the failure and output a complete corrected program."
        )
    baseline = cached_rect_baseline(task.reference)
    iou_n = norm_excess(float(result.iou), baseline.iou_rect)
    if iou_n >= 0.8:
        closeness = "VERY CLOSE to the target"
    elif iou_n >= 0.5:
        closeness = "close to the target, but clearly imperfect"
    elif iou_n >= 0.1:
        closeness = "partially matching the target"
    else:
        closeness = "far from the target beyond its overall footprint"
    pred_to_target = result.metrics.get("chamfer_pred_to_target_um")
    target_to_pred = result.metrics.get("chamfer_target_to_pred_um")
    direction = ""
    if pred_to_target is not None and target_to_pred is not None:
        if pred_to_target > 1.5 * target_to_pred:
            direction = (
                "Your rendering has EXTRA material the target does not have — "
                "simplify or remove structure."
            )
        elif target_to_pred > 1.5 * pred_to_target:
            direction = (
                "Your rendering is MISSING material the target has — add or "
                "extend structure."
            )
        else:
            direction = (
                "Material amounts roughly balance; refine shapes, positions, "
                "and repeated-element counts."
            )
    return (
        f"Your previous program executed. Its rendering is {closeness}. "
        f"{direction}\n"
        "Revise the program to better match the attached target image. "
        "Output only the complete corrected Python program."
    )


def run_agent_loop(
    *,
    benchmark_root: str,
    model_name: str,
    renderer_name: str,
    model_path: str | None,
    max_tokens: int,
    init_attempts: int = 8,
    revisions_per_round: int = 4,
    rounds: int = 3,
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
    from tinker_cookbook.renderers import Message, TextPart, get_text_content

    async def sample(conversation, count):
        prompt = renderer.build_generation_prompt(conversation)
        response = await client.sample_async(
            prompt=prompt, num_samples=count, sampling_params=params
        )
        out = []
        for sequence in response.sequences:
            message, _t = renderer.parse_response(list(sequence.tokens))
            out.append(get_text_content(message))
        return out

    evaluator = PixCellEvaluator(max_workers=4, evaluator_retries=3)
    report: dict[str, dict] = {}
    try:
        for task in tasks:
            user = _message(task, max_image=1440)
            history: list[dict] = []
            champion_code: str | None = None
            champion_result: EvaluationResult | None = None
            champion_iou = -1.0
            for round_index in range(rounds + 1):
                if round_index == 0:
                    conversation = [user]
                    count = init_attempts
                else:
                    assert champion_result is not None
                    feedback = _feedback(champion_result, task)
                    conversation = [
                        user,
                        Message(
                            role="assistant",
                            content=[
                                TextPart(
                                    type="text",
                                    text=f"```python\n{champion_code}\n```",
                                )
                            ],
                        ),
                        Message(
                            role="user",
                            content=[TextPart(type="text", text=feedback)],
                        ),
                    ]
                    count = revisions_per_round
                completions = asyncio.run(sample(conversation, count))
                results = evaluator.evaluate_batch(
                    [(task.reference, completion) for completion in completions]
                )
                round_best = -1.0
                for completion, result in zip(completions, results):
                    iou = (
                        float(result.iou)
                        if result.status is EvaluationStatus.OK and result.iou
                        else 0.0
                    )
                    round_best = max(round_best, iou)
                    if iou > champion_iou or champion_result is None:
                        champion_iou = max(iou, 0.0)
                        champion_code = extract_code(completion)
                        champion_result = result
                history.append(
                    {"round": round_index, "samples": count, "round_best": round_best,
                     "champion_iou": champion_iou}
                )
                print(
                    f"[{task.sampler.opaque_id}] round {round_index}: "
                    f"best {round_best:.3f}, champion {champion_iou:.3f}",
                    flush=True,
                )
            report[task.sampler.opaque_id] = {
                "champion_iou": champion_iou,
                "champion_code": champion_code or "",
                "footprint_um": list(task.observation.footprint_um),
                "rounds": history,
            }
    finally:
        evaluator.close()
    champions = [entry["champion_iou"] for entry in report.values()]
    summary = {
        "model_path": model_path,
        "init_attempts": init_attempts,
        "revisions_per_round": revisions_per_round,
        "rounds": rounds,
        "per_target": report,
        "overall_mean_champion": sum(champions) / len(champions),
    }
    if out_path:
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"overall_mean_champion": summary["overall_mean_champion"]}), flush=True)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    repo = Path(__file__).resolve().parents[2]
    ap.add_argument("--benchmark-root", default=str(repo / "data" / "benchmark"))
    ap.add_argument("--model-name", default="Qwen/Qwen3.6-35B-A3B")
    ap.add_argument("--renderer-name", default="qwen3_5_disable_thinking")
    ap.add_argument("--model-path", default="")
    ap.add_argument("--model-effort", type=float, default=-1.0)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    from rl.track_a.transport import disable_pyqwest_transport

    disable_pyqwest_transport()
    run_agent_loop(
        benchmark_root=args.benchmark_root,
        model_name=args.model_name,
        renderer_name=args.renderer_name,
        model_path=args.model_path or None,
        max_tokens=args.max_tokens,
        rounds=args.rounds,
        out_path=args.out,
        model_effort=args.model_effort if args.model_effort >= 0 else None,
    )


if __name__ == "__main__":
    main()
